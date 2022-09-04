from pandas import DataFrame, concat
from tika import parser as tkpr

import re

AVOID_KEYS = ['layout', 'pk_area', 'pk_name']

class Extract():
    def __init__(self, query_patterns: list, **kwargs) -> None:
        for key, val in kwargs.items():
            setattr(self, key, val)

        self.query_ptts    :dict    = query_patterns
        self.properties    :dict    = {key:{} for key in kwargs.keys()} # {area_name: {field_name: value}

    # METHODS #####################################################
    def set_properties(self, search_data: dict):
        """Set properties for all items in a dictionary given in a key:word_list pattern."""
        for area, keywords in search_data.items():
            text = getattr(self, area)

            for word in keywords:
                cmp = re.compile(self.query_ptts[area].format(word))
                srch = cmp.search(text)

                if not srch: continue
                key = srch.groupdict().get('name', None)
                val = srch.groupdict()['value'].strip()
                self.properties[area].update({key: val})
    
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
    def gather_extracts(self, extract_lst: list, pk_area: str, pk_name: str):
        """Group Extract objects onto corresponding Entity."""
        for ext in extract_lst:
            if ext.properties[pk_area][pk_name] == self.pk:
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
        natural_text   :str    = tkpr.from_file(f'{path}/{name}')['content']
        line_lst       :list   = []

        for ln in natural_text.split('\n'):
            if ln == '': continue
            line_lst.append(ln.strip())

        self.name      :str    = name
        self.text      :str    = '\n'.join(line_lst)
        self.entities  :list   = []
        self.extracts  :list   = []
        self.word_dct  :list   = {}

    # METHODS #####################################################
    def set_extracts(self, pattern_dct: dict):
        """Set Extracts containing useful text from this Document's text."""
        layout_pattern = re.compile(pattern_dct['layout'], re.M)
        query_patterns = {key: val[0] for key, val in pattern_dct.items() if key != 'layout'}

        for res in re.finditer(layout_pattern, self.text):
            self.extracts.append(Extract(query_patterns, **res.groupdict()))
    
    def set_entities(self, pk_area: str, pk_name: str):
        """Setup a new Entity for every key in a list of primary keys."""
        pk_list = set([ext.properties[pk_area][pk_name] for ext in self.extracts])
        self.entities = [Entity(pk) for pk in pk_list]

    def set_words(self, area_lst: list, avoid: list, pattern_dct: dict):
        """Get list of words within a certain area in all extracts."""
        ext: Extract

        filter_word = lambda word: word if not any(av in word for av in avoid) and len(word) > 2 else None
        self.word_dct = {area: [] for area in area_lst if area != 'layout'}

        for area in area_lst:
            if area == 'layout': continue
            if pattern_dct.get(area, None) is None: continue

            for ext in self.extracts:
                words =  ext.acquire_words(area, pattern_dct[area][1])
                words = list(filter(filter_word, words))
                self.word_dct[area] += words

            self.word_dct[area] = list(set(self.word_dct[area]))
