from tika import parser as tkpr
from pandas import DataFrame, concat
import re

class Extract():
    def __init__(self, search_ptts: list, **kwargs) -> None:
        for key, val in kwargs.items():
            setattr(self, key, val)

        self.search_ptts   :dict    = search_ptts
        self.properties    :dict    = {key:{} for key in kwargs.keys()} # {area_name: {field_name: value}

    # METHODS #####################################################
    def set_properties(self, dct: dict):
        for area, keywords in dct.items():
            text = getattr(self, area)

            for word in keywords:
                cmp = re.compile(self.search_ptts[area] % word)
                srch = cmp.search(text)

                if not srch: continue
                key = srch.groupdict().get('name', None)
                val = srch.groupdict()['value'].strip()
                dct = {key: val}

                self.properties[area].update(dct)
    
    def get_word_list(self, area):
        text = getattr(self, area)

        cmp = re.compile('\s[^0-9,-]*')
        lst = [res.strip() for res in cmp.findall(text) if res not in ['\n/', '\\', ' ', '/']]
        return list(filter(None, lst))
        

    
class Entity():
    def __init__(self, pk: str) -> None:
        self.pk             :str             = pk
        self.extracts       :list[Extract]   = []
        self.dataframe      :DataFrame       = None

    # METHODS #####################################################
    def group_extracts(self, extract_lst: list, pk_name: str, pk_area: str):
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
        # self.dataframe = self.dataframe.groupby(['Data de Crédito']).sum()

class Document():
    def __init__(self, file_path: str, file_name: str, pattern_dcts_lst: str) -> None:

        # Extract and process natural text
        natural_text   :str    = tkpr.from_file(f'{file_path}/{file_name}.pdf')['content']
        line_lst       :list   = []

        for ln in natural_text.split('\n'):
            if ln == '': continue
            line_lst.append(ln.strip())
        
        # Set variables
        self.name      :str    = file_name
        self.text      :str    = '\n'.join(line_lst)
        self.entities  :list   = []
        self.extracts  :list   = []

        for ptt_dct in pattern_dcts_lst:
            ptt_dct: dict
            text_ptt = ptt_dct.pop('text')
            self.set_extracts(text_ptt, ptt_dct)

    # METHODS #####################################################
    def set_extracts(self, text_pattern: str, search_patterns: dict):
        """Extract useful text from this Document's text."""
        for res in re.finditer(text_pattern, self.text, flags=re.M):
            self.extracts.append(Extract(search_patterns, **res.groupdict()))
    
    def set_entities(self, pk_name: str, pk_area: str):
        """Setup a new Entity for every key in a list of primary keys."""
        pk_list = set([ext.properties[pk_area][pk_name] for ext in self.extracts])
        self.entities = [Entity(pk) for pk in pk_list]

    def get_word_list(self, area: str, avoid: str):
        """Get list of words within a certain area in all extracts."""
        big_lst = []
        for ext in self.extracts:
            ext: Extract
            big_lst = big_lst + ext.get_word_list(area)
        big_lst = list(set(big_lst))

        filter_words = lambda wrd: wrd if not any(av in wrd for av in avoid) and len(wrd) > 2 else None
        return list(filter(filter_words, big_lst))





from os import path
root = path.dirname(__file__)
pattern_lst = [
{'text': """(?P<header>Demonstrativo de Pagamento(?:.*\n)*?Agência Crédito: .*)
(?P<body>(?:.*\n)*?BASES \/ Depósito FGTS.*)
(?P<footer>INSS: (?:.*\n)*?FGTS: .*)""",
'header': "(?P<name>%s):?(?:[:]?\s*)(?P<value>[\dA-z,.\/\s-]*?\n|[\dA-z-.,*\/]*)",
'body': "(?P<name>%s):?.*?(?P<value>[0-9.,]*)\n"},

{'text':"""(?P<header>Demostrativo de Pagamento(?:.*\n)*?Ag.Crédito: .*)
(?P<body>(?:.*\n)*?LÍQUIDO CREDITADO EM CONTA.*)
(?P<footer>INSS:(?:\s?.*\n)*?FGTS:\s?.*)""",
'header': "(?P<name>%s):?(?:[:]?\s*)(?P<value>[\dA-z,.\/\s-]*?\n|[\dA-z-.,*\/]*)",
'body': "(?P<name>%s):?.*?(?P<value>[0-9.,]*)\n"}
]

search_data = {'header': ['Data de Crédito', 'Nº pessoal'], 
               'body': ['Ordenado', 'REEMB.FERIAS', 'Adiant.Vale Transporte']}
pk_data = ('Nº pessoal', 'header')

ext: Extract
ent: Entity

doc = Document(f'{root}/documents/', 'simple2', pattern_lst)
avoid_words = ['DESCONTOS', 'TOTAL', 'LIQUIDO', '/', 'NUM.', 'VALOR']
for word in doc.get_word_list('body', avoid_words):
    print(word)

for ext in doc.extracts:
    ext.set_properties(search_data)

doc.set_entities(*pk_data)
for ent in doc.entities:
    ent.group_extracts(doc.extracts, *pk_data)
    ent.build_dataframe(search_data)
    
    print(ent.dataframe)
