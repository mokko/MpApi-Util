"""
Should emulate the hotfolder eventually. That is we 

(a) read in a configuration from an Excel file
(b) process an input directory (non recursively),
(c) create new multimedia (=asset) records from a template
(d) upload/attach files to an multimedia records
(e) create a reference usually from object to multimedia record

In order to make the process transparent it is carried out in several steps

AssetUploader does not work RECURSIVELY
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
            "asset_fn_exists": {
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
            "parts_objIds": {
                "label": "Teile objId",
                "desc": "für diese IdentNr",
                "col": "E",
                "width": 20,
            },
            "ref": {
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
                "width": 90,
            },
            "attached": {
                "label": "Asset hochgeladen?",
                "desc": "wenn Upload erfolgreich",
                "col": "K",
                "width": 15,
            },
            "targetpath": {
                "label": "nach Bewegen der Datei",
                "desc": "wenn Upload erfolgreich",
                "col": "J",
                "width": 30,
            },
        }

    def go(self) -> None:
        """
        Do the actual upload based on the preparations in the Excel file

        (a) create new multimedia (=asset) records from a template
        (b) upload/attach files to an multimedia records
        (c) create a reference usually from object to multimedia record
        (d) update Excel to reflect changes
        (e) move uploaded file in uploaded subdir.

        Should we rename from "go" to "upload" for consistency?

        Is it allowed to re-run go multiple time, e.g. to restart attachment?

        """
        # print("Enter go")
        self._go_checks()  # raise on error

        templateM = self._prepare_template()
        ws2 = self.wb["Conf"]
        if ws2["B4"].value is None:
            raise Exception("ERROR: Destination directory empty!")
        u_dir = Path(ws2["B4"].value)
        if not u_dir.exists():
            print(f"Making new dir '{u_dir}'")
            u_dir.mkdir()

        for c, rno in self._loop_table2():
            # relative path; assume dir hasn't changed since scandir run
            fn = c["filename"].value

            print(f"{rno}: {c['identNr'].value}")
            if c["ref"].value is None:
                print(
                    "   object reference unknown, not creating assets nor attachments"
                )
                continue
            else:
                print(f"   object reference known, continue {c['ref'].value}")

            if c["asset_fn_exists"].value == "None":
                new_asset_id = self._make_new_asset(
                    fn=fn, moduleItemId=c["ref"].value, templateM=templateM
                )
                c["asset_fn_exists"].value = new_asset_id
                c["asset_fn_exists"].font = teal
                print(f"   asset {new_asset_id} created")
            # else:
            #    print(f"   asset exists already: {c['asset_fn_exists'].value}")

            if c["attached"].value == None:
                if c["ref"].value is not None:
                    ID = int(c["asset_fn_exists"].value)
                    if self._attach_asset(
                        path=fn, mulId=ID, target_path=c["targetpath"].value
                    ):
                        c["attached"].value = "x"
                        # self._save_excel(path=excel_fn)  # save after every file
            else:
                print("   asset already attached")
            self._save_excel(path=excel_fn)

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
        self._write_table_description(description=self.table_desc, sheet=ws)

        #
        # Conf Sheet
        #
        ws2 = self.wb.create_sheet("Conf")
        ws2["A1"] = "templateID"
        ws2["C1"] = "Asset"

        ws2["A2"] = "verlinktes Modul"
        ws2["B2"] = "Objekte"  # todo alternativer Wert Restaurierung

        ws2["A3"] = "OrgUnit (optional)"
        ws2["B3"] = "EMMusikethnologie"
        ws2[
            "C3"
        ] = "OrgUnits sind RIA-Bereiche in interner Schreibweise (ohne Leerzeichen)"
        ws2["C3"].alignment = Alignment(wrap_text=True)

        ws2["A4"] = "Uploaded Directory"
        ws2[
            "C4"
        ] = "Für hochgeladene Verzeichnisse. UNC-Pfade brauchen in Python zweifache Backslash."

        ws2.column_dimensions["A"].width = 25
        ws2.column_dimensions["B"].width = 25
        ws2.column_dimensions["C"].width = 25

        for each in "A1", "A2", "A3", "A4":
            ws2[each].font = Font(bold=True)

        self._save_excel(path=excel_fn)

    def scandir(self, *, Dir=None) -> None:
        """
        Scans local directory and enters values for each file in the Excel

        It is possible to re-run scandir. While re-running files in list that no longer
        exist will be deleted from the list and new files on disk will be added at the
        end of the list. The upshot is that user can rename files on disk or delete
        rows in Excel to re-index files by a scandir re-run.

        add new files, manually delete rows from Excel and
        to update the table by re-running scandir.
        """
        self._scandir_checks()

        # looping thru files (usually pwd)
        if Dir is None:
            src_dir = Path(".")
        else:
            src_dir = Path(Dir)
        print(f"Scanning pwd {src_dir}")

        self._drop_rows_if_file_gone()
        c = 1
        for p in src_dir.glob("*"):  # dont try recursive!
            if str(p).startswith(".") or p == excel_fn:
                continue
            elif p.suffix == ".py" or p.suffix == ".ini" or p.suffix in (".lnk"):
                continue
            elif p.is_dir():
                continue
            elif str(p).lower() in ("thumbs.db", "desktop.ini", "debug.xml"):
                continue
            rno = self._path_in_list(p)  # returns None if not in list, else rno
            self._file_to_list(path=p, rno=rno)  # update or new row in table
            if self.limit == c:
                print("* Limit reached")
                break
            c += 1
        self._save_excel(path=excel_fn)

    #
    # private
    #
    def _attach_asset(self, *, path: str, mulId: int, target_path: str) -> bool:
        """
        attach an asset file (at path) and, if successful, move the asset file to new
        location (target_path).
        """
        if target_path is None:
            raise SyntaxError("ERROR: target path should not be None")

        # if the file doesn't exist (anymore) it indicates major issues!
        if not Path(path).exists():
            raise Exception("ERROR 101: Path doesn't exist. Already uploaded?")

        print(f"   attaching {path} {mulId}")
        ret = self.client.upload_attachment(file=path, ID=mulId)
        # print(f"   success on upload? {ret}")
        if ret.status_code == 204:
            self._move_file(src=path, dst=target_path)
            return True
        else:
            # should this raise an error?
            print("   ATTACHING FAILED (HTTP REQUEST)!")
            return False

    def _file_to_list(self, *, path: Path, rno=None):
        """
        if rno is None add a new file to the end of te Excel list, else update the row specified by
        rno.

        This is for the scandir step.
        """
        if rno is None:
            rno = self.ws.max_row + 1  # max_row seems to be zero-based
        cells = self._rno2dict(rno)
        identNr = extractIdentNr(path=path)  # returns Python's None on failure
        # only write in empty fields
        # relative path, but not if we use this recursively
        if cells["filename"].value is None:
            cells["filename"].value = path.name
        if cells["identNr"].value is None:
            cells["identNr"].value = identNr
        if cells["fullpath"].value is None:
            # .resolve() problems on UNC
            cells["fullpath"].value = str(path.absolute())
        # print (f"***{path}")
        if cells["asset_fn_exists"].value is None:
            idL = self.client.fn_to_mulId(fn=str(path), orgUnit=self.orgUnit)
            if len(idL) == 0:
                cells["asset_fn_exists"].value = "None"
            else:
                cells["asset_fn_exists"].value = "; ".join(idL)

        # in rare cases identNr_cell might be None, then we cant look up any objIds
        if cells["identNr"].value is None:
            print(f"WARNING: identNr cell is empty! {path.name}")
            return None

        if cells["objIds"].value == None:
            cells["objIds"].value = self.client.get_objIds(
                identNr=cells["identNr"].value, strict=True, orgUnit=self.orgUnit
            )

        if cells["parts_objIds"].value is None:
            cells["parts_objIds"].value = self.client.get_objIds2(
                identNr=cells["identNr"].value, strict=False
            )
            cells["parts_objIds"].alignment = Alignment(wrap_text=True)

        if cells["ref"].value is None:
            # if asset_fn exists we assume that asset has already been uploaded
            # if no single objId has been indentified, we will not create asset
            if cells["asset_fn_exists"].value == "None":
                # if single objId has been identified use it as ref
                objIds = int(cells["objIds"].value)
                if objIds != "None":  # ";" not in str(objIds)
                    cells["ref"].value = objIds
                    cells["ref"].font = teal
                # if single part objId has been identified use it as ref
                elif (
                    cells["parts_objIds"].value != "None"
                    and ";" not in cells["parts_objIds"].value
                ):
                    cells["ref"].value = (
                        cells["parts_objIds"].value.split(" ")[0].strip()
                    )
                    cells["ref"].font = red
            else:
                cells["ref"].value = "None"
                cells["ref"].font = red

        if cells["targetpath"].value is None:
            ws2 = self.wb["Conf"]
            if ws2["B4"].value is None:
                raise ConfigError("WARNING: orgUnit not filled in!")
            else:
                u_dir = Path(ws2["B4"].value)
            fn = Path(cells["filename"].value)
            t = u_dir / fn
            while t.exists():
                t = self._plus_one(t)
            else:
                cells["targetpath"].value = str(t)
                cells["targetpath"].font = teal

        print(f"   {rno}: {path.name} -> {identNr} [{cells['ref'].value}]")
        if cells["photographer"].value is None:
            # known extensions that dont work with exif
            if path.suffix == ".jpg" or path.suffix == ".pdf":
                cells["photographer"].value = "None"
                return

            try:
                with pyexiv2.Image(str(path)) as img:
                    img_data = img.read_iptc()
            except:
                print("   Couldn't open for exif")
                cells["photographer"].value = "None"
                return
            try:
                img_data["Iptc.Application2.Byline"]
            except:
                print("   Didn't find photographer info")
                cells["photographer"].value = "None"
                return
            else:
                cells["photographer"].value = "; ".join(
                    img_data["Iptc.Application2.Byline"]
                )

    def _go_checks(self) -> None:
        """
        Checks requirements for go command. Raises on error.
        """
        # check if excel exists, has the expected shape and is writable
        if not excel_fn.exists():
            raise ConfigError(f"ERROR: {excel_fn} NOT found!")

        self.wb = self._init_excel(path=excel_fn)

        # die if not writable so that user can close it before waste of time
        self._save_excel(path=excel_fn)

        try:
            self.ws = self.wb["Assets"]
        except:
            raise ConfigError("ERROR: Excel file has no sheet 'Assets'")

        ws2 = self.wb["Conf"]
        if ws2["B1"] is None:
            raise ConfigError(
                "ERROR: Missing configuration value: no templateID provided"
            )
        if ws2["B3"] is None:
            raise ConfigError(
                "ERROR: Missing configuration value: no dir for uploaded files"
            )

        if not Path(self.ws["A3"].value).exists():
            raise Exception("ERROR: File doesn't exist (anymore). Already uploaded?")

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

    def _move_file(self, *, src: str, dst: str) -> None:
        """
        What do I do if src or dst are None?
        """
        dstp = Path(dst)
        if not dstp.exists():
            shutil.move(src, dst)
            print(f"   moved to target '{dst}'")
        else:
            raise SyntaxError(f"ERROR: target location already used! {dst}")

    def _scandir_checks(self) -> None:
        # check if excel exists, has the expected shape and is writable
        if not excel_fn.exists():
            raise ConfigError(f"ERROR: {excel_fn} NOT found!")

        self.wb = self._init_excel(path=excel_fn)

        # die if not writable so that user can close it before waste of time
        self._save_excel(path=excel_fn)
        try:
            self.ws = self.wb["Assets"]
        except:
            raise ConfigError("ERROR: Excel file has no sheet 'Assets'")

        if self.ws.max_row < 2:
            raise ConfigError(
                f"ERROR: Scandir needs an initialized Excel sheet! {self.ws.max_row}"
            )

        conf_ws = self.wb["Conf"]
        orgUnit = conf_ws["B3"].value  # can be None
        if orgUnit is None:
            pass
        elif orgUnit.strip() == "":
            orgUnit = None
        self.orgUnit = orgUnit

        # todo: check that target_dir is filled-in
        if conf_ws["C4"].value is None:
            raise ConfigError("ERROR: Need target dir in B4")

    def _path_in_list(self, path) -> None:
        """Returns True of filename is already in list (column A), else False."""
        rno = 3
        for row in self.ws.iter_rows(min_row=3):  # start at 3rd row
            fn = row[0].value
            if fn == str(path):
                return rno
            rno += 1
        return None

    def _prepare_template(self) -> Module:
        ws2 = self.wb["Conf"]
        templateID = int(ws2["B1"].value)
        print(f"Using asset {templateID} as template")
        template = self.client.get_template(ID=templateID, mtype="Multimedia")
        template.toFile(path=f".template{templateID}.orig.xml")
        return template
