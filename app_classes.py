from tika import parser as tkpr
from pandas import DataFrame, concat
import re

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
                cmp = re.compile(self.query_ptts[area] % word)
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

    def build_dataframe(self, dct: dict):
        """From a dictionary in pattern area:keywords, build a dataframe containing
        all of this Entity's Extract objects properties."""
        df_lst = []
        for area, keywords in dct.items():
            data = [ext.properties[area] for ext in self.extracts if ext.properties[area] != {}]
            df_lst.append(DataFrame(data, columns=keywords))
        self.dataframe = concat(df_lst, axis=1)

class Document():
    def __init__(self, file_path: str, file_name: str) -> None:
        natural_text   :str    = tkpr.from_file(f'{file_path}/{file_name}.pdf')['content']
        line_lst       :list   = []

        for ln in natural_text.split('\n'):
            if ln == '': continue
            line_lst.append(ln.strip())

        self.name      :str    = file_name
        self.text      :str    = '\n'.join(line_lst)
        self.entities  :list   = []
        self.extracts  :list   = []
        self.word_dct  :list   = {}

    # METHODS #####################################################
    def set_extracts(self, pattern_dct: dict):
        """Set Extracts containing useful text from this Document's text."""
        layout_pattern = re.compile(pattern_dct.pop('layout'), re.M)
        query_patterns = {key: val[0] for key, val in pattern_dct.items()}

        for res in re.finditer(layout_pattern, self.text):
            self.extracts.append(Extract(query_patterns, **res.groupdict()))
    
    def set_entities(self, pk_area: str, pk_name: str):
        """Setup a new Entity for every key in a list of primary keys."""
        pk_list = set([ext.properties[pk_area][pk_name] for ext in self.extracts])
        self.entities = [Entity(pk) for pk in pk_list]

    def set_words(self, search_data: dict, avoid: list, pattern_dct: dict):
        """Get list of words within a certain area in all extracts."""
        filter_word = lambda word: word if not any(av in word for av in avoid) and len(word) > 2 else None
        ext: Extract

        area_lst = list(search_data.keys())
        word_patterns = {key: val[1] for key, val in pattern_dct.items()}
        self.word_dct = {area: [] for area in area_lst}
        
        for area in area_lst:
            for ext in self.extracts:
                words = list(filter(filter_word, ext.acquire_words(area, word_patterns[area])))
                self.word_dct[area] += words
            self.word_dct[area] = list(set(self.word_dct[area]))





from os import path
root = path.dirname(__file__)

ext: Extract
ent: Entity
pattern_dct: dict

# From CONFIG.INI
pattern_dct_lst = [
{'layout': """(?P<header>Demonstrativo de Pagamento(?:.*\n)*?Agência Crédito: .*)
(?P<body>(?:.*\n)*?BASES \/ Depósito FGTS.*)
(?P<footer>INSS: (?:.*\n)*?FGTS: .*)""",
'header': ("(?P<name>%s):?(?:[:]?\s*)(?P<value>[\dA-z,.\/\s-]*?\n|[\dA-z-.,*\/]*)",     "[A-Z].+?:"),
'body': ("(?P<name>%s):?.*?(?P<value>[0-9.,]*)\n",                                      "\s[^0-9,-]*")
},

{'layout': """(?P<header>Demostrativo de Pagamento(?:.*\n)*?Ag.Crédito: .*)
(?P<body>(?:.*\n)*?LÍQUIDO CREDITADO EM CONTA.*)
(?P<footer>INSS:(?:\s?.*\n)*?FGTS:\s?.*)""",
'header': ("(?P<name>%s):?(?:[:]?\s*)(?P<value>[\dA-z,.\/\s-]*?\n|[\dA-z-.,*\/]*)",     "[A-Z].+?:"),
'body': ("(?P<name>%s):?.*?(?P<value>[0-9.,]*)\n",                                      "\s[^0-9,-]*")
}
]

# From GUI
pk_data = ('header', 'Nº pessoal')
search_data = {'header': ['Data de Crédito', 'Nº pessoal'], 
               'body': ['Ordenado', 'Reemb.Férias no Mês', 'Adiant.Vale Transporte']}
avoid_words = ['DESCONTOS', 'TOTAL', 'LIQUIDO', '/', 'NUM.', 'VALOR']

# Acquisition & pre-processing ################################
doc = Document(f'{root}/documents/', 'simple2')
for pattern_dct in pattern_dct_lst:
    doc.set_extracts(pattern_dct)
    doc.set_words(search_data, avoid_words, pattern_dct)

# Data processing #############################################
for ext in doc.extracts:
    ext.set_properties(search_data)

# Data grouping ###############################################
doc.set_entities(*pk_data)
for ent in doc.entities:
    ent.gather_extracts(doc.extracts, *pk_data)
    ent.build_dataframe(search_data)
    print(ent.dataframe)