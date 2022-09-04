from pandas import DataFrame, concat
from tika import parser as tkpr

import re

class Extract():
    def __init__(self, pk_data: dict, query_ptts: list, **kwargs) -> None:
        for key, val in kwargs.items():
            setattr(self, key, val)

        self.pk_area       :str     = pk_data['area']
        self.pk_key        :str     = pk_data['key']
        self.pk            :str     = None

        self.query_ptts    :dict    = query_ptts
        self.properties    :dict    = {key:{} for key in kwargs.keys()} # {area_name: {field_name: value}

    # METHODS #####################################################
    def set_properties(self, search_data: dict):
        """Set properties for all items in a dictionary given in a key:word_list pattern."""
        
        search_data[self.pk_area].insert(0, self.pk_key)
        
        for area, keywords in search_data.items():
            text = getattr(self, area)

            for word in keywords:
                cmp = re.compile(self.query_ptts[area].format(word))
                srch = cmp.search(text)

                if not srch: continue
                key = srch.groupdict().get('name', None)
                val = srch.groupdict()['value'].strip()
                self.properties[area].update({key: val})
        
        del search_data[self.pk_area][0]
        self.pk = self.properties[self.pk_area][self.pk_key]
    
    def acquire_words(self, area: str, pattern: str):
        """Get a list of all field words in an area."""
        text = getattr(self, area)
        cmp = re.compile(pattern)
        lst = [res.strip() for res in cmp.findall(text) if res not in ['\n/', '\\', ' ', '/']]
        return list(filter(None, lst))
        
class Entity():
    def __init__(self, pk: str) -> None:
        self.pk             :str             = pk
        self.extracts       :list[Extract]   = []
        self.dataframe      :DataFrame       = None

    # METHODS #####################################################
    def gather_extracts(self, extract_lst: list):
        """Group Extract objects onto corresponding Entity."""
        for ext in extract_lst:
            if ext.pk == self.pk:
                self.extracts.append(ext)

    def build_dataframe(self, search_data: dict):
        """From a dictionary in pattern area:keywords, build a dataframe containing
        all of this Entity's Extract objects properties."""
        df_lst = []
        for area, keywords in search_data.items():
            data = [ext.properties[area] for ext in self.extracts if ext.properties[area] != {}]
            df_lst.append(DataFrame(data, columns=keywords))
        self.dataframe = concat(df_lst, axis=1)

class Document():
    def __init__(self, path: str, name: str) -> None:
        self.natural_text   :str    = tkpr.from_file(f'{path}/{name}')['content']
        line_lst       :list   = []

        for ln in self.natural_text.split('\n'):
            if ln == '': continue
            line_lst.append(ln.strip())

        self.name      :str    = name.replace('.pdf', '')
        self.text      :str    = '\n'.join(line_lst)
        self.entities  :list   = []
        self.extracts  :list   = []
        self.word_dct  :list   = {}

    # METHODS #####################################################
    def set_extracts(self, dct: dict):
        """Set Extracts containing useful text from this Document's text."""
        layout_pattern = re.compile(dct['MAIN']['layout'], re.M)
        query_patterns = {key: val for key, val in dct['MAIN'].items() if key != 'layout'}
        pk_data = dct['PK']

        for res in re.finditer(layout_pattern, self.text):
            self.extracts.append(Extract(pk_data, query_patterns, **res.groupdict()))
    
    def set_entities(self):
        """Setup a new Entity for every key in a list of primary keys."""
        pk_list = set([ext.pk for ext in self.extracts])
        self.entities = [Entity(pk) for pk in pk_list]

    def set_words(self, dct: dict, avoid: list):
        """Get list of words within a certain area in all extracts."""
        filter_word = lambda word: word if not any(av in word for av in avoid) and len(word) > 2 else None

        self.word_dct = {area: [] for area in dct.keys()}

        ext: Extract
        for area in dct.keys():
            for ext in self.extracts:
                words =  ext.acquire_words(area, dct[area])
                words = list(filter(filter_word, words))
                self.word_dct[area] += words

            self.word_dct[area] = list(set(self.word_dct[area]))


