# from PyPDF2 import PdfFileReader as rdr
# from PyPDF2 import PdfFileWriter as wtr
from tika import parser as tkpr
from pandas import DataFrame
from re import finditer
# import re

########################################################################################################################################################################################################################
class Block():
    lst = []

    def __init__(self, header: str, body: str, footer: str) -> None:
        if id in Block.lst: return
        
        self.header      :str        = header
        self.body        :str        = body
        self.footer      :str        = footer
        self.areas       :dict       = {'header': {},'body': {},'footer': {} }

        Block.lst.append(self)

    def extract_properties(self, txt: str, pattern: str, keywords: list):
        sw = {self.header: 'header', self.body: 'body', self.footer: 'footer'}
        for word in keywords:
            for result in finditer(pattern % word, txt):
                self.areas[sw[txt]][word] = result.group('value').strip()
    
class Group():
    lst = []
    def __init__(self, id: str) -> None:
        self.id       :str           = id
        self.blocks   :list[Block]   = []

        Group.lst.append(self)

    def acquire_blocks(self, area: str, name: str):
        self.blocks = [blk for blk in Block.lst if blk.areas[area][name] == self.id]


    def build_dataframe(self, keywords: list, area: str='body'):
        if area not in {'header', 'body', 'footer'}: raise ValueError("<area> value is invalid.")
        lst = [blk.areas[area] for blk in self.blocks if blk.areas['body'] != {}]
        return DataFrame.from_records(lst, columns=keywords)

class Document():
    lst = []
    def __init__(self, file_path: str, file_name: str) -> None:

        # Detect file rotation
        # self._rotate_pages(file_path, file_name)

        # Extract and process natural text
        natural_text        :str    = tkpr.from_file(f'{file_path}/{file_name}.pdf')['content']
        self.line_lst       :list   = []

        for ln in natural_text.split('\n'):
            if ln == '': continue
            self.line_lst.append(ln.strip())
        
        # Set variables
        self.name      :str    = file_name
        self.text      :str    = '\n'.join(self.line_lst)
        self.groups    :list   = []
        
        Document.lst.append(self)

    # def _rotate_pages(self, file_path: str, file_name: str):
    #     input = open(f'{file_path}/{file_name}.pdf', 'rb')
        
    #     writer = wtr()
    #     reader = rdr(input, strict=False)

    #     for pagenum in range(reader.numPages):
    #         page = reader.getPage(pagenum)
            
    #         # orientation = reader.getPage(pagenum).get('/Rotate')
    #         page.rotateClockwise(180)
    #         writer.addPage(page)

    #     output = open(f'{file_path}/_{file_name}.pdf', 'wb')
    #     writer.write(output)
        
    #     input.close()
    #     output.close()

    # METHODS #####################################################
    def extract_data(self, pattern: str):
        for result in finditer(pattern, self.text):
            header = result.group('header')
            body = result.group('body')
            footer = result.group('footer')

            Block(header, body, footer)

    def add_groups(self, group_lst: list):
        for group in group_lst:
            self.groups.append(group)
