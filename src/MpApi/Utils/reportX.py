"""
ReportX writes reports describing the files in the current directory.

The report is written in Excel (xlsx). It's basically a list of files with some information
(size, mtime etc.).

"""
import datetime
from MpApi.Utils.logic import extractIdentNr
from MpApi.Utils.BaseApp import BaseApp, ConfigError
from openpyxl import load_workbook, Workbook, worksheet
from openpyxl.styles import Alignment, Font
from pathlib import Path
#from Typing import Optional
fast = False

class ReportX(BaseApp):
    def __init__(self) -> None:
        pass

    def write_report(self, fn: str) -> None:
        """
        We assume that the report is empty at the beginning, loop thru all files and enter 
        each one into Excel table.
        """
        xlsx_fn = Path(fn)
        ws = self._init_report(path=xlsx_fn)
        ws2 = self.wb.create_sheet("Conf")
        rno = 2
        print ("beginning recursive scandir")
        for p in Path().rglob("*"):
            if p.is_dir():
                print (f" {p} dir")
                continue
            elif p.name.lower() == "thumbs.db" or p.name.lower() == "desktop.ini":
                continue
            identNr = extractIdentNr(path=Path(p.name))
            print(f"   {rno}: {p} -> {identNr}")
            ws[f"A{rno}"].value = p.name
            if not fast:
                ws[f"B{rno}"].value = p.stat().st_size
                ws[f"C{rno}"].value = p.stat().st_mtime
            ws[f"D{rno}"].value = identNr
            ws[f"E{rno}"].value = str(p.parent)
            ws[f"F{rno}"].value = str(p.absolute())
            if (rno/10000).is_integer():
                # if we save periodically, we dont know when the run has completed
                self._save_excel(path=xlsx_fn)
            rno += 1
        ws2["A1"].value = "done"
        self._save_excel(path=xlsx_fn)
        
    #
    # private
    #
    
    def _init_report(self, *, path:Path) -> worksheet:
        """
        Creates a new report and saves it in self.wb. Also returns the new first
        worksheet.
        """
        if path.exists():
            raise ConfigError(f"ERROR: Excel report '{path}' exists already. Abort!")
        self.wb = self._init_excel(path=path)
        ws = self.wb.active
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        ws.title = now
        print (f"new sheet {now}")
        ws['A1'] = "Dateiname"
        ws['B1'] = "Größe (KB)"
        ws['C1'] = "mtime"
        ws['D1'] = "IdentNr?"
        ws['E1'] = "rel. Verzeichnis"
        ws['F1'] = "Absoluter Pfad"

        for each in "A1", "B1", "C1", "D1", "E1", "F1":
            ws[each].font = Font(bold=True)

        ws.column_dimensions["A"].width = 17
        ws.column_dimensions["B"].width = 12
        ws.column_dimensions["C"].width = 15
        ws.column_dimensions["D"].width = 10
        ws.column_dimensions["E"].width = 15
        ws.column_dimensions["F"].width = 50

        return ws