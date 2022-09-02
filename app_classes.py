from tika import parser as tkpr
from pandas import DataFrame, concat
import re

class Extract():
    def __init__(self, **kwargs) -> None:
        for key, val in kwargs.items():
            setattr(self, key, val)
        
        self.properties    :dict    = {key:{} for key in kwargs.keys()} # {area_name: {field_name: value}

    # METHODS #####################################################
    def set_properties(self, dct: dict):
        for area, (pattern, keywords) in dct.items():
            text = getattr(self, area)

            for word in keywords:
                cmp = re.compile(pattern % word)
                mtc = cmp.search(text)

                if not mtc: continue
                key = mtc.groupdict().get('name', None)
                val = mtc.groupdict()['value'].strip()
                dct = {key: val}

                self.properties[area].update(dct)
    
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

class Document():
    def __init__(self, file_path: str, file_name: str, text_pattern: str) -> None:

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

        self.set_extracts(text_pattern)

    # METHODS #####################################################
    def set_extracts(self, pattern: str):
        """Extract useful text from this Document's text."""
        for res in re.finditer(pattern, self.text, flags=re.M):
            self.extracts.append(Extract(**res.groupdict()))
    
    def set_entities(self, pk_name: str, pk_area: str):
        """Setup a new Entity for every key in a list of primary keys."""
        pk_list = set([ext.properties[pk_area][pk_name] for ext in self.extracts])
        self.entities = [Entity(pk) for pk in pk_list]




from os import path
root = path.dirname(__file__)

txt_ptt = """(?P<header>Demostrativo de Pagamento(?:.*\n)*?Ag.Crédito: .*)
(?P<body>(?:.*\n)*?LÍQUIDO CREDITADO EM CONTA.*)
(?P<footer>INSS:(?:\s?.*\n)*?FGTS:\s?.*)"""
header_ptt = "(?P<name>%s):?(?:[:]?\s*)(?P<value>[\dA-z,.\/\s-]*?\n|[\dA-z-.,*\/]*)"
body_ptt = "(?P<name>%s):?.*?(?P<value>[0-9.,]*)\n"


doc = Document(f'{root}/documents/', 'teste', txt_ptt)
for ext in doc.extracts:
    ext: Extract
    ext.set_properties({'header': (header_ptt, ['Data de Crédito', 'Nºpessoal']), 
                         'body': (body_ptt, ['ORDENADO', 'REEMB.FERIAS', 'ADIANT.VALE TRANSPORTE'])})

doc.set_entities('Nºpessoal', 'header')
for ent in doc.entities:
    ent: Entity
    ent.group_extracts(doc.extracts, 'Nºpessoal', 'header')
    body = ent.build_dataframe({'header': ['Data de Crédito', 'Nºpessoal'],
                                'body': ['ORDENADO', 'REEMB.FERIAS', 'ADIANT.VALE TRANSPORTE']})
    print(ent.dataframe)
