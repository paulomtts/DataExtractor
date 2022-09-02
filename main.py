from aux_funcs import format_date, format_number
from app_classes import Document, Entity, Extract
from configparser import ConfigParser
from xlwings import App, Book
from datetime import datetime
from pandas import read_excel
from time import sleep
from tika import initVM
from os import path

########################################################################################################################################################################################################################
ROOT_PATH = path.dirname(__file__).replace('/app', '').replace('\\', '/')

CONFIG_INI = ConfigParser()
CONFIG_INI.read_file(open(f'{ROOT_PATH}/app/config.ini', "r", encoding="utf8"))

CONFIG_XL = {}
for row in read_excel(f'{ROOT_PATH}/app/extractor.xlsm').iterrows():
    file_name = str(row[1][0]).strip().rstrip('.pdf')
    date_key = str(row[1][1]).strip()
    id_key = str(row[1][2])
    CONFIG_XL[file_name] = {
        'id_numbers'    : [el.strip() for el in str(row[1][3]).split(',')],
        'header_kwrds'  : [el.strip() for el in str(row[1][4]).split(',')],
        'body_kwrds'    : [el.strip() for el in str(row[1][5]).split(',')],
        'footer_kwrds'  : [el.strip() for el in str(row[1][6]).split(',') if el != 'nan'],
    }

# Initialize tika
initVM()

########################################################################################################################################################################################################################
def setup_objects():
    """Setup Document and Group objects objects."""

    doc_lst  = [Document(f'{ROOT_PATH}/documents', f'{file_name}') for file_name in CONFIG_XL.keys()]
    for doc in doc_lst:
        doc.set_entities([id_number for id_number in CONFIG_XL[doc.name]['id_numbers']])

now = lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S')
"Return the date and time in standard format."

def main():
    """Extract data from all files and parse them into separate excel files."""
    doc: Document; ent: Entity; ext: Extract

    # Set variables
    drop_cols = ['MONTH', 'YEAR', date_key, id_key]

    text_ptt = CONFIG_INI['EXPRESSIONS']['text']
    header_ptt = CONFIG_INI['EXPRESSIONS']['header'].format("%")
    body_ptt = CONFIG_INI['EXPRESSIONS']['body'].format("%")
    footer_ptt = CONFIG_INI['EXPRESSIONS']['footer'].format("%")
    
    # Setup document and group objects
    print('Preparing Document and Block objects...')
    setup_objects()

    # Extract data from documents
    for doc in Document.lst:
        global TIMESTAMP
        
        # Set additional variables
        TIMESTAMP = str(now()).replace(' ', '_').replace(':', '-')
        header_kwrds = CONFIG_XL[doc.name]['header_kwrds']
        body_kwrds = CONFIG_XL[doc.name]['body_kwrds']
        footer_kwrds = CONFIG_XL[doc.name]['footer_kwrds']
        
        print('Done!')
        print('Extracting data...')
        doc.set_extracts(text_ptt)

        # Log line list
        with open(f'{ROOT_PATH}/app/extracts/naturals/{TIMESTAMP}_{file_name}_nat.txt', 'w', encoding='UTF-8') as fl:
            for ln in doc.line_lst:
                fl.write(ln + '\n')

        # Log extracted data
        with open(f'{ROOT_PATH}/app/extracts/{TIMESTAMP}_{doc.name}_ext.txt', 'w', encoding='UTF-8') as fl:
            for obj in Extract.lst:
                obj: Extract
                fl.write(obj.header + '\n')
                fl.write(obj.body+ '\n')
                fl.write(obj.footer+ '\n')
                fl.write('------\n')

        # Extract properties from data
        print('Acquiring properties for each segment...')
        for ext in Extract.lst:
            ext.set_properties(ext.header, header_ptt, header_kwrds)
            ext.set_properties(ext.body, body_ptt, body_kwrds)
            ext.set_properties(ext.footer, footer_ptt, footer_kwrds)

        # Assign blocks to groups and build dataframes from properties
        print('Assigning Blocks to Groups...')
        for ent in doc.entities:
            ent.acquire_extracts('header', id_key)

            header = ent.build_dataframe(header_kwrds, 'header')
            body   = ent.build_dataframe(body_kwrds, 'body')
            footer = ent.build_dataframe(footer_kwrds, 'footer')

            # Treat data and join dataframes
            df = header.join([body, footer])
            df = df.fillna('0')

            df[date_key] = df[date_key].apply(format_date)
            df['MONTH'] = df[date_key].apply(lambda val: val.month)
            df['YEAR'] = df[date_key].apply(lambda val: val.year)
            df = df.reindex(columns=['YEAR', 'MONTH'] + [col for col in df.columns if col not in drop_cols])

            for col in [col for col in df.columns if col not in drop_cols]:
                df[col] = df[col].apply(format_number)

            df = df.sort_values(['YEAR', 'MONTH'])
            df = df.drop_duplicates()
            df = df.reset_index(drop=True)

        # Write to excel
        print(f'{doc.name} - Writing to excel file...')
        App(visible=False)
        wb = Book()
        ws = wb.sheets[0]


        pos = 2
        ws.range(f'A1').value = list(df.columns)
        ws.range(f'A1:AAA1').font.bold = True
        ws.range(f'A1:AAA1').font.size = 14
        for year in df['YEAR'].unique():
            slice = df[df['YEAR']==year]
            ws.range(f'A{pos}').options(index=False, header=False).value = slice
            pos += len(slice.index)+1

        for ws in wb.sheets:
                ws.autofit(axis="columns")

        ws.range(f'$A1:$Z999').api.HorizontalAlignment = -4108

        wb.save(f'{ROOT_PATH}/spreadsheets/{TIMESTAMP}__{doc.name}.xlsx')
        wb.close()
        print('\tDone!')
        
        sleep(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f'{TIMESTAMP} - {error}')
        with open(f'{ROOT_PATH}/app/log.txt', 'a') as file:
            file.write(str(now()) + f' - {error}\n')
    finally:
        print('Stopping graciously...')
