from MpApi.Utils.attach2 import Attacher2
from pathlib import Path

excel_fn = Path("../sdata/attach.xlsx")


def test_init():
    a = Attacher2(excel_fn=excel_fn)


def test_finder():
    a = Attacher2(excel_fn=excel_fn)
    a.xls.raise_if_no_file()
    a.ws = a.xls.get_or_create_sheet(title="Missing Attachments")
    a.xls.raise_if_no_content(sheet=a.ws)
    p = Path("path/to/MayaBlau_B_91_121213.pdf")
    hits = a._find_name_in_excel(p)

    print(hits)
    assert hits


def test_adder():
    a = Attacher2(excel_fn=excel_fn)
    a.xls.raise_if_no_file()
    a.ws = a.xls.get_or_create_sheet(title="Missing Attachments")
    a.xls.raise_if_no_content(sheet=a.ws)
    p = Path("path/to/MayaBlau_B_91_121213.pdf")
    a._add_file_excel(p)
    a.xls.save()
