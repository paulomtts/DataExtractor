from os import path as os_path, listdir as os_listdir
from app_classes import Document, Entity, Extract
from aux_funcs import format_date, format_number
from xlwings import App, Book, Sheet
from datetime import datetime
from pandas import DataFrame

import json

PATH = os_path.dirname(__file__)
TIMESTAMP = lambda: str(datetime.now().strftime('%y-%m-%dT%H-%M'))
with open(f'{PATH}/app/config.json', encoding='utf-8') as json_file:
    CONFIG = json.load(json_file)

# MAIN METHODS #############################################################################################
def analyze(folder_path: str):
    """Pre-process the text by setting up extracts and acquiring lists of words."""
    files = [(folder_path, file_name) for file_name in os_listdir(folder_path) if '.pdf' in file_name]
    avoid_words = from_gui('avoid_words')

    doc_lst  = [Document(path, name) for (path, name) in files]
    for doc in doc_lst:
        for dct in CONFIG.values():
            doc.set_extracts(dct)
            doc.set_words(dct['WORDS'], avoid_words)
    return doc_lst

def extract(doc_lst: list):
    """Extract data from the the document and send it to excel."""
    doc: Document; ent: Entity; ext: Extract

    search_data = from_gui('search_data')
    
    for doc in doc_lst:

        # Write natural .txt
        with open(f'{PATH}/app/extracts/naturals/{TIMESTAMP()}__{doc.name}__nat.txt', 'w', encoding='utf-8') as file:
            file.write(doc.natural_text)

        # Write extract .txt
        for ext in doc.extracts:
            ext.set_properties(search_data)

            with open(f'{PATH}/app/extracts/{TIMESTAMP()}__{doc.name}__ext.txt', 'a', encoding='utf-8') as file:
                for prop in ext.properties.keys():
                    file.write(getattr(ext, prop) + '\n')
                file.write('----\n')

        doc.set_entities()
        for ent in doc.entities:
            ent.gather_extracts(doc.extracts)
            ent.build_dataframe(search_data)
            dataframe = treat_dataframe(ent.dataframe, 'Data de Crédito')
            to_excel(dataframe, doc.name, ent.pk.replace('.', ''))

# OUTPUT METHODS ###########################################################################################
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
        wb.save(f'{PATH}/spreadsheets/{TIMESTAMP()}__{doc_name}__{ent_id}.xlsx')
    except:
        pass
    finally:
        wb.close()



#####################################################
# SINCE THIS WILL COME FROM GUI, EVERY ITERATION WILL GET IT'S PROPER SET
def from_gui(label: str):
    avoid_words = ['DESCONTOS', 'TOTAL', 'LIQUIDO', '/', 'NUM.', 'VALOR']
    search_data = {'header': ['Data de Crédito'], 
                'body': ['Ordenado', 'Reemb.Férias no Mês', 'Adiant.Vale Transporte', 'ORDENADO']}
    if label == 'avoid_words':
        return avoid_words
    elif label == 'search_data':
        return search_data
#####################################################

docs = analyze(f'{PATH}/documents/')       # Used by GUI access word lists in each document
extract(docs)                              # This happens when you click EXTRACT