from pandas import DataFrame, concat
from tika import parser as tkpr

import re

class Extract():
    def __init__(self, layout_info: dict, query_ptts: list, **kwargs) -> None:
        for key, val in kwargs.items():
            setattr(self, key, val)

        self.layout_name   :str     = layout_info['layout_name']
        self.pk_area       :str     = layout_info['primary_key_area']
        self.pk_key        :str     = layout_info['primary_key_name']
        self.query_ptts    :dict    = query_ptts

        self.pk            :str     = None
        self.keywords      :dict    = {}
        self.properties    :dict    = {key:{} for key in kwargs.keys()} # {area_name: {field_name: value}

    # METHODS #####################################################
    def acquire_words(self, area: str, pattern: str):
        """Get a list of all field words in an area."""
        
        text = getattr(self, area)
        cmp = re.compile(pattern, re.M)
        words = [wrd.strip() for wrd in cmp.findall(text) 
                    if wrd not in ['\n/', '\\', ' ', '/', None] 
                    and len(wrd.strip()) > 2]

        if area not in self.keywords.keys():
            self.keywords[area] = []

        for wrd in words:
            wrd = wrd.strip()
            if wrd not in self.keywords[area]:
                self.keywords[area].append(wrd.strip())
        return self.keywords[area]

    def set_properties(self):
        """Set properties for all items in a dictionary given in a key:word_list pattern."""

        for area, keywords in self.keywords.items():
            text = getattr(self, area)

            for word in keywords:
                cmp = re.compile(self.query_ptts[area].format(word), re.M)
                srch = cmp.search(text)

                if not srch: continue
                
                key = srch.groupdict()['name'].strip()
                val = srch.groupdict()['value'].strip()

                self.properties[area].update({key: val})

        self.pk = self.properties[self.pk_area][self.pk_key]


class Document():
    def __init__(self, file_path: str, file_name: str) -> None:
        self.natural_text   :str    = tkpr.from_file(f'{file_path}/{file_name}')['content']
        text_lines       :list   = []

        for ln in self.natural_text.split('\n'):
            if ln == '': continue
            text_lines.append(ln.strip())

        self.name      :str    = file_name.replace('.pdf', '')
        self.text      :str    = '\n'.join(text_lines)
        self.entities  :list   = []
        self.extracts  :list   = []
        self.keywords  :list   = {}

    # METHODS #####################################################
    def set_extracts(self, extraction_pattern: dict, querying_patterns: dict, layout_info: dict):
        """Set Extracts containing useful text from this Document's text."""

        layout_pattern = re.compile(extraction_pattern['layout'])

        for match in re.finditer(layout_pattern, self.text):
            self.extracts.append(
                Extract(layout_info, querying_patterns, **match.groupdict())
            )
    
    def set_keywords(self, pre_processing_patterns: dict):
        """Use regular expressions to acquire a list of keywords for an area."""
        ext: Extract
        
        self.keywords.update({area: [] for area in pre_processing_patterns.keys() if area not in self.keywords.keys()})
        for area, pattern in pre_processing_patterns.items():
            for ext in self.extracts:
                words =  ext.acquire_words(area, pattern)
                self.keywords[area] += words
            self.keywords[area] = list(set(self.keywords[area]))

    def remove_keywords_from_extracts(self, words_to_keep: dict, words_to_filter: list):
        """Remove keywords from each Extract."""
        ext: Extract

        def _word_filter(word: str, words_to_filter: list):
            if any(av in word for av in words_to_filter) and len(word) <= 2: 
                return None
            return word

        for ext in self.extracts:
            for area, word_lst in ext.keywords.items():
                new_wrd_lst = (wrd for wrd in word_lst if wrd in words_to_keep[area])
                new_wrd_lst = [wrd for wrd in new_wrd_lst if _word_filter(wrd, words_to_filter) is not None]
                ext.keywords[area] = new_wrd_lst


    def set_entities(self):
        """Setup a new Entity for every key in a list of primary keys."""

        primary_keys = set([ext.pk for ext in self.extracts])
        self.entities = [Entity(pk) for pk in primary_keys]


class Entity():
    def __init__(self, pk: str) -> None:
        self.pk             :str             = pk
        self.extracts       :list[Extract]   = []
        self.dataframe      :DataFrame       = DataFrame()
        self.keywords       :dict            = {}

    # METHODS #####################################################
    def gather_extracts(self, extract_lst: list):
        """Group Extract objects onto corresponding Entity."""
        ext: Extract

        for ext in extract_lst:
            if ext.pk == self.pk:
                self.extracts.append(ext)

    def collect_words_from_extracts(self):
        """Get all keywords from this Entity's Extract objects."""

        for ext in self.extracts:
            for area, word_lst in ext.keywords.items():
                if area not in self.keywords:
                    self.keywords[area] = word_lst
                else:
                    self.keywords[area] += [word for word in word_lst if word not in self.keywords[area]]

    def build_dataframe(self):
        """From a dictionary in pattern area:keywords, build a dataframe containing
        all of this Entity's Extract objects properties."""

        dfs = []
        for area, words in self.keywords.items():
            data = [ext.properties[area] for ext in self.extracts if ext.properties[area] != {}]
            dfs.append(DataFrame(data, columns=words))

        self.dataframe = concat(dfs, axis=1)
        self.dataframe = self.dataframe.loc[:,~self.dataframe.columns.duplicated()]