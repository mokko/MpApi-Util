from pathlib import Path
from MpApi.Utils.Xls import Xls
from openpyxl import Workbook  # load_workbook
from openpyxl.styles import Alignment, Font

c = 1
limit = -1
red = Font(color="FF0000")

desc = {
    "filename": {
        "label": "Name",
        "desc": "aus Verzeichnis",
        "col": "A",  # 0
        "width": 20,
    },
    "duplicate": {
        "label": "Duplicate?",
        "desc": "gibt es diesen Filenamen mehr als einmal?",
        "col": "B",
        "width": 20,
    },
    "fullpath": {
        "label": "Fullpath",
        "desc": "",
        "col": "C",
        "width": 20,
    },
}
xls = Xls("renb.xlsx", desc)
ws = xls.get_or_create_sheet(title="Dedupe")
xls.raise_if_content(sheet=ws)
xls.write_header(sheet=ws)
xls.save()  # make sure it's writable

knwn_name = list()

for p in Path().glob("**/*.tif"):
    print(f"{p} -> {p.name}")
    cells = xls._rno2dict(c, sheet=ws)
    if cells["filename"].value is None:
        cells["filename"].value = p.name
    if p.name not in knwn_name:
        knwn_name.append(p.name)
    else:
        cells["duplicate"].value = "x"
        cells["filename"].font = red

    if cells["fullpath"].value is None:
        cells["fullpath"].value = str(p)

    if c == limit:
        break
    c += 1
xls.save()  # make sure it's writable
