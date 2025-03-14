import xml.etree.ElementTree as ET
from json import dumps as jdumps
from os.path import exists

__author__	= 'lMonk'
__version__	= '1.3.01'

class meta:
	'''
	Manage class attributes and helper functions
	'''
	def __init__(self, attr:dict=None):
		self.__attrib = attr.copy()

	@property
	def name(self):
		return self.__attrib['name'] if 'name' in self.__attrib else False
	@property
	def value(self):
		return self.__attrib['value'] if 'value' in self.__attrib else False
	@property
	def template(self):
		return self.__attrib['template'] if 'template' in self.__attrib else False
	@property
	def id(self):
		return self.__attrib['_id'] if '_id' in self.__attrib else False
	@property
	def index(self):
		return self.__attrib['_index'] if '_index' in self.__attrib else False
	@property
	def cls(self):
		return 'name' in self.__attrib and (
			self.__attrib['name'].startswith('Gc') or \
			self.__attrib['name'].startswith('Tk') or \
			len(self.__attrib) > 1
		)
	@property
	def lst(self):
		return len(self.__attrib) == 1

class mxdict(dict):
	'''
	Parses a No Man's Sky mxml file and converts it to a working searchable dictionary,
	Sets class and value names as unique keys wherever possible for direct access.
	'''
	def __init__(self, mxml:str=None, casting:bool=False, use_id:bool=False, ext:dict=None):
		'''
		@param mxml: [optional] Either an mxml-formatted string or a [*.mxml] file path
		@param casting: [optional] cast values to appropriate types. All are strings if False
		@param use_id: [optional] Use the _id attribute as dictionary keys where available
		@param ext: [optional] Import values from an external dictionary
		'''
		self.__mxml = mxml
		self.__cast = casting
		self.__useid = use_id
		if ext is not None: self.update(ext)

	@property
	def use_id(self) -> bool:
		''' Use _id attribute as dictionary keys '''
		return self.__useid
	@use_id.setter
	def use_id(self, i:bool):
		self.__useid = i

	@property
	def casting(self) -> bool:
		'''
		Evaluates values and casts to appropriate types (enables __eval)
		If False all values in the produced dictionary are represented as strings
		'''
		return self.__cast
	@casting.setter
	def casting(self, c:bool):
		self.__cast = c

	@property
	def mxml(self) -> str:
		''' Either an mxml-formatted string or a [*.mxml] file path '''
		return self.__mxml
	@mxml.setter
	def mxml(self, e):
		self.__mxml = e

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
		Skipped by class flag 'casting'
		'''
		if not self.__cast: return val
		try:
			if val.count('.') > 0:
				return float(val)
			else:
				return int(val)
		except ValueError:
			if val == 'true': return True
			if val == 'false': return False
			return val

	def __to_dict(self, tree, dct):
		'''
		Traverse mxml file or sections and build an equivalent dictionary
		'''
		parent = meta(tree.attrib)
		if parent.template:
			dct['template'] = parent.template
		else:
			dct['meta'] = tree.attrib.copy()

		for nd in tree:
			node = meta(nd.attrib)
			if len(nd) > 0:
				if node.id and self.__useid:
					key = node.id
				elif parent.template or parent.cls:
					key = node.name
				else:
					key = len(dct) - 1

				dct[key] = self.__to_dict(nd, mxdict(casting=self.__cast, use_id=self.__useid))

			else:
				if node.lst:
					# empty list stub
					key = node.name
					val = None
				elif node.name == parent.name and parent.lst:
					# ordered list value
					key = len(dct) - 1
					val = self.__eval(node.value)
				else:
					# regular property
					key = node.name
					val = self.__eval(node.value)

				dct[key] = val

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
				node = ET.SubElement(tree, 'Property')
				if isinstance(cls, dict):
					node.attrib = cls['meta'].copy()
					self.__to_tree(cls, node)
				# add properties
				else:
					if isinstance(key, int):
						# ordered list property
						attribs = {'name': dct['meta']['name'], 'value': str(cls)}
					elif cls is not None:
						# normal property
						attribs = {'name': key, 'value': str(cls)}
					else:
						# list stub
						attribs = {'name': key}

					node.attrib = attribs

		return tree

	def update(self, dct:dict):
		'''
		Overwrites dict.update() to perform deep-copy into self
		while initiating mxdict for sub-dicts
		@param dct: Copy values from an external dictionary
		'''
		for key, val in dct.items():
			if key is None: key = len(self)

			if isinstance(val, dict) and key != 'meta':
				super().update({key: mxdict(casting=self.__cast, use_id=self.__useid, ext=val)})
			else:
				super().update({key: val})

	def append(self, key:str=None, value=''):
		'''
		Add new keyed dictionary value or append to a 'list' with sequential keys
		'''
		if 'meta' in self and 'name' in self['meta']:
			key = len(self) - 1
		self[key] = value

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
					result.append(traverse(dat))
				return sep2.join(result)
			else:
				return str(d)

		if len(self) <= 0: return None

		res = [traverse(dat) for _,dat in self.data_items()]
		if len(res) == 1 and (res[0] is None):
			return None
		# use sep2 if data has a single level
		return (sep1 if res[0].count(sep2) > 0 else sep2).join(res)

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
			print('mxdict is empty.')

def main():
	mxd = mxdict(casting=False, use_id=False)

	mxd.parse('d:/modz_stuff/nomanssky/unpacked/metadata/reality/defaultreality.mxml')
	mxd.write_mxml('D:/_dump/defaultreality.mxml')
	mxd.write_json(target='D:/_dump/defaultreality.json')

	# mxd.parse('D:/MODZ_stuff/NoMansSky/UNPACKED/metadata/reality/tables/rewardtable.mxml')
	# mxd.write_mxml('D:/_dump/rewardtable.mxml')
	# mxd.write_json(target='D:/_dump/rewardtable.json')

	print('\n... Processing Done :)')

if __name__ == '__main__': main()
