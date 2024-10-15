import xml.etree.ElementTree as ET
from json import dumps as jdumps
from os.path import exists

class exdict(dict):
	'''
	Parse a No Man's Sky exml file and convert it to a working dictionary
	@param exml: [optional] Either an exml-formatted string or a [*.exml] file path
	@param casting: [optional] cast values to appropriate types. All are strings if False
	'''
	def __init__(self, exml:str=None, casting:bool=False):
		self.__exml = exml
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
	def exml(self) -> str:
		''' Either an exml-formatted string or a [*.exml] file path '''
		return self.__exml
	@exml.setter
	def exml(self, e): self.__exml = e

	def parse(self, exml:str=None) -> dict:
		'''
		Parse exml text into a dictionary
		Internal dict will be cleared before the process
		@param exml: Either an exml-formatted string or a [*.exml] file path
		'''
		self.clear()
		if exml: self.exml = exml
		try:
			if self.exml.lower().endswith('.exml'): # switch string or file
				if exists(self.exml):
					t = ET.parse(self.exml).getroot()
					return self.__to_dict(t, self)
				else:
					print('File not found!')
			else:
				t = ET.fromstring(self.exml)
				return self.__to_dict(t, self)
		except ET.ParseError as e:
			print(f'Parsing encountered an error! {e.args}')

	def	__eval(self, val:str):
		''' evaluate value and cast to appropriate type '''
		try:
			if val.count('.') > 0:
				return float(val)
			else:
				return int(val)
		except ValueError:
			if val == 'True': return True
			if val == 'False': return False
			return val

	def	__attr(self, n):
		'''
		Return values from node attributes (skipping the useless tags)
		cast values to real types (optional with class flag 'casting')
		'''
		if len(n) > 1:
			return n['name'], self.__eval(n['value']) if self.__cast else n['value']
		elif len(n) > 0:
			if 'name'	  in n: return 'name',	   n['name']
			if 'value'	  in n: return 'value',	   self.__eval(n['value']) if self.__cast else n['value']
			if 'template' in n: return 'template', n['template']
		return None

	def __to_dict(self, tree, dct):
		'''
		Traverse exml file or sections and build an equivalent dictionary
		'''
		k, v = self.__attr(tree.attrib)
		if k == 'template':
			dct[k] = v
		else:
			dct['meta'] = (k, v)

		for node in tree:
			k, v = self.__attr(node.attrib)
			if len(node) > 0:
				current = exdict({'meta': (k, v)}, casting=self.__cast)
				# value section: open new dict
				if 'meta' in dct and dct['meta'][0] != 'name' or 'template' in dct:
					dct[v if k == 'name' else k] = current
				else:
				# Inside 'name' list. can't risk overwriting keys
				# add sequential keys just like lua ;)
					dct[str(len(dct)-1)] = current

				self.__to_dict(node, current)
			else:
				if k == 'value':
				# non-named values
					dct[str(len(dct)-1)] = v
				elif k == 'name':
				# empty list stub
					dct[v] = None
				else:
				# regular property
					dct[k] = v

		return dct

	def	to_exml(self) -> str:
		'''
		Convert dictionary to an exml string
		'''
		if 'template' in self:
			root = ET.Element('Data', attrib={'template': self['template']})
			return ET.tostring(self.__to_tree(self, root), encoding='utf-8')
		else:
			# __to_tree needs another containing dict to loop through the first one
			return ET.tostring(self.__to_tree({'faux_container': self}), encoding='unicode')

	def	__to_tree(self, dct, tree=None) -> ET.Element:
		'''
		Build exml format from dictionary
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
					# 1-attribute : new list
					else:
						attribs = {'value' if att2 else 'name': key}

					node.attrib = attribs
					self.__to_tree(cls, node)
				# add properties
				else:
					if key.isnumeric():
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

	def	one_liner(self, sep:str=',') -> str:
		'''
		Returns all values in the dict joined in a string, or None if empty
		@param sep: Separator between values
		'''
		def	liner(exd):
			values = []
			if isinstance(exd, dict):
				for _,o in exd.data_items(): values += liner(o)
			else:
				values.append(exd)
			return values

		if len(self) > 0:
			ds = liner(self)
			if len(ds) == 1 and (ds[0] is None):
				return None
			return sep.join([str(s) for s in ds])
		else:
			return None

	def write_exml(self, target:str):
		'''
		Writes dictionary back to exml file
		@param target: Output exml file path
		'''
		if len(self) > 0:
			with open(target, 'wb') as f: f.write(self.to_exml())
		else:
			print('exdictionary is empty.')

	def write_json(self, source:str=None, target:str=None):
		'''
		Writes exml as json format.
		@param source: Input exml file path or formatted text. If none, uses current data
		@param target: Output file path. If None, uses the template as name
		'''
		if source is not None: self.parse(source)
		if len(self) > 0:
			if target is None:
				target = (self['template'] if 'template' in self else 'exdict_section') + '.json'
			with open(target, 'w') as f:
				f.write(jdumps(self))
		else:
			print('exdictionary is empty.')

def main():
	exd = exdict(casting=True)

	# load an exml for work
	exd.parse('C:/NMS_UNPACKED/METADATA/REALITY/TABLES/REWARDTABLE.EXML')

	# convert dictionary back to EXML
	exd.write_exml('C:/TEMP/REWARDTABLE.EXML')

	# convert and save EXML to JSON (an aid to see the data's layout)
	exd.write_json('C:/NMS_UNPACKED/METADATA/REALITY/TABLES/REWARDTABLE.EXML', 'C:/NMS_UNPACKED/REWARDTABLE.json')

	print('\n... Processing Done :)')

if __name__ == '__main__': main()
