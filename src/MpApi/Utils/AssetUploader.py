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
"""
import copy
from datetime import datetime
from lxml import etree
from mpapi.constants import get_credentials
from mpapi.module import Module
from MpApi.Record import Record  # should be MpApi.Record.Multimedia
from MpApi.Utils.BaseApp import BaseApp, ConfigError
from MpApi.Utils.logic import extractIdentNr, has_parts, is_suspicious, whole_for_parts
from MpApi.Utils.Ria import RIA

from openpyxl import Workbook  # load_workbook
from openpyxl.styles import Alignment, Font
from pathlib import Path
import PIL
import re
import shutil
from typing import Any, Optional
from tqdm import tqdm

excel_fn = Path(
    "upload14.xlsx"
)  # adding number of fields to prevent accidental overwriting of old versions
bak_fn = Path("upload14.xlsx.bak")
red = Font(color="FF0000")
parser = etree.XMLParser(remove_blank_text=True)
teal = Font(color="008080")
blue = Font(color="0000FF")

IGNORE_NAMES = (
    "checksum.md5",
    "desktop.ini",
    "debug.xml",
    "prepare.xlsx",
    "prepare.log",
    "prepare.ini",
    "upload.xlsx",
    "upload.xlsx.bak",
    str(excel_fn),
    str(bak_fn),
    "thumbs.db",
)
IGNORE_SUFFIXES = (".py", ".ini", ".lnk", ".tmp")


class AssetUploader(BaseApp):
    def __init__(self, *, limit: int = -1, offset: int = 3) -> None:
        self.limit = int(limit)  # allows to break the go loop after number of items
        self.offset = int(offset)  # set to 3 by default to start at 3 row
        user, pw, baseURL = get_credentials()
        self.client = RIA(baseURL=baseURL, user=user, pw=pw)
        self.objIds_cache: dict[str, str] = {}

        self.table_desc = {
            "filename": {
                "label": "Asset Dateiname",
                "desc": "aus Verzeichnis",
                "col": "A",  # 0
                "width": 20,
            },
            "identNr": {
                "label": "IdentNr",
                "desc": "aus Dateinamen",
                "col": "B",  # 1
                "width": 15,
            },
            "asset_fn_exists": {
                "label": "Assets mit diesem Dateinamen",
                "desc": "mulId(s) aus RIA",
                "col": "C",  # 2
                "width": 15,
            },
            "objIds": {
                "label": "objId(s) aus RIA",
                "desc": "exact match für diese IdentNr",
                "col": "D",  # 3
                "width": 15,
            },
            "parts_objIds": {
                "label": "Teile objId",
                "desc": "für diese IdentNr",
                "col": "E",  # 4
                "width": 20,
            },
            "whole_objIds": {
                "label": "Ganzes objId",
                "desc": "für diese IdentNr",
                "col": "F",  # 5
                "width": 20,
            },
            "ref": {
                "label": "Objekte-Link",
                "desc": "automat. Vorschlag für Objekte-DS",
                "col": "G",  # 6
                "width": 9,
            },
            "notes": {
                "label": "Bemerkung",
                "desc": "für Notizen",
                "col": "H",  # 7
                "width": 20,
            },
            "photographer": {
                "label": "Fotograf*in",
                "desc": "aus Datei",
                "col": "I",  # 8
                "width": 20,
            },
            "creatorID": {
                "label": "ID Urheber*in",
                "desc": "aus RIA",
                "col": "J",  # 9
                "width": 20,
            },
            "fullpath": {
                "label": "absoluter Pfad",
                "desc": "aus Verzeichnis",
                "col": "K",  # 10
                "width": 90,
            },
            "targetpath": {
                "label": "nach Bewegen der Datei",
                "desc": "wenn Upload erfolgreich",
                "col": "L",  # 11
                "width": 30,
            },
            "attached": {
                "label": "Asset hochgeladen?",
                "desc": "wenn Upload erfolgreich",
                "col": "M",  # 12
                "width": 15,
            },
            "standardbild": {
                "label": "Standardbild",
                "desc": "Standardbild setzen, wenn noch keines existiert",
                "col": "N",  # 13
                "width": 5,
            },
        }

    def backup_excel(self):
        try:
            shutil.copy(excel_fn, bak_fn)
        except KeyboardInterrupt:
            print("Catching keyboard interrupt during Excel operation; try again...")

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

        BTW: go is now called 'up' in command line interface.

        """
        self._check_go()  # raise on error

        ws2 = self.wb["Conf"]
        if ws2["B4"].value is not None:
            u_dir = Path(ws2["B4"].value)
            if not u_dir.exists():
                print(f"Making new dir '{u_dir}'")
                u_dir.mkdir()

        # breaks at limit, but doesn't save on its own
        for cells, rno in self._loop_table2(sheet=self.ws, offset=self.offset):
            # relative path; assume dir hasn't changed since scandir run
            print(f"{rno}: {cells['identNr'].value} up")
            if cells["ref"].value == "None":
                print(
                    "   object reference unknown, not creating assets nor attachments"
                )
                continue  # SEEMS NOT TO WORK, so we try with else!
            else:
                #  print(f"   object reference known, continue {cells['ref'].value}")
                try:
                    self._create_new_asset(cells)
                    self._upload_file(cells, rno)
                    self._set_Standardbild(cells)
                except KeyboardInterrupt:
                    print(
                        "Catching keyboard interrupt during RIA operation; try again..."
                    )
                # dont save if here, save after loop instead
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
        ws2["B1"] = ""
        ws["C1"] = """Hendryks default jpg 6697400"""

        ws2["C1"] = "Asset"

        ws2["A2"] = "verlinktes Modul"
        ws2["B2"] = "Objekte"  # todo alternativer Wert Restaurierung

        ws2["A3"] = "OrgUnit (optional)"
        ws2["B3"] = ""
        ws2[
            "C3"
        ] = """OrgUnits sind RIA-Bereiche in interner Schreibweise (ohne Leerzeichen). 
        Die Suche der existierenden Assets wird auf den angegebenen Bereich eingeschränkt. 
        Wenn kein Bereich angegenen, wird die Suche auch nicht eingeschränkt. Gültige 
        orgUnits sind z.B. EMArchiv, EMMusikethnologie, EMMedienarchiv, EMPhonogrammArchiv"""
        # ws2["C3"].alignment = Alignment(wrap_text=True)

        ws2["A4"] = "Zielverzeichnis"
        ws2[
            "C4"
        ] = """Verzeichnis für hochgeladene Dateien. UNC-Pfade brauchen zweifachen 
        Backslash. Wenn Feld leer. wird Datei nicht bewegt."""
        ws2["A5"] = "Filemask"
        ws2["B5"] = "*.jpg"  # temporary new default
        ws2["C5"] = "Filemask für rekursive Suche, default ist *"

        ws2.column_dimensions["A"].width = 25
        ws2.column_dimensions["B"].width = 25
        ws2.column_dimensions["C"].width = 25

        ws2["A6"] = "Erstellungsdatum"
        ws2["B6"] = datetime.today().strftime("%Y-%m-%d")

        ws2["A7"] = "Ignore suspicious?"
        ws2["B7"] = "True"

        for row in ws2.iter_rows(min_col=1, max_col=1):
            for cell in row:
                cell.font = Font(bold=True)

        for row in ws2.iter_rows(min_col=3, max_col=3):
            for cell in row:
                cell.font = blue

        self._save_excel(path=excel_fn)

    def initial_offset(self) -> int:
        """
        Returns number of rows with x in int representing the first row in the Excel without x in field
        "attached" (aka "Asset hochgeladen").
        """
        self._init_wbws()

        # we need a loop that doesn't break on limit
        c = 3  # row counter
        for row in self.ws.iter_rows(min_row=3):  # start at 3rd row
            if row[12].value == "x":
                c += 1
        return c

    def photo(self):
        """
        Loop thru the excel entries and lookup ids for fotographers/creators if no ID
        filled in yet.
        """
        self._init_wbws()
        for cells, rno in self._loop_table2(sheet=self.ws):
            self._photo(cells)
        self._save_excel(path=excel_fn)

    def scandir(self, *, Dir: Optional[Path] = None, offset: int = 0) -> None:
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
        # fast-forward cache: jump over all the files that have
        # already been attached according to Excel
        attached_cache = self._attached_cache()
        # rm excel rows if file no longer exists on disk
        # self._drop_rows_if_file_gone(col="I", cont=len(attached_cache))
        print("   in case of substantial file changes, create new Excel sheet")
        self._save_excel(path=excel_fn)

        c = 1  # counting files here, no offset for headlines
        print("Preparing file list...")
        file_list = src_dir.glob(f"**/{self.filemask}")
        file_list2 = list()
        chunk_size = self.limit - offset
        print(f"   chunk size: {chunk_size}")
        with tqdm(total=chunk_size + len(attached_cache)) as pbar:
            for p in file_list:
                p_abs = str(p.absolute())
                # dirty, temporary...
                ignore_dir = "W:\0_Neu"
                if p_abs.startswith(ignore_dir):
                    continue
                if (
                    p.name.startswith(".")
                    or p.name.startswith("debug")
                    or p.name.lower() in IGNORE_NAMES
                ):
                    # print("   exluding reason 1")
                    continue
                elif p.is_dir():
                    # print("   exluding reason 2: dir")
                    continue
                # we dont need to ignore suffixes if we look for *.jpg etc.
                elif self.filemask == "*" and p.suffix in IGNORE_SUFFIXES:
                    continue
                    c += 1  # attached files we want to count
                    # print(f"   already in RIA {p_abs}")
                pbar.update()
                if p_abs not in attached_cache:
                    file_list2.append(p)
                if self.limit == c:
                    print("* Limit reached")
                    break
                c += 1

        print(f"Sorting file list... {len(file_list2)}")
        file_list2 = sorted(file_list2)

        print("Scanning file list...")
        for p in file_list2:
            print(f"scandir: {p}")
            rno = self._path_in_list(p.name, 0)
            # rno is the row number in Assets sheet
            # rno is None if file not in list
            rno = self._file_to_list(path=p, rno=rno)

            # save every thousand files to protect against interruption
            if rno is not None and rno % 1000 == 0:
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

    def wipe(self) -> None:
        """
        Loop thru excel and delete all data rows. This re-creates the state of
        'upload init'. Can be useful for running another scandir.

        Beware of --limit.
        """
        self._init_wbws()
        self._wipe()

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
            raise FileNotFoundError("ERROR: Path doesn't exist. Already uploaded?")

        print(f"   attaching {path}")
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

    def _attached_cache(self) -> set:
        rno = 3  # row counter;
        cache = set()
        # loop without limit
        for row in self.ws.iter_rows(min_row=rno):  # start at 3rd row
            cells = self._rno2dict(rno)
            fullpath = cells["fullpath"].value
            attached = cells["attached"].value
            # print(f"{rno} {cells}")
            if attached == "x":
                cache.add(fullpath)
                # print(f"attached cache: {fullpath} {attached}")
            rno += 1
        print(f"Skipping files already uploaded ({len(cache)} files)")
        return cache

    def _check_go(self) -> None:
        """
        Checks requirements for go command. Raises on error.

        Saves workbook to self.wb
        """
        self._init_wbws()

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
        self._init_wbws()

        if self.ws.max_row < 2:
            raise ConfigError(
                f"ERROR: Scandir needs an initialized Excel sheet! {self.ws.max_row}"
            )

        ws2 = self.wb["Conf"]
        self.orgUnit = self._get_orgUnit(cell="B3")  # can be None

        if ws2["B5"].value is None:
            self.filemask: str = "*"
        else:
            self.filemask = ws2["B5"].value

        if ws2["B7"].value.lower() == "true":
            self.ignore_suspicious = True
        else:
            self.ignore_suspicious = False

    def _create_from_template(
        self, *, fn: str, objId: int, templateM: Module, creatorID: Optional[int] = None
    ) -> Optional[int]:
        """
        Creates a new asset record in RIA by copying the template. Also fill in
        - object reference
        - filename
        - size

        CHANGES
        - Used to die if assetID was not defined; now just returns
        - Used to be called _make_new_asset
        """
        # print("enter _create_from_template")
        if objId is None or objId == "None":
            # Do we want to log this error/warning in Excel?
            print(f"moduleItemdId '{objId}' not allowed! Not creating new asset.")
            return None
        r = Record(templateM)
        r.add_reference(targetModule="Object", moduleItemId=objId)
        r.set_filename(path=fn)
        r.set_size(path=fn)
        if creatorID is not None:
            print(f"   creatorID {creatorID} _create_from_template")
            r.set_creator(ID=creatorID)
        newAssetM = r.toModule()
        newAssetM.toFile(path="debug.template.xml")
        new_asset_id = self.client.create_asset_from_template(
            templateM=newAssetM,
        )
        return new_asset_id

    def _create_new_asset(self, cells: dict) -> None:
        """
        Copies a template specified in the configuration.
        Gets called during upload (go) phase.
        """
        # print("_create_new_asset")
        if cells["asset_fn_exists"].value == "None":
            templateM = self._prepare_template()
            fn = cells["fullpath"].value
            if not Path(fn).exists():
                # fn had been found during a scandir process
                # if it is not found anymore at this time the file system has changed in
                # an important way which warrants an error and the user's attention.
                raise FileNotFoundError(f"File not found: '{fn}'")
            # print(f"fn: {fn}")
            creatorID = cells["creatorID"].value
            # print(f"   template with creatorID {creatorID}")
            new_asset_id = self._create_from_template(
                fn=fn,
                objId=cells["ref"].value,
                templateM=templateM,
                creatorID=creatorID,
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
            print(f"\tExif: ignoring suffix {path.suffix}")
            return None

        try:
            with PIL.Image(str(path)) as img:
                img_data = img._getexif()
                # img_data = img.read_iptc() pyexiv2
        except:
            print("\tExif:Couldn't open for exif")
            return None

        try:
            img_data["Iptc.Application2.Byline"]
        except:
            print("\tExif:Didn't find photographer info")
            return None
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
        fullpath = path.absolute()  # .resolve() problems on UNC
        # only write in empty fields
        # relative path, but not if we use this recursively
        if cells["filename"].value is None:
            cells["filename"].value = path.name

        self._write_identNr(cells, path)

        if cells["fullpath"].value is None:
            cells["fullpath"].value = str(fullpath)
        # print (f"***{path}")
        self._write_asset_fn(cells, fullpath)

        # identNr_cell might be None, then we cant look up any objIds
        identNr = cells["identNr"].value
        if identNr is None:
            print(f"WARNING: identNr cell is empty!!!\n {path.name}")
            return

        if cells["objIds"].value == None:
            cells["objIds"].value = self._get_objIds(identNr=identNr)

        self._write_parts(cells)
        self._write_whole(cells)
        self._write_ref(cells)
        self._write_targetpath(cells)
        ref = cells["ref"].value
        print(f"   {rno}: {identNr} [{ref}]")
        self._write_photographer(cells, path)
        self._write_photoID(cells)
        return rno

    def _init_wbws(self):
        if not excel_fn.exists():
            raise ConfigError(f"ERROR: {excel_fn} NOT found!")
        self.wb = self._init_excel(path=excel_fn)

        # die if not writable so that user can close it before waste of time
        self._save_excel(path=excel_fn)

        try:
            self.ws = self.wb["Assets"]
        except:
            raise ConfigError("ERROR: Excel file has no sheet 'Assets'")

    def _get_mulId(self, *, fullpath: Path) -> int | str:
        """
        Expects a fullpath, returns mulId. Currently as str, should return int, I guess.
        """
        idL = self.client.fn_to_mulId(fn=str(fullpath.name), orgUnit=self.orgUnit)
        if len(idL) == 0:
            mulId = "None"
        else:
            mulId = "; ".join(idL)
        return mulId

    def _get_objIds(self, *, identNr: str):
        """
        For a given identNr:str return the objId or objIds. If multiple objIds match,
        they are returned as a string that is joined by "; ". If there is no match,
        the returned string is "None".

        The string is cached, so if you query the same identNr again the same run
        of the script, it doesn't need another TCP request.

        This is an obsolete version.
        """
        if identNr in self.objIds_cache:
            return self.objIds_cache[identNr]
        else:
            objIds = self.client.get_objIds(
                identNr=identNr, strict=True, orgUnit=self.orgUnit
            )
            self.objIds_cache[identNr] = objIds
            # print(f"   new objId from RIA [{objIds}]")
            return objIds

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

    def _prepare_template(self) -> Module:
        try:
            return self.templateM
        except:
            ws2 = self.wb["Conf"]
            templateID = int(ws2["B1"].value)
            print(f"   template from asset {templateID}")
            self.templateM: Module = self.client.get_template(
                ID=templateID, mtype="Multimedia"
            )
            if not self.templateM:
                raise ValueError("Template not available!")
            # template.toFile(path=f".template{templateID}.orig.xml")
            return self.templateM

    def _upload_file(self, cells, rno) -> None:
        # print("enter _upload_file")
        if cells["attached"].value == None:
            fn = cells["fullpath"].value
            ID = int(cells["asset_fn_exists"].value)
            if self._attach_asset(
                path=fn, mulId=ID, target_path=cells["targetpath"].value
            ):
                cells["attached"].value = "x"
            # save after every file that is uploaded
            if rno is not None and rno % 10 == 0:
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

    def _write_asset_fn(self, cells, fullpath):
        if cells["asset_fn_exists"].value is None:
            # if cache the known paths drastically reduces http requests
            cells["asset_fn_exists"].value = self._get_mulId(fullpath=fullpath)
            if cells["asset_fn_exists"].value != "None":
                print("   asset exists in RIA already")
                cells["attached"].value = "x"
                cells["attached"].font = red
                # red signifies that asset has already been uploaded, but it has not been
                # tested if asset is linked to any or correct object.
                # We need the x here to fast-forward during continous mode

    def _write_identNr(self, cells: dict, path: Path) -> None:
        if cells["identNr"].value is None:
            identNr = extractIdentNr(path=path)  # returns Python's None on failure
            if self.ignore_suspicious and is_suspicious(identNr=identNr):
                return
            # currently only accepting identNrs that dont look suspicious
            # print(f"***{identNr=}")
            cells["identNr"].value = identNr

            if is_suspicious(identNr=identNr):
                cells["identNr"].font = red

    def _write_parts(self, cells):
        if cells["parts_objIds"].value is None:
            # print("\t_write_parts")
            # we want to use the new get_objIds_beginswith which returns a dict,
            # but it doesn't work yet
            IDs = self.client.get_objIds2(
                # no orgUnit. Should that remain that way?
                identNr=cells["identNr"].value,
                strict=False,
            )
            if IDs:
                IDs = [str(e) for e in IDs]
                cells["parts_objIds"].value = "; ".join(IDs)
            else:
                cells["parts_objIds"].value = "None"

    def _write_whole(self, cells):
        if cells["whole_objIds"].value is None:
            identNr = cells["identNr"].value
            ident_whole = whole_for_parts(identNr)
            # print(f"\t_write_whole {ident_whole}")
            if identNr != ident_whole:
                cells["whole_objIds"].value = f"{ident_whole}: " + self._get_objIds(
                    identNr=ident_whole
                )
            else:
                cells["whole_objIds"].value = "None"

    def _write_photoID(self, cells):
        # print("\t_write_photoID")
        cname = cells["photographer"].value
        if cells["creatorID"].value is None and cname != "None" and cname is not None:
            print(f"\tlooking up creatorID '{cname}'")
            idL = self.client.get_photographerID(name=cname)
            # can be None, not "None". Since i may want to run 'upload foto' again after i have
            # added photographer to RIA's person module.
            if idL is None:
                print(f"\tcreatorID not found")
            else:
                cells["creatorID"].value = "; ".join(idL)
                # print(cells["creatorID"].value)

    def _write_photographer(self, cells, path):
        # if file already attached, we dont need to look for photographer again
        # assuming attached is either None or x, but not "" or anything
        if cells["photographer"].value is None and cells["attached"].value is None:
            # print("in photographer")
            creator = self._exiv_creator(path=path)
            if creator is None:
                cells["photographer"].value = "None"
            else:
                cells["photographer"].value = creator

    def _write_ref(self, cells):
        if cells["ref"].value is None:
            # if asset_fn exists we assume that asset has already been uploaded
            # if no single objId has been identified, we will not create asset
            whole_objIds = cells["whole_objIds"].value
            if cells["asset_fn_exists"].value == "None":
                # if single objId has been identified use it as ref
                objIds = cells["objIds"].value
                # if single part objId has been identified use it as ref
                if objIds != "None" and ";" not in str(objIds):
                    print("   taking ref from objIds...")
                    cells["ref"].value = int(objIds)
                    cells["ref"].font = teal
                # taking ref from part
                elif cells["parts_objIds"].value != "None" and ";" not in str(
                    cells["parts_objIds"].value
                ):
                    print("   taking ref from parts...")
                    cells["ref"].value = (
                        cells["parts_objIds"].value.split(" ")[0].strip()
                    )
                    cells["ref"].font = red
                elif not "None" in whole_objIds:  # this only works for single entries
                    ident_whole, objId = whole_objIds.split(": ")
                    objId = int(objId)
                    print("   taking ref from whole...")
                    # assuming ref is empty at this point...
                    cells["ref"].value = objId
                else:  # right indent?
                    cells["ref"].value = "None"
                    cells["ref"].font = red  # seems not to work!

    def _write_targetpath(self, cells):
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
