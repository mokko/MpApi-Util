"""
Should emulate the hotfolder eventually. That is we 

(a) read in a configuration from an Excel file
(b) process an input directory (non recursively),
(c) create new multimedia (=asset) records from a template
(d) upload/attach files to an multimedia records
(e) create a reference usually from object to multimedia record

In order to make the process transparent it is carried out in several steps


"""
import copy
from lxml import etree
from MpApi.Utils.BaseApp import BaseApp, ConfigError
from MpApi.Utils.logic import extractIdentNr
from MpApi.Utils.Ria import RIA
from mpapi.module import Module
from mpapi.record import Record

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from pathlib import Path
import pyexiv2
import re
import shutil
from typing import Any, Optional

excel_fn = Path("upload.xlsx")
red = Font(color="FF0000")
parser = etree.XMLParser(remove_blank_text=True)
teal = Font(color="008080")


class AssetUploader(BaseApp):
    def __init__(self, *, limit: int = -1) -> None:
        self.limit = int(limit)  # allows to break the go loop after number of items
        creds = self._read_credentials()
        self.client = RIA(baseURL=creds["baseURL"], user=creds["user"], pw=creds["pw"])
        self.wb = self._init_excel(path=excel_fn)

    def go(self) -> None:
        """
        Do the actual upload based on the preparations in the Excel file

        (a) create new multimedia (=asset) records from a template
        (b) upload/attach files to an multimedia records
        (c) create a reference usually from object to multimedia record
        (d) update Excel to reflect changes
        (e) move uploaded file in uploaded subdir.

        """
        print("Enter go")
        # check if excel exists, has the expected shape and is writable
        if not excel_fn.exists():
            raise ConfigError(f"ERROR: {excel_fn} NOT found!")

        # die if not writable so that user can close it before waste of time
        self._save_excel(path=excel_fn)

        try:
            self.ws = self.wb["Assets"]
        except:
            raise ConfigError("ERROR: Excel file has no sheet 'Assets'")

        ws2 = self.wb["Conf"]
        if ws2["B1"] is None:
            raise ConfigError("ERROR: no templateID provided")

        templateM = self._prepare_template()

        u_dir = Path("uploaded")
        if not u_dir.exists():
            print(f"Making new dir '{u_dir}'")
            u_dir.mkdir()

        for row, c in self._loop_table():
            # relative path; assume dir hasn't changed since scandir run
            filename_cell = self.ws[f"A{c}"]
            asset_fn_exists_cell = self.ws[f"C{c}"]
            ref_cell = self.ws[f"F{c}"]
            fn = filename_cell.value
            asset_already_attached_cell = self.ws[f"J{c}"]
            print(f"{c}: {filename_cell.value}")
            if ref_cell.value == "None":
                print(
                    "   object reference unknown, not creating assets nor attachments"
                )
                continue
            else:
                print(f"   object reference known, continue {ref_cell.value}")

            if asset_fn_exists_cell.value == "None":
                new_asset_id = self._make_new_asset(
                    fn=fn, moduleItemId=ref_cell.value, templateM=templateM
                )
                asset_fn_exists_cell.value = new_asset_id
                asset_fn_exists_cell.font = teal
                print(f"   asset {new_asset_id} created")
            else:
                print(f"   asset exists already: {asset_fn_exists_cell.value}")

            if asset_already_attached_cell.value == None:
                ID = int(asset_fn_exists_cell.value)
                print(f"   attaching {fn} {ID}")
                ret = self.client.upload_attachment(file=fn, ID=ID)
                # print(f"   success on upload? {ret}")
                if ret.status_code == 204:
                    asset_already_attached_cell.value = "x"
                    shutil.move(fn, u_dir)
                    print(f"   fn moved to dir '{u_dir}'")
                else:
                    print("   ATTACHING FAILED!")
            else:
                print("   asset already attached")
            self._save_excel(path=excel_fn)  # save after every file/row

    def init(self) -> None:
        """
        Creates a pre-structured, but essentially empty Excel file for configuration
        and logging purposes.

        Don't overwrite existing Excel file.
        """

        if excel_fn.exists():
            print(f"WARN: Abort init since '{excel_fn}' exists already!")
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
            "reference": {
                "label": "Objekte-Link",
                "desc": "automatisierter Vorschlag",
                "col": "F",
                "width": 7,
            },
            "notes": {
                "label": "Bemerkung",
                "desc": "für Notizen",
                "col": "G",
                "width": 20,
            },
            "photographer": {
                "label": "Fotograf*in",
                "desc": "aus Datei",
                "col": "H",
                "width": 20,
            },
            "fullpath": {
                "label": "absoluter Pfad",
                "desc": "aus Verzeichnis",
                "col": "I",
                "width": 115,
            },
            "attached": {
                "label": "Asset hochgeladen?",
                "desc": "wenn Upload erfolgreich",
                "col": "J",
                "width": 15,
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
        #
        # Conf Sheet
        #
        ws2 = self.wb.create_sheet("Conf")
        ws2["A1"] = "templateID"
        ws2["C1"] = "Asset"
        ws2["A2"] = "verlinktes Modul"
        ws2["B2"] = "Objekte"  # todo alternativer Wert Restaurierung
        ws2["A3"] = "OrgUnit (optional)"
        ws2[
            "C3"
        ] = "OrgUnits sind RIA-Bereiche in interner Schreibweise (ohne Leerzeichen)"
        ws2["B3"] = "EMMusikethnologie"

        ws2["C3"].alignment = Alignment(wrap_text=True)
        ws2.column_dimensions["A"].width = 25
        ws2.column_dimensions["B"].width = 25
        ws2.column_dimensions["C"].width = 25

        for each in "A1", "A2", "A3":
            ws2[each].font = Font(bold=True)

        self._save_excel(path=excel_fn)

    def scandir(self, *, Dir=None) -> None:
        """
        Scans local directory and enters values for each file in the Excel
        """

        # check if excel exists, has the expected shape and is writable
        if not excel_fn.exists():
            raise ConfigError(f"ERROR: {excel_fn} NOT found!")

        # die if not writable so that user can close it before waste of time
        self._save_excel(path=excel_fn)
        try:
            ws = self.wb["Assets"]
        except:
            raise ConfigError("ERROR: Excel file has no sheet 'Assets'")

        if ws.max_row > 2:
            raise ConfigError("ERROR: Scandir info already filled in!")
        # For the development we want to be able to run scandir multiple times
        # We do not want to overwrite Excel cells that have already been filled in
        # It is not unlikely that new files are added or existing files get deleted
        # between runs. If that is the case info might be entered in the wrong row.
        # To avoid that we should __not__ allow rewriting in production mode.

        conf_ws = self.wb["Conf"]
        orgUnit = conf_ws["B3"].value  # can be None
        if orgUnit == "" or orgUnit.isspace():
            orgUnit = None
        print(f"Using orgUnit = {orgUnit}")

        def _per_row(*, c: int, path: Path) -> None:
            # labels are more readable
            filename_cell = ws[f"A{c}"]
            ident_cell = ws[f"B{c}"]
            asset_fn_exists_cell = ws[f"C{c}"]
            objId_cell = ws[f"D{c}"]
            parts_objId_cell = ws[f"E{c}"]
            ref_cell = ws[f"F{c}"]
            # G has comments which are exclusively for Excel user
            fotografer_cell = ws[f"H{c}"]
            fullpath_cell = ws[f"I{c}"]

            identNr = extractIdentNr(path=path)  # returns Python's None on failure
            print(f"  {path.name}: {identNr}")
            # only write in empty fields
            if filename_cell.value is None:
                filename_cell.value = path.name
            if ident_cell.value is None:
                ident_cell.value = identNr
            if fullpath_cell.value is None:
                fullpath_cell.value = str(path.resolve())

            if asset_fn_exists_cell.value is None:
                idL = self.client.fn_to_mulId(fn=filename_cell.value, orgUnit=orgUnit)
                if len(idL) == 0:
                    asset_fn_exists_cell.value = "None"
                else:
                    asset_fn_exists_cell.value = "; ".join(idL)

            # in rare cases identNr_cell might be None, then we cant look up any objIds
            if ident_cell.value is None:
                return None

            if objId_cell.value == None:
                objId_cell.value = self.client.get_objIds(
                    identNr=ident_cell.value, strict=True
                )

            if parts_objId_cell.value is None:
                parts_objId_cell.value = self.client.get_objIds2(
                    identNr=ident_cell.value, strict=False
                )
                parts_objId_cell.alignment = Alignment(wrap_text=True)

            if ref_cell.value is None:
                if (
                    asset_fn_exists_cell.value == "None"
                    and objId_cell.value != "None"
                    and ";" not in objId_cell.value
                ):
                    ref_cell.value = objId_cell.value
                    ref_cell.font = teal
                else:
                    ref_cell.value = "None"
                    ref_cell.font = red

            if fotografer_cell.value is None:
                with pyexiv2.Image(str(path)) as img:
                    data = img.read_iptc()
                try:
                    data["Iptc.Application2.Byline"]
                except:
                    pass
                else:
                    fotografer_cell.value = "; ".join(data["Iptc.Application2.Byline"])

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
            elif str(p).lower() in ("thumbs.db", "desktop.ini", "debug.xml"):
                continue
            # print(f" {p}")

            _per_row(c=c, path=p)
            c += 1

        self._save_excel(path=excel_fn)

    #
    #
    #

    def _make_new_asset(self, *, fn: str, moduleItemId: int, templateM: Module) -> int:
        if moduleItemId is None or moduleItemId == "None":
            raise SyntaxError(f"moduleItemdId {moduleItemdId} not allowed!")
        r = Record(templateM)
        r.add_reference(targetModule="Object", moduleItemId=moduleItemId)
        r.set_filename(path=fn)
        r.set_size(path=fn)
        newAssetM = r.toModule()
        new_asset_id = self.client.create_asset_from_template(
            templateM=newAssetM,
        )
        return new_asset_id

    def _prepare_template(self) -> Module:
        ws2 = self.wb["Conf"]
        templateID = int(ws2["B1"].value)
        print(f"Using asset {templateID} as template")
        template = self.client.get_template(ID=templateID, mtype="Multimedia")
        template.toFile(path=f".template{templateID}.orig.xml")
        return template
