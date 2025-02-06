import xml.etree.ElementTree as ET
from json import dumps as jdumps
from os.path import exists

class mxdict(dict):
	'''
	Parses a No Man's Sky mxml file and converts it to a working searchable dictionary,
	Sets class and value names as unique keys wherever possible for direct access.
	@param mxml: [optional] Either an mxml-formatted string or a [*.mxml] file path
	@param casting: [optional] cast values to appropriate types. All are strings if False
	'''
	def __init__(self, mxml:str=None, casting:bool=False):
		self.__mxml = mxml
		self.__cast = casting

	@property
	def casting(self) -> bool:
		'''
		Evaluates values and casts to appropriate types (enables __eval)
		If False all values in the produced dictionary are represented as strings
		'''
		return self.__cast
	@casting.setter
	def casting(self, c:bool): self.__cast = c

	@property
	def mxml(self) -> str:
		''' Either an mxml-formatted string or a [*.mxml] file path '''
		return self.__mxml
	@mxml.setter
	def mxml(self, e): self.__mxml = e

	def parse(self, mxml:str=None) -> dict:
		'''
		Parse mxml text into a dictionary
		Internal dict will be cleared before the process
		@param mxml: Either an mxml-formatted string or a [*.mxml] file path
		'''
		self.clear()
		if mxml: self.mxml = mxml
		try:
			if self.mxml.lower().endswith('xml'): # switch string or file
				if exists(self.mxml):
					t = ET.parse(self.mxml).getroot()
					return self.__to_dict(t, self)
				else:
					print('File not found!')
			else:
				t = ET.fromstring(self.mxml)
				return self.__to_dict(t, self)
		except ET.ParseError as e:
			print(f'Parsing encountered an error! {e.args}')

	def	__eval(self, val:str):
		'''
		evaluate value and cast to appropriate type
		(rudimentary - but it's enough)
		'''
		try:
			if val.count('.') > 0:
				return float(val)
			else:
				return int(val)
		except ValueError:
			if val == 'true': return True
			if val == 'false': return False
			return val

	def	__attr(self, n):
		'''
		Return values from node attributes (skipping the useless tags)
		cast values to real types (optional with class flag 'casting')
		'''
		if len(n) > 2:
			return n['name'], n['value'], n['linked']
		elif len(n) > 1:
			return n['name'], self.__eval(n['value']) if self.__cast else n['value'], None
		elif len(n) > 0:
			if 'name'	  in n: return 'name',		n['name'], None
			if 'value'	  in n: return 'value',		self.__eval(n['value']) if self.__cast else n['value'], None
			if 'template' in n: return 'template',	n['template'], None
		return None

	def __to_dict(self, tree, dct):
		'''
		Traverse mxml file or sections and build an equivalent dictionary
		'''
		rk, rv, rl = self.__attr(tree.attrib)
		if rk == 'template':
			dct[rk] = rv
		else:
			dct['meta'] = [rk, rv]
			if rl is not None: dct['meta'].append(rl)

		for node in tree:
			k, v, _ = self.__attr(node.attrib)
			if len(node) > 0:
				if k == 'name':
				# new ordered list section
					key = v
				else:
					if rk != 'name':
					# new class section
						key = k
					else:
					# ordered list nested inside ordered list
						key = len(dct) - 1

				dct[key] = self.__to_dict(node, mxdict(casting=self.__cast))

			else:
				if k == 'value':
				# non-named values
					dct[len(dct) - 1] = v
				elif k == 'name':
				# empty list stub
					dct[v] = None
				elif rk == 'name':
				# v5.30+ ordered list value
					dct[len(dct) - 1] = self.__to_dict(node, mxdict(casting=self.__cast))
				else:
				# regular property
					dct[k] = v

		return dct

	def	to_mxml(self) -> str:
		'''
		Convert dictionary to an mxml string
		'''
		if 'template' in self:
			root = ET.Element('Data', attrib={'template': self['template']})
			return ET.tostring(self.__to_tree(self, root), encoding='utf-8')
		else:
			# __to_tree needs another containing dict to process the root
			return ET.tostring(self.__to_tree({'faux_container': self}), encoding='unicode')

	def	__to_tree(self, dct, tree=None) -> ET.Element:
		'''
		Build mxml format from dictionary
		'''
		if tree is None:
			tree = ET.Element('Data', attrib={'faux': 'container'})

		for key, cls in dct.items():
			if key != 'meta' and key != 'template':
				# open new node
				sdic = isinstance(cls, dict)
				node = ET.SubElement(tree, 'Property')
				if sdic:
					# 2-attribute
					att2 = cls['meta'][0] != 'name'
					if att2:
						att, val = cls['meta'][0], cls['meta'][1]
						if att == 'value':
							attribs = {'value': val}
						else:
							attribs = {'name': att, 'value': val}
							if len(cls['meta']) > 2:
								attribs.update({'linked': cls['meta'][2]})
					# 1-attribute : new list
					else:
						attribs = {'value' if att2 else 'name': key}

					node.attrib = attribs
					self.__to_tree(cls, node)
				# add properties
				else:
					# if key.isnumeric():
					if isinstance(key, int):
						# 'un-named' list property
						attribs = {'value': str(cls)}
					elif cls is not None:
						# normal property
						attribs = {'name': key, 'value': str(cls)}
					else:
						# list stub
						attribs = {'name': key}

					node.attrib = attribs

		return tree

	def append(self, key:str=None, val=''):
		'''
		Add new keyed dictionary value or append to a 'list' with sequential keys
		'''
		if 'meta' in self and self['meta'][0] == 'name':
			key = len(self) - 1
		self[key] = val

	def data_keys(self) -> list:
		'''
		Returns a list of Keys for iteration while excluding meta key
		'''
		return [k for k in super().keys() if k != 'meta']

	def data_items(self) -> list:
		'''
		Returns a list of (Key, Value) for iteration while excluding meta data
		'''
		return [(k, v) for k, v in super().items() if k != 'meta']

	def one_liner(self, sep1:str=';', sep2:str=',') -> str:
		'''
		Returns all values in the dict joined in a string, or None if empty
		@param sep1: Root level object separator
		@param sep2: Sub level value separator
		'''
		def traverse(d):
			if isinstance(d, dict):
				result = []
				for _,dat in d.data_items():
					if d['meta'][0] == 'name' and len(d[0]) == 1:
						# v5.30 nested arrays fix
						result.append(traverse(dat['meta'][1]))
					else:
						result.append(traverse(dat))
				return sep2.join(result)
			else:
				return str(d)

		if len(self) > 0:
			if self['meta'][0] == 'name' and len(self[0]) == 1:
				# v5.30 nested arrays fix
				contr = mxdict()
				contr.update({0: self})
				res = [traverse(dat) for _,dat in contr.data_items()]
			else:
				res = [traverse(dat) for _,dat in self.data_items()]

			if len(res) == 1 and (res[0] is None):
				return None
			# use sep2 if data has a single level
			return (sep1 if res[0].count(sep2) > 0 else sep2).join(res)
		else:
			return None

	def write_mxml(self, target:str):
		'''
		Writes dictionary back to mxml file
		@param target: Output mxml file path
		'''
		if len(self) > 0:
			with open(target, 'wb') as f: f.write(self.to_mxml())
		else:
			print('exdictionary is empty.')

	def write_json(self, source:str=None, target:str=None):
		'''
		Writes mxml as json format.
		@param source: Input mxml file path or formatted text. If none, uses current data
		@param target: Output file path. If None, uses the template as name
		'''
		if source is not None: self.parse(source)
		if len(self) > 0:
			if target is None:
				target = (self['template'] if 'template' in self else 'mxdict_section') + '.json'
			with open(target, 'w') as f:
				f.write(jdumps(self))
		else:
			print('mxdictionary is empty.')

def main():
	mxd = mxdict(casting=True)

	mxd.write_json('D:/MODZ_stuff/NoMansSky/UNPACKED/METADATA/REALITY/TABLES/nms_reality_gctechnologytable.mxml', 'D:/_dump/nms_reality_gctechnologytable.json')

	# mxd.parse('D:/MODZ_stuff/NoMansSky/UNPACKED/METADATA/REALITY/TABLES/REWARDTABLE.mxml')
	# mxd.write_mxml('D:/_dump/REWARDTABLE.mxml')
	# mxd.write_json('D:/MODZ_stuff/NoMansSky/UNPACKED/METADATA/REALITY/TABLES/REWARDTABLE.mxml', 'D:/_dump/REWARDTABLE.json')


	# mxd.parse('D:/_Dump/playercharacter.entity.mxml')
	# mxd.write_mxml('D:/_Dump/playercharacter.entity_processed.mxml')

	print('\n... Processing Done :)')

if __name__ == '__main__': main()
