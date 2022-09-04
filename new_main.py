from os import path as os_path, listdir as os_listdir
from app_classes import Document, Entity, Extract
from aux_funcs import format_date, format_number
from configparser import ConfigParser
from xlwings import App, Book, Sheet
from datetime import datetime
from pandas import DataFrame

import re

PATH = os_path.dirname(__file__)
CONFIG = ConfigParser()
CONFIG.read_file(open(f'{PATH}/app/config.ini', "r", encoding="utf8"))

def from_ini():

    pattern_dct_lst = []
    for title, dct in CONFIG.items():
        if 'LAYOUT_' in title:
            main_dct = {key: val for key, val in dct.items() if '_search' not in key}
            aux_dct = {key: val for key, val in dct.items() if '_search' in key}
            
            for key in main_dct:
                if f'{key}_search' in aux_dct.keys():
                    main_dct[key] = (main_dct[key], aux_dct[f'{key}_search'])
            pattern_dct_lst.append(main_dct)
    return pattern_dct_lst

def from_gui(label: str):
    avoid_words = ['DESCONTOS', 'TOTAL', 'LIQUIDO', '/', 'NUM.', 'VALOR']
    pk_data = ('header', 'Nº pessoal')
    search_data = {'header': ['Data de Crédito', 'Nº pessoal'], 
                'body': ['Ordenado', 'Reemb.Férias no Mês', 'Adiant.Vale Transporte', 'ORDENADO']}
    if label == 'avoid_words':
        return avoid_words
    elif label == 'primary_key':
        return pk_data
    elif label == 'search_data':
        return search_data

def analyze(folder_path: str):
    """Pre-process the text by setting up extracts and acquiring lists of words."""
    
    files = [(folder_path, file_name) for file_name in os_listdir(folder_path) if '.pdf' in file_name]
    avoid_words = from_gui('avoid_words')
    pattern_dct = from_ini()

    doc_lst  = [Document(path, name) for (path, name) in files]
    for doc in doc_lst:
        for dct in pattern_dct:
            area_lst = list(re.compile(dct['layout'], re.M).groupindex.keys())
            doc.set_extracts(dct['MAIN'])
            doc.set_words(area_lst, avoid_words, dct)
    return doc_lst

def extract(doc_lst: list):
    """Extract data from the the document and send it to excel."""
    doc: Document; ent: Entity; ext: Extract

    pk_data = from_gui('primary_key')
    search_data = from_gui('search_data')
    
    for doc in doc_lst:
        if doc.name == 'teste.pdf': search_data['header'][1] = 'Nºpessoal'
        if doc.name == 'teste.pdf': pk_data = ('header', 'Nºpessoal')
        # Data processing
        for ext in doc.extracts:
            ext.set_properties(search_data)

        # Data grouping
        doc.set_entities(*pk_data)
        for ent in doc.entities:
            ent.gather_extracts(doc.extracts, *pk_data)
            ent.build_dataframe(search_data)
            dataframe = treat_dataframe(ent.dataframe, 'Data de Crédito')
            to_excel(dataframe, doc.name.replace('.pdf', ''), ent.pk)

def treat_dataframe(dataframe: DataFrame, date_col: str):
    avoid_cols = ['YEAR', 'MONTH'] + [date_col]

    dataframe = dataframe.fillna('0')
    dataframe[date_col] = dataframe[date_col].apply(format_date)
    dataframe['MONTH'] = dataframe[date_col].apply(lambda val: val.month)
    dataframe['YEAR'] = dataframe[date_col].apply(lambda val: val.year)
    dataframe = dataframe.reindex(columns=['YEAR', 'MONTH'] + [col for col in dataframe.columns if col not in avoid_cols])

    for col in [col for col in dataframe.columns if col not in avoid_cols]:
        dataframe[col] = dataframe[col].apply(format_number)

    dataframe = dataframe.drop_duplicates()
    dataframe = dataframe.sort_values(['YEAR', 'MONTH'])
    dataframe = dataframe.reset_index(drop=True)
    return dataframe

def to_excel(dataframe: DataFrame, doc_name: str, ent_id: str):
    """Write data to excel."""
    wb: Book; ws: Sheet

    TIMESTAMP = str(datetime.now().strftime('%y-%m-%d %H:%M')).replace(' ', 'T').replace(':', '-')
    
    # Setup excel
    App(visible=False)
    wb = Book()
    ws = wb.sheets[0]
    try:
        # Format table headers
        ws.range(f'A1').value = list(dataframe.columns)
        ws.range(f'A1:AAA1').font.bold = True
        ws.range(f'A1:AAA1').font.size = 14

        # Write data
        pos = 2
        for year in dataframe['YEAR'].unique():
            slice = dataframe[dataframe['YEAR']==year]
            ws.range(f'A{pos}').options(index=False, header=False).value = slice
            pos += len(slice.index)+1

        # Fit columns and rows
        for ws in wb.sheets:
                ws.autofit(axis="columns")
                ws.autofit(axis="rows")

        # Save
        wb.save(f'{PATH}/spreadsheets/{TIMESTAMP}__{doc_name}__{ent_id}.xlsx')
    except:
        pass
    finally:
        wb.close()


docs = analyze(f'{PATH}/documents/')       # Used by GUI access word lists in each document
extract(docs)                              # This happens when you click EXTRACT