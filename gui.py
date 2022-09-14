import tika
import tkinter as tk
import unidecode

from main import pre_process_documents, extract_from_text, update_json, timestamp, PATH
from tkinter import filedialog, ttk

words_to_filter = ['Posição', 'IR', 'Agência Crédito', 'Conta', 'Período', 'Provis', 'Posição', 'Ag.Crédito', 'Nome', 'Empresa']
tika.initVM()

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.counter = 0
        self.docs = None

        # Setup
        self.geometry('820x480')
        self.resizable(False, False)
        self.title('PDFExtractor')
        self.iconbitmap(f'{PATH}/app/favicon.ico')

        # Configure the grid
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=20)
        self.columnconfigure(2, weight=1)

        # Setup variables
        source = tk.StringVar()
        destination = tk.StringVar()


        ##################################################################################################################################################
        # Labels
        label_source = ttk.Label(self, text="Source")
        label_destination = ttk.Label(self, text="Destination")
        label_listboxes = ttk.Label(self, text='Keywords')
        
        # Entries
        self.entry_source = ttk.Entry(self,
            textvariable=source, 
            width=80, 
            justify='center', 
            font=('Helvetica', 11))
       
        self.entry_destination = ttk.Entry(self, 
            textvariable=destination, 
            width=80, 
            justify='center',
            font=('Helvetica', 11))
        
        # Entry
        self.textbox_logger = tk.Text(self, height=7, font=('Helvetica', 9), wrap=tk.WORD)
        
        scroll_bar = tk.Scrollbar(self, orient='vertical', command=self.textbox_logger.yview)
        
        self.textbox_logger['yscrollcommand'] = scroll_bar.set
        self.textbox_logger.config(state=tk.DISABLED)

        # Buttons
        button_source = ttk.Button(self,
            text="Select",
            command = lambda: self.path_bttn(self.entry_source))

        button_destination = ttk.Button(self, 
            text="Select",
            command = lambda: self.path_bttn(self.entry_destination))

        button_load = ttk.Button(self, 
            text="Load",
            command= lambda: self.load_button())
        
        button_extract_0 = ttk.Button(self, 
            text="Extract",
            command= lambda: self.extract_button(self.list_items_left))

        button_extract_1 = ttk.Button(self, 
            text="Extract",
            command= lambda: self.extract_button(self.list_items_right))

        button_load_profile = ttk.Button(self, 
            text="Load Profile",
            command= lambda: self.load_profile())

        button_save_profile = ttk.Button(self, 
            text="Save Profile",
            command= lambda: self.save_profile())

        button_update = ttk.Button(self, 
            text="Update",
            command= lambda: self.update_button())

        # Listboxes
        self.list_items_left = tk.Variable(value=[])
        self.list_items_right = tk.Variable(value=[])
        
        self.listbox_left = tk.Listbox(
            listvariable=self.list_items_left, width=48)

        self.listbox_right = tk.Listbox(
            listvariable=self.list_items_right, width=48)

        def list_items_left_click(_: tk.Event):
            try:
                val = self.listbox_left.selection_get()
                idx = self.listbox_left.curselection()[0]

                curr_vals = self.list_items_right.get()

                if val not in curr_vals:
                    self.listbox_right.insert(0, val)
                self.listbox_left.delete(idx)
            except tk._tkinter.TclError:
                pass
        
        def list_items_right_click(_: tk.Event):
            try:
                val = self.listbox_right.selection_get()
                idx = self.listbox_right.curselection()[0]

                curr_vals = self.list_items_left.get()

                if val not in curr_vals:
                    self.listbox_left.insert(0, val)
                self.listbox_right.delete(idx)
            except tk._tkinter.TclError:
                pass

        self.listbox_left.bind('<Double-1>', list_items_left_click)
        self.listbox_right.bind('<Double-1>', list_items_right_click)


        ##################################################################################################################################################
        # Positioning
        label_source.grid(column=0, row=0, sticky='E', **{'padx': 10, 'pady': 10})
        label_destination.grid(column=0, row=1, sticky='E', **{'padx': 10, 'pady': 10})
        label_listboxes.grid(column=1, row=4, sticky='N', **{'padx': 0, 'pady': 10})
        
        self.entry_source.grid(column=1, row=0, sticky='W')
        self.entry_destination.grid(column=1, row=1, sticky='W')

        self.textbox_logger.grid(rowspan=2, column=1, row=2, sticky='EWNS', pady=10)
        scroll_bar.grid(rowspan=2, column=1, row=2, sticky='e', ipady=29)
        
        button_source.grid(column=2, row=0, **{'padx': 10, 'pady': 10})
        button_destination.grid(column=2, row=1, **{'padx': 10, 'pady': 10})

        button_load.grid(rowspan=2, column=2, row=2, sticky='ns', **{'padx': 0, 'pady': 10})

        button_load_profile.grid(column=2, row=5, sticky='N', **{'padx': 0, 'pady': 0})
        button_save_profile.grid(column=2, row=5, sticky='N', **{'padx': 0, 'pady': 40})
        button_update.grid(column=2, row=5, sticky='S')

        button_extract_0.grid(column=1, row=6, sticky='W', **{'padx': 0, 'pady': 10})
        button_extract_1.grid(column=1, row=6, sticky='E', **{'padx': 0, 'pady': 10})

        self.listbox_left.grid(column=1, row=5, sticky='W')
        self.listbox_right.grid(column=1, row=5, sticky='E')
        
        # Style
        self.style = ttk.Style(self)
        self.style.configure('TLabel', font=('Helvetica', 11))
        self.style.configure('TButton', font=('Helvetica', 11))
        self.style.configure('TText', font=('Helvetica', 11))



    def log_to_textbox(self, text: str):
        """Enable the textbox, insert text into it, and then disable it."""
        self.textbox_logger.config(state=tk.NORMAL)
        self.textbox_logger.insert(tk.END, text + '\n')
        self.textbox_logger.yview_pickplace("end")
        self.textbox_logger.config(state=tk.DISABLED)

    def path_bttn(self, entry_object: ttk.Entry):
        """Open a dialog box and save the chose path into one of the path textboxes."""

        folder_path = filedialog.askdirectory(initialdir=f'{PATH}/')
        if folder_path:
            entry_object.delete(0, tk.END)
            entry_object.insert(0, folder_path)

    def save_profile(self):
        """Save the keywords in the right listbox as a profile."""

        items = [item+'\n' for item in self.list_items_right.get()]
        with filedialog.asksaveasfile(mode='w', defaultextension='.txt', initialdir=f'{PATH}/profiles') as file:
            file.writelines(items)

    def load_profile(self):
        """Load a profile of keywords into the right listbox."""

        lines = None
        file_path = filedialog.askopenfilename(initialdir=f'{PATH}/profiles')
        with open(file_path, 'r') as file:
            lines = file.read().split('\n')
        if lines:
            self.list_items_right.set(lines)

    def load_button(self):
        """Pre-process files by extracting keywords and sending them to the left listbox."""

        normalize = lambda word: unidecode.unidecode(word).replace(' ', '').upper()

        source_path = self.entry_source.get()
        self.listbox_left.delete(0, tk.END)
        self.listbox_right.delete(0, tk.END)
        
        if source_path != '':
            self.log_to_textbox(f'#{self.counter} Acquiring keywords...')
            self.update()
            self.counter += 1

            try:
                self.docs = pre_process_documents(source_path)
                insert_lst = []
                
                for doc in self.docs:
                    for words in doc.keywords.values():
                        for wrd in words:
                            if normalize(wrd) not in [normalize(item) for item in insert_lst] and \
                               normalize(wrd) not in [normalize(item) for item in words_to_filter]:
                                insert_lst.append(wrd)
                
                insert_lst.sort()
                self.listbox_left.insert(0, *insert_lst)

                if not self.docs:
                    self.log_to_textbox('No files were found in the selected folder.')

            except Exception as error:
                with open(f'{PATH}/app/logs/log.txt', 'a', encoding='utf-8') as file:
                    file.write(f'{timestamp()} - {str(error)}\n')

                self.log_to_textbox(f'Could not pre-process files. Check the log file for more information.')
                with open(f'{PATH}/app/logs/{timestamp()}_opr.txt', 'w', encoding='utf-8') as file:
                    file.write(self.textbox_logger.get("1.0", tk.END))
        
                tk.messagebox.showwarning('Warning', f'Error: {error}\nFor more information, please see the log file.')

            finally:
                self.log_to_textbox('Done!\n_____')
        else:
            tk.messagebox.showinfo('Warning', 'Please select a source location!')


    def extract_button(self, list_items: tk.Variable):
        """Perform the keyword extraction using the words from one of the listboxes, and then build
        an excel sheet for each file."""

        items = [item for item in list_items.get()]
        destination_path = self.entry_destination.get()

        if self.docs != None and items != [] and destination_path != '':
            self.log_to_textbox(f'#{self.counter} Extracting data...')
            self.update()
            self.counter += 1

            try:           
                extract_from_text(self.docs, destination_path, words_to_keep=items, words_to_filter=words_to_filter)
            except Exception as error:
                with open(f'{PATH}/app/logs/log.txt', 'a', encoding='utf-8') as file:
                    file.write(f'{timestamp()} - {str(error)}\n')

                self.log_to_textbox(f'Could not extract keywords from text. Check the log file for more information.')
                with open(f'{PATH}/app/logs/{timestamp()}_opr.txt', 'w', encoding='utf-8') as file:
                    file.write(self.textbox_logger.get("1.0", tk.END))

                tk.messagebox.showwarning('Warning', f'Error: {error}\nFor more information, please see the log file.')

            finally:
                self.log_to_textbox('Done!\n_____')
        else:
            tk.messagebox.showinfo('Warning', 'Please select a destination path and load the files!')

    def update_button(self):
        """Attempt to update the JSON file."""

        self.log_to_textbox('Requesting at https://api.jsonbin.io/v3/ ...')
        self.update()
        response = update_json()

        if response.status_code == 200:
            self.listbox_left.delete(0, tk.END)
            self.listbox_right.delete(0, tk.END)
            self.log_to_textbox('Update complete! Please reload.\n_____')
        else:
            self.log_to_textbox(f'{response}. Visit https://jsonbin.io/api-reference/bins/read for more information.')


if __name__ == "__main__":
    app = App()
    app.mainloop()