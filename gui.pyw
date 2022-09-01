from tkinter import filedialog, filedialog
from tkinter import *

import os

ROOT_PATH = os.path.dirname(__file__)
root = Tk()

rsc_path = f'{ROOT_PATH}/app/resources'
entries = {'entry_0': None, 'entry_1': None, 'entry_2': None}

def path_btn_clicked(object, entry_name: str):
    folder_path = filedialog.askdirectory()
    if folder_path:
        print('File loaded.')
        object.insert(0, folder_path)

# Setup window, canvas and background#########################
root.geometry("1000x600")
root.configure(bg = "#ffffff")

canvas = Canvas(
    root,
    bg = "#ffffff",
    height = 600,
    width = 1000,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge")
canvas.place(x = 0, y = 0)

background_img = PhotoImage(file = f"{rsc_path}/background.png")
background = canvas.create_image(
    489.0, 301.5,
    image=background_img)

# Entry fields ###############################################
for i in range(2):
    entry_y = 111 - (i*65)
    entry_bg = {0: "#f5fdf3", 1: "#fdf3f3"}

    entry = Entry(
        name = f'entry_{i}',
        justify='center',
        borderwidth=2,
        bg = entry_bg[i],
        highlightthickness = 1)
    entry.place(
        x = 46, y = entry_y,
        width = 694,
        height = 42)

    entries[f'entry_{i}'] = entry

# Multiline text #############################################
for i in range(3):
    entry_y = 463 - (i*132)

    entry = Text(
        borderwidth=1,
        bg = "#ebebeb",
        highlightthickness = 1)

    # Positioning
    entry.place(
        x = 46, y = entry_y,
        width = 694,
        height = 85)


# Buttons ###################################################
img1 = PhotoImage(file = f"{rsc_path}/img1.png")
b1 = Button(
    root,
    image = img1,
    borderwidth = 0,
    highlightthickness = 0,
    command = lambda: path_btn_clicked(entries['entry_0'], 'entry_0'),
    relief = "flat")
b1.place(
    x = 758, y = 113,
    width = 203,
    height = 32)

img0 = PhotoImage(file = f"{rsc_path}/img0.png")
b0 = Button(
    image = img0,
    borderwidth = 0,
    highlightthickness = 0,
    command = lambda: path_btn_clicked(entries['entry_1'], 'entry_1'),
    relief = "flat")
b0.place(
    x = 759, y = 51,
    width = 203,
    height = 32)

img2 = PhotoImage(file = f"{rsc_path}/img2.png")
b2 = Button(
    image = img2,
    borderwidth = 0,
    highlightthickness = 0,
    # command = lambda: path_btn_clicked(entries['entry_1'], 'entry_0'),
    relief = "flat")
b2.place(
    x = 811, y = 484,
    width = 99,
    height = 43)

root.resizable(False, False)
root.mainloop()
