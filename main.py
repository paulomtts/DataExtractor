from os import path as os_path, listdir as os_listdir
from app_classes import Document, Entity, Extract
from aux_funcs import format_date, format_number
from configparser import ConfigParser
from xlwings import App, Book, Sheet
from datetime import datetime
from pandas import DataFrame

import requests
import json


PATH = os_path.dirname(__file__)
timestamp = lambda: str(datetime.now().strftime('%y-%m-%dT%H-%M-%S'))

with open(f'{PATH}/app/config.json', encoding='utf-8') as json_file:
    LAYOUT_CONFIGS = json.load(json_file)


# UPDATE METHODS ###########################################################################################
def update_json():
    conf = ConfigParser()
    conf.read(f'{PATH}/app/config.ini')

    id = conf['API']['id']
    
    url = f'https://api.jsonbin.io/v3/b/{id}/'
    headers = {
        'X-Master-Key': conf['API']['X_Master_Key'],
        'X-Bin-Meta': conf['API']['X_Bin_Meta']
    }

    req = requests.get(url, json=None, headers=headers)

    if req.status_code == 200:
        with open(f'{PATH}/app/config.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(req.json(), ensure_ascii=False, indent=4))
    
    return req


# INPUT METHODS ############################################################################################
def pre_process_documents(folder_path: str):
    """Pre-process the text by setting up extracts and acquiring lists of words."""
    
    files = [(folder_path, file_name) for file_name in os_listdir(folder_path) if '.pdf' in file_name]
    documents  = [Document(file_path, file_name) for (file_path, file_name) in files]
    for doc in documents:
        doc: Document
        doc.start()
    doc.join()

    for doc in documents:
        for layout in LAYOUT_CONFIGS.values():
            doc.set_extracts(layout['PATTERNS']['EXTRACTION'], layout['PATTERNS']['QUERYING'], layout['INFO'])
            doc.set_keywords(layout['PATTERNS']['PRE_PROCESSING'])
            
    return documents

def extract_from_text(documents: list, destination_folder: str, words_to_keep: str, words_to_filter: str):
    """Extract data from the the document and send it to excel."""
    doc: Document; ent: Entity; ext: Extract

    for doc in documents:
        with open(f'{PATH}/app/text/processed/{timestamp()}__{doc.name}__prc.txt', 'w', encoding='utf-8') as file:
            file.write(doc.text)

        doc.keep_keywords_from_extracts(words_to_keep, words_to_filter)

        for ext in doc.extracts:
            ext.set_properties()

            with open(f'{PATH}/app/text/extracts/{timestamp()}__{doc.name}__ext.txt', 'a', encoding='utf-8') as file:
                for prop in ext.properties.keys():
                    file.write(getattr(ext, prop) + '\n')
                file.write('----\n')

        doc.set_entities()
        for ent in doc.entities:
            ent.gather_extracts(doc.extracts)
            ent.collect_words_from_extracts()
            ent.build_dataframe()
            dataframe = treat_dataframe(ent.dataframe)
            write_to_excel(dataframe, doc.name, ent.pk.replace('.', ''), destination_folder)


# OUTPUT METHODS ###########################################################################################
def treat_dataframe(dataframe: DataFrame):
    date_column_name = 'Data de Crédito'
    columns_to_avoid = ['YEAR', 'MONTH', 'Nºpessoal', 'Nº pessoal', 'Nº Pessoal'] + [date_column_name]

    dataframe = dataframe.fillna('0')

    dataframe[date_column_name] = dataframe[date_column_name].apply(format_date)
    dataframe['MONTH'] = dataframe[date_column_name].apply(lambda val: val.month)
    dataframe['YEAR'] = dataframe[date_column_name].apply(lambda val: val.year)
    dataframe = dataframe.reindex(columns=['YEAR', 'MONTH'] + [col for col in dataframe.columns if col not in columns_to_avoid])

    for col in [col for col in dataframe.columns if col not in columns_to_avoid]:
        try:
            dataframe[col] = dataframe[col].apply(format_number)
        except:
            continue

    dataframe = dataframe.drop_duplicates()
    dataframe = dataframe.sort_values(['YEAR', 'MONTH'])
    dataframe = dataframe.reset_index(drop=True)

    return dataframe

def write_to_excel(dataframe: DataFrame, doc_name: str, pk: str, destination_folder: str):
    """Write data to excel."""
    wb: Book; ws: Sheet
    
    # Setup excel
    App(visible=False)
    wb = Book()
    ws = wb.sheets[0]

    # Format table headers
    ws.range(f'A1').value = list(dataframe.columns)
    ws.range(f'A1:AAA1').font.bold = True
    ws.range(f'A1:AAA1').font.size = 14

    # Write data
    pos = 2
    for year in dataframe['YEAR'].unique():
        slice = dataframe[dataframe['YEAR']==year]
        slice = slice.groupby(['YEAR','MONTH']).sum()
        ws.range(f'A{pos}').options(header=False).value = slice
        pos += len(slice.index)+1

    # Fit columns and rows
    for ws in wb.sheets:
            ws.autofit(axis="columns")
            ws.autofit(axis="rows")

    # Save
    wb.save(f'{destination_folder}/{timestamp()}__{doc_name}__{pk}.xlsx')
    wb.close()