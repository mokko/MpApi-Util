"""
ReportX writes reports describing the files in the current directory.

The report is written in Excel (xlsx). It's basically a list of files with some information
(size, mtime etc.).

"""
from MpApi.Utils.logic import extractIdentNr
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from pathlib import Path


class ReportX:
    def __init__(self) -> None:
        pass

    def make_report(self, fn: str) -> None:
        for p in Path().rglob("*.py"):
            print(f"{p}")
