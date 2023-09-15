"""
Should emulate the hotfolder eventually. That is we 

(a) read in a configuration from an Excel file
(b) process an input directory (non recursively),
(c) create new multimedia (=asset) records from a template
(d) upload/attach files to an multimedia records
(e) create a reference usually from object to multimedia record
(f) potentially set Standardbild
(g) move a successfully uploaded asset to another dir for safekeeping

In order to make the process transparent it is carried out in several steps

AssetUploader does NOT work RECURSIVELY


"""
import copy
from lxml import etree
from mpapi.constants import get_credentials
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

IGNORE_NAMES = (
    "thumbs.db",
    "desktop.ini",
    "debug.xml",
    "prepare.log",
    "prepare.ini",
    "checksum.md5",
)
IGNORE_SUFFIXES = (".py", ".ini", ".lnk")


class AssetUploader(BaseApp):
    def __init__(self, *, limit: int = -1) -> None:
        self.limit = int(limit)  # allows to break the go loop after number of items
        user, pw, baseURL = get_credentials()
        self.client = RIA(baseURL=baseURL, user=user, pw=pw)

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
                "desc": "automat. Vorschlag für Objekte-DS",
                "col": "F",
                "width": 9,
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
            "targetpath": {
                "label": "nach Bewegen der Datei",
                "desc": "wenn Upload erfolgreich",
                "col": "J",
                "width": 30,
            },
            "attached": {
                "label": "Asset hochgeladen?",
                "desc": "wenn Upload erfolgreich",
                "col": "K",
                "width": 15,
            },
            "standardbild": {
                "label": "Standardbild",
                "desc": "Standardbild setzen, wenn noch keines existiert",
                "col": "L",
                "width": 5,
            },
        }

    def go(self) -> None:
        """
        Do the actual upload based on the preparations in the Excel file

        (a) create new multimedia (=asset) records from a template
        (b) upload/attach files to an multimedia records
        (c) create a reference usually from object to multimedia record
        (d) update Excel to reflect changes
        (e) set Standardbild (if x in right place)
        (f) move uploaded file in uploaded subdir.

        Is it allowed to re-run go multiple time, e.g. to restart attachment? Yes!

        BTW: go is now called up in command line interface.

        """
        self._check_go()  # raise on error

        ws2 = self.wb["Conf"]
        if ws2["B4"].value is not None:
            u_dir = Path(ws2["B4"].value)
            if not u_dir.exists():
                print(f"Making new dir '{u_dir}'")
                u_dir.mkdir()

        for cells, rno in self._loop_table2(sheet=self.ws):
            # relative path; assume dir hasn't changed since scandir run
            print(f"{rno}: {cells['identNr'].value}")
            if cells["ref"].value is None:
                print(
                    "   object reference unknown, not creating assets nor attachments"
                )
                continue
            #  print(f"   object reference known, continue {cells['ref'].value}")
            self._create_new_asset(cells)
            self._upload_file(cells)
            self._set_Standardbild(cells)
            # save after every file to protect against interruptions
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
        ws2["B3"] = "EMArchiv"
        ws2[
            "C3"
        ] = "OrgUnits sind RIA-Bereiche in interner Schreibweise (ohne Leerzeichen)"
        ws2["C3"].alignment = Alignment(wrap_text=True)

        ws2["A4"] = "Zielverzeichnis"
        ws2[
            "C4"
        ] = """Verzeichnis für hochgeladene Dateien. UNC-Pfade brauchen zweifachen 
        Backslash. Wenn Feld leer. wird Datei nicht bewegt."""
        ws2["A5"] = "Filemask"
        ws2["B5"] = "*"
        ws2["C5"] = "Filemask für rekursive Suche, default ist *"

        ws2.column_dimensions["A"].width = 25
        ws2.column_dimensions["B"].width = 25
        ws2.column_dimensions["C"].width = 25

        for each in "A1", "A2", "A3", "A4", "A5":
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
        self._check_scandir()

        # looping thru files (usually pwd)
        if Dir is None:
            src_dir = Path(".")
        else:
            src_dir = Path(Dir)
        print(f"Scanning {src_dir}/{self.filemask}")

        self._drop_rows_if_file_gone()
        c = 1
        print("preparing file list...")
        file_list = src_dir.glob(f"**/{self.filemask}")
        # sorted lasts too long for large amounts of files
        if len(file_list) < 5000:
            file_list = sorted(file_list)
        print(f"done ({len(file_list)} items)")
        for p in file_list:  # dont try recursive!
            print(f"working on {p}")
            if p.name.startswith(".") or p.name == excel_fn or p.name == "prepare.xlsx":
                continue
            elif p.is_dir():
                continue
            elif p.suffix in IGNORE_SUFFIXES:
                continue
            elif p.name.lower() in IGNORE_NAMES:
                continue
            rno = self._path_in_list(p)  # returns None if not in list, else rno
            # if rno is None _file_to_list adds a new line
            self._file_to_list(path=p, rno=rno)
            if self.limit == c:
                print("* Limit reached")
                break
            c += 1
            # save every few thousand files to protect against interruption
            if c % 1000 == 0:
                self._save_excel(path=excel_fn)
        self._save_excel(path=excel_fn)

    def standardbild(self) -> None:
        """
        Loop thru Excel and only set standardbild if requested
        """
        print("Only setting Standardbild")
        self._check_scandir()
        for c, rno in self._loop_table2(sheet=self.ws):
            # relative path; assume dir hasn't changed since scandir run
            fn = c["filename"].value

            print(f"{rno}: {c['identNr'].value}")
            if c["ref"].value is None:
                print(
                    "   object reference unknown, not creating assets nor attachments"
                )
                continue
            self._set_Standardbild(c)
        self._save_excel(path=excel_fn)

    #
    # private
    #
    def _attach_asset(self, *, path: str, mulId: int, target_path: str) -> bool:
        """
        attach an asset file (at path) and, if successful, move the asset file to new
        location (target_path).
        """

        # if the file doesn't exist (anymore) it indicates major issues!
        if not Path(path).exists():
            raise Exception("ERROR 101: Path doesn't exist. Already uploaded?")

        print(f"   attaching {path} {mulId}")
        ret = self.client.upload_attachment(file=path, ID=mulId)
        # print(f"   success on upload? {ret}")
        if ret.status_code == 204:
            if target_path is not None:
                self._move_file(src=path, dst=target_path)
                return True
        else:
            # should this raise an error?
            print("   ATTACHING FAILED (HTTP REQUEST)!")
            return False

    def _check_go(self) -> None:
        """
        Checks requirements for go command. Raises on error.

        Saves workbook to self.wb
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

        check_if_none = {
            "B1": "ERROR: Missing configuration value: No templateID provided!",
            "B3": "ERROR: Missing configuration value: orgUnit not filled in!",
            # B4 is now optional
            # "B4": "ERROR: Missing configuration value: Target directory empty!",
        }
        ws2 = self.wb["Conf"]
        for cell in check_if_none:
            if ws2[cell].value is None:
                raise ConfigError(check_if_none[cell])

        if not Path(self.ws["A3"].value).exists():
            # got here after I manually uploaded one file somehow
            print("WARNING: File doesn't exist (anymore). Already uploaded?")

    def _check_scandir(self) -> None:
        """
        A couple of checks for scandir. Saves worksheet to self.wb.
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

        if self.ws.max_row < 2:
            raise ConfigError(
                f"ERROR: Scandir needs an initialized Excel sheet! {self.ws.max_row}"
            )

        ws2 = self.wb["Conf"]
        self.orgUnit = self._get_orgUnit(cell="B3")  # can be None

        if ws2["B5"].value is None:
            self.filemask = "*"
        else:
            self.filemask = ws2["B5"].value

    def _create_new_asset(self, cells: dict) -> None:
        # print("_create_new_asset")
        if cells["asset_fn_exists"].value == "None":
            templateM = self._prepare_template()
            fn = cells["filename"].value
            if not Path(fn).exists():
                raise ValueError(f"File does not exist: '{fn}'")
            # print(f"fn: {fn}")
            new_asset_id = self._make_new_asset(
                fn=fn, moduleItemId=cells["ref"].value, templateM=templateM
            )
            cells["asset_fn_exists"].value = new_asset_id
            cells["asset_fn_exists"].font = teal
            print(f"   asset {new_asset_id} created")

    def _exiv_creator(self, *, path: Path) -> Optional[str]:
        """
        Expect a pathlib path, try to read that file with exiv and return
        (a) a string with a single creator,
        (b) a semicolon separated list of creators as a str or
        (c) None if no creator could be found.

        A few file types are exempt from checking.
        """

        # known extensions that dont work with exif
        exclude_exts = (".jpg", ".exr", ".obj", ".pdf", ".xml", ".zip")
        if path.suffix.lower() in exclude_exts:
            print(f"\tExif: ignoring suffix {path}")
            return

        try:
            with pyexiv2.Image(str(path)) as img:
                img_data = img.read_iptc()
        except:
            print("   Exif:Couldn't open for exif")
            return

        try:
            img_data["Iptc.Application2.Byline"]
        except:
            print("   Exif:Didn't find photographer info")
            return
        else:
            return "; ".join(img_data["Iptc.Application2.Byline"])

    def _file_to_list(self, *, path: Path, rno=None):
        """
        If rno is None, add a new file to the end of the Excel list; else update the row
        specified by rno.

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

        # identNr_cell might be None, then we cant look up any objIds
        if cells["identNr"].value is None:
            print(f"WARNING: identNr cell is empty! {path.name}")
            return None

        if cells["objIds"].value == None:
            cells["objIds"].value = self.client.get_objIds(
                identNr=cells["identNr"].value, strict=True, orgUnit=self.orgUnit
            )

        if cells["parts_objIds"].value is None:
            partsL = self._has_parts(identNr=cells["identNr"].value)
            if partsL:
                cells["parts_objIds"].value = "; ".join(parts)
            else:
                cells["parts_objIds"].value = "None"
            cells["parts_objIds"].alignment = Alignment(wrap_text=True)

        if cells["ref"].value is None:
            # if asset_fn exists we assume that asset has already been uploaded
            # if no single objId has been identified, we will not create asset
            if cells["asset_fn_exists"].value == "None":
                # if single objId has been identified use it as ref
                objIds = cells["objIds"].value
                if objIds != "None" and ";" not in str(objIds):
                    cells["ref"].value = int(objIds)
                    cells["ref"].font = teal
                # if single part objId has been identified use it as ref
                elif cells["parts_objIds"].value != "None" and ";" not in str(
                    cells["parts_objIds"].value
                ):
                    cells["ref"].value = (
                        cells["parts_objIds"].value.split(" ")[0].strip()
                    )
                    cells["ref"].font = red
            else:
                cells["ref"].value = "None"
                cells["ref"].font = red

        if cells["targetpath"].value is None:
            # print("in targetpath")
            ws2 = self.wb["Conf"]
            if ws2["B4"].value is not None:
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
            # print("in photographer")
            creator = self._exiv_creator(path=path)
            if creator is None:
                cells["photographer"].value = "None"
            else:
                cells["photographer"].value = creator

    def _make_new_asset(self, *, fn: str, moduleItemId: int, templateM: Module) -> int:
        # print("enter _make_new_asset")
        if moduleItemId is None or moduleItemId == "None":
            raise SyntaxError(f"moduleItemdId {moduleItemdId} not allowed!")
        r = Record(templateM)
        r.add_reference(targetModule="Object", moduleItemId=moduleItemId)
        r.set_filename(path=fn)
        r.set_size(path=fn)
        newAssetM = r.toModule()
        # newAssetM.toFile(path="debug.template.xml")
        new_asset_id = self.client.create_asset_from_template(
            templateM=newAssetM,
        )
        print("ok")
        return new_asset_id

    def _move_file(self, *, src: str, dst: str) -> None:
        """
        What do I do if src or dst are None?
        """
        dstp = Path(dst)
        if not dstp.exists():
            shutil.move(src, dst)  # die if problems
            print(f"   moved to target '{dst}'")
        else:
            raise SyntaxError(f"ERROR: Target location already used! {dst}")

    def _path_in_list(self, path) -> None:
        """Returns True if filename is already in list (column A), else None."""
        rno = 3
        for row in self.ws.iter_rows(min_row=3):  # start at 3rd row
            fn = row[0].value
            if fn == str(path):
                return rno
            rno += 1
        return None

    def _prepare_template(self) -> Module:
        try:
            return self.templateM
        except:
            ws2 = self.wb["Conf"]
            templateID = int(ws2["B1"].value)
            print(f"Using asset {templateID} as template")
            self.templateM = self.client.get_template(ID=templateID, mtype="Multimedia")
            # template.toFile(path=f".template{templateID}.orig.xml")
            return self.templateM

    def _upload_file(self, cells) -> None:
        # print("enter _upload_file")
        if cells["attached"].value == None:
            if cells["ref"].value is not None:
                fn = cells["filename"].value
                ID = int(cells["asset_fn_exists"].value)
                if self._attach_asset(
                    path=fn, mulId=ID, target_path=cells["targetpath"].value
                ):
                    cells["attached"].value = "x"
                # save after every file that is uploaded
                self._save_excel(path=excel_fn)
        else:
            print("   asset already attached")

    def _set_Standardbild(self, c) -> None:
        """
        If column standardbild = x, try to set asset as standardbild for known object;
        only succeeds if object has no Standardbild yet.
        """
        # print("enter _set_Standardbild")
        if c["standardbild"].value is not None:
            if c["standardbild"].value.lower() == "x":
                objId = int(c["objIds"].value)
                mulId = int(c["asset_fn_exists"].value)
                self.client.mk_asset_standardbild2(objId=objId, mulId=mulId)
                c["standardbild"].value = "erledigt"
                self._save_excel(path=excel_fn)
                print("\tstandardbild set")
