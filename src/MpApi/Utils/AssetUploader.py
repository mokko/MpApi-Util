"""
Should emulate the hotfolder eventually. That is we 

(a) read in a configuration from an Excel file
(b) process an input directory (non recursively),
(c) create new multimedia (=asset) records from a template
(d) upload/attach files to an multimedia records
(e) create a reference usually from object to multimedia record

In order to make the process transparent it is carried out in several steps


"""
from MpApi.Utils.BaseApp import BaseApp
from MpApi.Utils.logic import extractIdentNr

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from pathlib import Path
import re
from typing import Any, Optional

excel_fn = Path("upload.xlsx")


class AssetUploader(BaseApp):
    def __init__(self) -> None:
        creds = self._read_credentials()
        self.baseURL = creds["baseURL"]
        self.pw = creds["pw"]
        self.user = creds["user"]
        self.wb = self._init_excel(path=excel_fn)

        print(self.user, self.baseURL, self.pw)

    def go(self) -> None:
        """
        Do the actual upload based on the preparations in the Excel file
        """

    def init(self) -> None:
        """
        Creates a pre-structured, but essentially empty Excel file for configuration
        and logging purposes.

        Don't overwrite existing Excel file.
        """

        if excel_fn.exists():
            print(f"WARN: Abort init since {excel_fn} exists already!")
            return

        self.wb = Workbook()
        ws = self.wb.active
        ws.title = "Assets"

        self.table_desc = {
            "filename": {
                "label": "Asset Dateiname",
                "desc": "aus Verzeichnis",
                "col": "A",
                "width": 20,
            },
            "identNr": {
                "label": "IdentNr",
                "desc": "aus Dateinamen",
                "col": "B",
                "width": 15,
            },
            "assetUploaded": {
                "label": "Assets mit diesem Dateinamen",
                "desc": "mulId(s) aus RIA",
                "col": "C",
                "width": 15,
            },
            "objIds": {
                "label": "objId(s) aus RIA",
                "desc": "für diese IdentNr",
                "col": "D",
                "width": 15,
            },
            "partsObjIds": {
                "label": "Teile objId",
                "desc": "für diese IdentNr",
                "col": "E",
                "width": 20,
            },
            "unused": {
                "label": "Kandidat",
                "desc": "neue Objekte erzeugen?",
                "col": "F",
                "width": 7,
            },
            "notes": {
                "label": "Bemerkung",
                "desc": "für Notizen",
                "col": "G",
                "width": 20,
            },
            "fullpath": {
                "label": "Pfad",
                "desc": "aus Verzeichnis",
                "col": "H",
                "width": 115,
            },
        }

        for itemId in self.table_desc:
            col = self.table_desc[itemId]["col"]  # letter
            ws[f"{col}1"] = self.table_desc[itemId]["label"]
            ws[f"{col}1"].font = Font(bold=True)
            # print (f"{col} {self.table_desc[itemId]['label']}")
            if "desc" in self.table_desc[itemId]:
                desc = self.table_desc[itemId]["desc"]
                ws[f"{col}2"] = desc
                ws[f"{col}2"].font = Font(size=9, italic=True)
                # print (f"\t{desc}")
            if "width" in self.table_desc[itemId]:
                width = self.table_desc[itemId]["width"]
                # print (f"\t{width}")
                ws.column_dimensions[col].width = width

        ws2 = self.wb.create_sheet("Conf")
        ws2["A1"] = "templateID"
        ws2["C1"] = "Asset"
        ws2["A2"] = "reference"
        ws2["B2"] = "Object"
        ws2["A3"] = "OrgUnit(optional)"
        ws2["B3"] = "NGAlteNationalgalerie"

        self._save_excel(path=excel_fn)

    def scandir(self, *, Dir=None) -> None:
        """
        Scans local directory and enters values for each file in the Excel
        """

        # check if excel exists, has the expected shape and is writable
        if not excel_fn.exists():
            raise configError(f"ERROR: {excel_fn} does NOT exist!")

        # die if not writable so that user can close it before waste of time
        self._save_excel(path=excel_fn)
        try:
            ws = self.wb["Assets"]
        except:
            raise configError("Excel file has no sheet 'Assets'")

        if ws.max_row > 2:
            raise configError("Error: Scandir info already filled in!")

        self.client = self._init_client()
        conf_ws = self.wb["Conf"]
        orgUnit = conf_ws["B3"].value

        def _per_row(*, c: int, path: Path) -> None:
            # labels are more readable
            filename_cell = ws[f"A{c}"]
            ident_cell = ws[f"B{c}"]
            asset_fn_exists_cell = ws[f"C{c}"]
            objId_cell = ws[f"D{c}"]
            parts_objId_cell = ws[f"E{c}"]
            candidate_cell = ws[f"F{c}"]
            # G has comments which are for Excel user
            fullpath_cell = ws[f"H{c}"]

            identNr = extractIdentNr(path=path)  # returns None on failure
            print(f"{identNr} : {path.name}")
            filename_cell.value = path.name
            ident_cell.value = identNr
            fullpath_cell.value = str(path)

            idL = self.client.fn_to_mulId(fn=filename_cell.value, orgUnit=orgUnit)
            if len(idL) == 0:
                asset_fn_exists_cell.value = "None"
            else:
                asset_fn_exists_cell.value = "; ".join(idL)

            # in rare cases identNr_cell might be None, then we cant look up any objIds
            if ident_cell.value is None:
                return None

            # only write if field empty
            if objId_cell.value == None:
                objId_cell.value = self.client.get_objIds(
                    identNr=ident_cell.value, strict=True
                )

            if parts_objId_cell.value is None:
                parts_objId_cell.value = self.client.get_objIds2(
                    identNr=ident_cell.value, strict=False
                )
                parts_objId_cell.alignment = Alignment(wrap_text=True)

            if candidate_cell == None:
                if (
                    ident_cell is not None
                    and asset_fn_exists_cell.value == "None"
                    and objId_cell.value != "None"
                ):
                    candidate_cell.value = "x"

        # looping thru files (usually pwd)
        if Dir is None:
            src_dir = Path(".")
        else:
            src_dir = Path(Dir)
        print(f"Scanning pwd {src_dir}")

        c = 3  # line counter, begin at 3rd line
        for p in src_dir.glob("*"):
            if str(p).startswith("."):
                continue
            elif p.suffix == ".py" or p.suffix == ".ini":
                continue
            elif p == excel_fn:
                continue
            elif p.is_dir():
                continue
            elif str(p) == "thumbs.db" or str(p) == "desktop.ini":
                continue
            print(f" {p}")

            _per_row(c=c, path=p)
            c += 1

        self._save_excel(path=excel_fn)
