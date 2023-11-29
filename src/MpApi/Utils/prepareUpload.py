"""
Prepare for assets for upload (e.g with regular Bildimport)

At heart, this tool creates Object records for properly named asset files. New records 
are copied from a template record and get the identNr from the file.

With this tool we 
- recursively scan a directory
- filter for specific files (e.g. with "-KK" or only *.jpg)
- extract the identNr from filename
- check if asset has already been uploaded (sort of a "Dublette")
- lookup objId by identNr
- mark cases where extracted identNr are suspicious
- figure out cases where object record doesn't exit yet
- write results into spreadsheet
- for those cases create object records by copying a template record
- write the new identNr in the new record

CONCEPT
This tool is meant to be used by a person that we'll call the editor. The editor runs 
the script multiple times in different phases. The script writes its output into an
Excel file which we also use for configuration values. For each phase, the edior checks 
the results typically in the Excel file and, if necessary, corrects something. 

Prepare works on current working directory (aka pwd) and can work recursively, if so
configured (using the filemask in Conf[iguration] sheet of the Excel file).

There are now four phases
(0) init
(1) scandir 
(2) checkria and
(3) createobjects
(4) movedupes (optional)

   $ prepare scandir 
   $ prepare checkria  
   $ prepare createobjects    

After running scandisk
- check IdentNr have successfully been extracted
- if files are not named correctly/consistently, rename them
- check that schema ids have been identified; if necessary update schema db
- check if already uploaded results are plausible (current check is not exact)
- if there are a number of assets that have already been uploaded, consider moving them
  away using other util
- check cases where one file has multiple mulIds objIds
- if necessary delete Excel and re-run scandisk phase

After running checkria
- check if candidates are plausible
- revise candidates manually if desired

After running createobjects
- preserve Excel file for documentation; contains ids of newly created records

Update 
November 2023
- new step init to make it more similar to upload
April 2023
- changes to cli frontend
  (1) no more separate config file ('prepare.ini'), instead we use prepare.xlsx 
  (2) We now scan current working directory 
  (3) We get RIA credentials from $HOME/.RIA file  
  (4) 'prepare scandir' (without -p for phase)
  (5) hardcoded "prepare.xlsx" file name
  (6) scandisk renamed to scandir with alias init to be more similar to mover and upload
  (7) currently filemask is not configurable so always falls back to default
- changes inside
  (8) the indivdual checks from checkria into a single loop
  (9) got rid of old code
  (10) use the filename identNr parser from logic
TODO
- scandir should be re-runnable
- we should be able to set Standardbild
- Make use of the log file
"""

import configparser  # todo replace with toml in future
import logging
from lxml import etree
from mpapi.module import Module
from mpapi.constants import get_credentials
from MpApi.Utils.BaseApp import BaseApp, ConfigError, NoContentError
from MpApi.Utils.identNr import IdentNrFactory
from MpApi.Utils.logic import extractIdentNr
from MpApi.Utils.Ria import RIA
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
import openpyxl.cell.cell
from pathlib import Path
import re
import shutil
from typing import Any, Optional

red = Font(color="FF0000")


class PrepareUpload(BaseApp):
    def __init__(
        self,
        *,
        limit: int = -1,
    ) -> None:
        user, pw, baseURL = get_credentials()
        self.client = RIA(baseURL=baseURL, user=user, pw=pw)
        print(f"Logged in as '{user}'")
        self.limit = int(limit)
        if self.limit != -1 and self.limit < 3:
            raise ValueError("ERROR: limit < 3 is pointless!")
        print(f"Using limit {self.limit}")
        # self._init_log()
        self.excel_fn = Path("prepare.xlsx")
        if self.excel_fn.exists():
            print(f"* {self.excel_fn} exists already")
        else:
            print(f"* About to make new Excel '{self.excel_fn}'")

        self.table_desc = {
            "filename": {
                "label": "Dateiname",
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
                "label": "Asset hochgeladen?",
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
                "label": "Teile/Ganzes",
                "desc": "objId für Teile/Ganzes",
                "col": "E",
                "width": 20,
            },
            "candidate": {
                "label": "Kandidat",
                "desc": "neue Objekte erzeugen?",
                "col": "F",
                "width": 7,
            },
            "notes": {
                "label": "Bemerkung",
                "desc": "",
                "col": "G",
                "width": 20,
            },
            "fullpath": {
                "label": "Pfad",
                "desc": "aus Verzeichnis",
                "col": "H",
                "width": 115,
            },
            "schema": {
                "label": "Schema",
                "desc": "aus IdentNr",
                "col": "I",
            },
            "schemaId": {
                "label": "SchemaId",
                "desc": "aus IdentNr",
                "col": "J",
            },
            "duplicate": {
                "label": "Duplikat",
                "desc": "aus IdentNr",
                "col": "K",
            },
        }
        self.wb = self._init_excel(path=self.excel_fn)
        self.ws = self._init_sheet(workbook=self.wb)  # explicit is better than implicit

    #
    # public
    #

    def checkria(self) -> None:
        """
        We loop thru the Excel table, test if
        (a) assets with the given filename exist already
        (b) figure out the objId for the identNr
        (c) based on this information, fill in the candidate cell
        """
        self._raise_if_excel_has_no_content()
        for cells, rno in self._loop_table2(sheet=self.ws):
            if cells["assetUploaded"] is not None and cells["identNr"] is not None:
                self.mode = "ff"
            else:
                self.mode = ""
            self._asset_exists_already(cells)
            self._objId_for_ident(cells)
            self._fill_in_candidate(cells)
            self._checkria_messages(cells, rno)

            if rno is not None and rno % 100 == 0:
                # dont save when in fast forward mode
                # if not self.mode == "ff":
                self._save_excel(path=self.excel_fn)
        self._save_excel(path=self.excel_fn)

    def create_objects(self) -> None:
        """
        Loop thru excel objId column. Act for rows where candidates = "x" or "X".
        For those, create a new object record in RIA using template record mentioned in
        the configuration (templateID).

        Write the objId(s) of the newly created records in candidate column.
        """

        def _create_object(*, identNrs: str, template) -> str:
            identL = identNrs.split(";")
            objIds = set()  # unique list of objIds from Excel
            for ident in identL:
                identNr = ident.strip()
                # print(f"***trying to create new object '{identNr}' from template")
                new_id = self.client.create_from_template(
                    template=template, identNr=identNr
                )
                # logging.info(f"new record created: object {new_id} with {identNr} from template")
                objIds.add(new_id)
            objIds_str = "; ".join(str(objId) for objId in objIds)
            return objIds_str

        ws2 = self.wb["Conf"]
        try:
            temp_str = ws2["B1"].value  # was "Object 12345". Keep that?
        except:
            raise ConfigError("Config value 'template' not defined!")

        ttype, tid = temp_str.split()
        ttype = ttype.strip()  # do i need to strip?
        tid = int(tid.strip())
        print(f"***template: {ttype} {tid}")

        self._raise_if_excel_has_no_content()
        # we want the same template for all records

        templateM = self.client.get_template(ID=tid, mtype=ttype)
        # print ("Got template")
        # templateM.toFile(path="debug.template.xml")

        for c, rno in self._loop_table2(sheet=self.ws):
            print(f"{rno} of {self.ws.max_row}")  # , end="\r" flush=True
            if c["identNr"].value is None:
                # without a identNr we cant fill in a identNr in template
                # should not happen, that identNr is empty and cadinate = x
                # maybe log this case?
                return
            if c["candidate"].value is not None:
                cand_str = c["candidate"].value.strip().lower()
                if cand_str == "x":
                    objIds_str = _create_object(
                        identNrs=c["identNr"].value, template=templateM
                    )
                    c["objIds"].value = objIds_str
                    c["candidate"].value = None
                    if rno is not None and rno % 5 == 0:
                        # save almost immediately since likely to die
                        self._save_excel(path=self.excel_fn)
        self._save_excel(path=self.excel_fn)

    def init(self) -> None:
        if self.excel_fn.exists():
            raise Exception(f"* {self.excel_fn} exists already")

        # die if not writable so that user can close it before waste of time
        self._save_excel(path=self.excel_fn)

    def mv_dupes(self) -> None:
        def mk_dupes_dir():
            dupes_dir = Path(self.conf["mv_dupes"])
            if not dupes_dir.exists():
                print("Making dupes dir {dupes_dir}")
                dupes_dir.mkdir()

        if "mv_dupes" not in self.conf:
            raise ConfigError("config value 'mv_dupes' missing")

        self._raise_if_excel_has_no_content()
        mk_dupes_dir()
        for row, c in self._loop_table():  # start at 3rd row
            src_cell = row[6]
            filename_cell = row[0]
            dest_dir = Path(self.conf["mv_dupes"])
            dest_fn = dest_dir / filename_cell.value
            print(f"***{src_cell}")
            if dest_fn.exists():
                print(f"WARN: Dupe exists already {dest_fn}, no overwrite")
            else:
                print(f"* Moving Dupe to {dest_fn}")
                shutil.move(src_cell.value, dest_dir)

    def scan_disk(self) -> None:
        """
        Recursively scan a dir (src_dir). List the files in an Excel file trying
        to extract the proper identNr.

        Filenames with suspicious characters (e.g. '-' or ';') are flagged by coloring
        them red.
        """

        def _per_row(*, c: int, path: Path, known_idents: set) -> None:
            """
            c: row count
            specific to this scandisk task of prepare command

            writes to self.ws
            """
            identNr = extractIdentNr(path=path)
            identNrF = IdentNrFactory()
            print(f"   {path.name} -> {identNr}")
            self.ws[f"A{c}"] = path.name
            self.ws[f"B{c}"] = str(identNr)
            self.ws[f"H{c}"] = str(path.absolute())
            if identNr is not None:
                schema = identNrF._extract_schema(text=identNr)
            else:
                schema = "None"
            self.ws[f"I{c}"] = schema

            try:
                schemaId = self.schemas[schema]["schemaId"]
                self.ws[f"J{c}"] = schemaId
            except:
                self.ws[f"J{c}"] = "None"
                self.ws[f"J{c}"].font = red

            if self._suspicious_characters(identNr=identNr):
                for x in "ABCDEF":
                    self.ws[f"{x}{c}"].font = red
                print(
                    f"WARNING: identNr is suspicious - file correctly named? {identNr}"
                )
            # If the original files are misnamed, perhaps best to correct them instead of
            # adapting the parser to errors.

            if identNr in known_idents:
                self.ws[f"B{c}"].font = red
                self.ws[f"K{c}"] = "Duplikat"
                # print(f"Duplikat {identNr}")
            known_idents.add(identNr)

        self._check_scandir()
        src_dir = Path()  # Path(self.conf["src_dir"])
        print(f"* Scanning source dir: {src_dir}")

        c = 3  # start writing in 3rd line
        # todo: would be nice if we could stop after limit
        print(f"FILEMASK {self.filemask}, starting scan...")
        file_list = sorted(src_dir.glob(self.filemask))
        print(f"len(file_list) files found")
        known_idents: set[str] = set()  # mark duplicates
        ignore_names = (
            "thumbs.db",
            "desktop.ini",
            "prepare.ini",
            "prepare.log",
            "prepare.xlsx",
        )

        for path in file_list:
            if path.is_dir():
                continue
            if path.name.startswith("."):
                continue
            if path.name.lower().strip() in ignore_names:
                continue
            if self.limit == c:
                print("* Limit reached")
                break
            _per_row(c=c, path=path, known_idents=known_idents)
            print(f"sd {c} of {len(file_list)}")  # DDD{filemask2}
            if c % 500 == 0:
                self._save_excel(path=self.excel_fn)
            c += 1
        self._save_excel(path=self.excel_fn)

    #
    # PRIVATE
    #

    def _asset_exists_already(self, c) -> None:
        """
        Mainly fills in the "already uploaded?" cell in Excel (column C).

        Checks if an asset with that filename exists already in RIA. If so, it lists the
        corresponding mulId(s); if not None

        If config value mv_dupes exists, move asset files to the directory from the
        mv_dupes config value.

        Creates the dupes dir if it doesn't exist.

        New:
        - The check is now specific to an OrgUnit which is the internal name of a Bereich
        (e.g. EMSudseeAustralien).
        - The search is not exact. RIA ignores Sonderzeichen like _; i.e. if we search
          for an asset with  name x_x.jog and we learn that this one exists already
          according to this method then we dont know if the filename is really x_x.jpg
          or any number of variants such as x__x.jpg.

        If the Excel cell is empty, we still need to run the test. If it has one, multiple
        mulIds or "None" we don't need to run it again.
        """
        ws2 = self.wb["Conf"]
        orgUnit = self._get_orgUnit(cell="B2")  # can return None
        if c["assetUploaded"].value == None:
            idL = self.client.fn_to_mulId(fn=c["filename"].value, orgUnit=orgUnit)
            if len(idL) == 0:
                c["assetUploaded"].value = "None"
            else:
                c["assetUploaded"].value = "; ".join(idL)

    def _checkria_messages(self, c, rno):
        print(
            f"cr {c['filename'].value} -> {c['identNr'].value} {c['candidate'].value}"
        )
        print(f"{rno} of {self.ws.max_row}", end="\r", flush=True)

    def _check_scandir(self):
        # let's not overwrite or modify file information in Excel if already written
        # 2 lines are getting written by initialization
        # if self.ws.max_row > 2:
        #    raise Exception("Error: Scan dir info already filled in")

        identNrF = IdentNrFactory()
        self.schemas = identNrF.get_schemas()
        # if writable it's not open
        self._save_excel(path=self.excel_fn)

        conf_ws = self.wb["Conf"]
        try:
            self.filemask = conf_ws["B3"].value
        except Exception as e:
            raise ValueError(f"Error: Filemask missing {e}")

    def _fill_in_candidate(self, c) -> None:
        if c["schemaId"].value is None:
            c["candidate"].font = red
        if c["candidate"].value is None:
            if (
                c["assetUploaded"].value == "None"
                and c["objIds"].value == "None"
                and c["partsObjIds"].value == "None"
                and c["duplicate"].value != "Duplikat"
            ):
                c["candidate"].value = "x"

    def _get_objIds(self, *, identNr: str, strict: bool) -> str:
        orgUnit = self._get_orgUnit(cell="B2")  # can return None
        for single in identNr.split(";"):
            ident = single.strip()
            objIdL = self.client.identNr_exists(
                nr=ident, orgUnit=orgUnit, strict=strict
            )
            if not objIdL:
                return "None"
            return self._rm_garbage("; ".join(str(objId) for objId in objIdL))
        return "None"

    def _get_objIds2(self, *, identNr: str, strict: bool) -> str:
        """
        Superloaded version of get_objIds that only lets real parts through. Not very
        fast, but since RIA cant search for Sonderzeichen there is no way around it.

        We could move the logic that identifies parts to the RIA module though. But
        we have to move the garbage eliminator as well. Not today.
        """
        orgUnit = self._get_orgUnit(cell="B2")  # can return None
        for single in identNr.split(";"):
            identNr = single.strip()
            resL = self.client.identNr_exists2(
                nr=identNr, orgUnit=orgUnit, strict=strict
            )
            if not resL:
                return "None"
            real_parts = []
            for result in resL:
                objId = result[0]
                identNr_part = self._rm_garbage(result[1])
                if f"{identNr} " in identNr_part:
                    real_parts.append(f"{objId} [{identNr_part}]")
            # if we tested some results, but didnt find any real parts
            # we dont want to test them again
            if not real_parts:
                return "None"
            return "; ".join(real_parts)
        return "None"

    def _init_sheet(self, workbook: Workbook) -> openpyxl.worksheet.worksheet.Worksheet:
        """
        Returns the worksheet, makes a new document if necessary. Needs to be specific to app.
        """
        sheet_title = "prepareUpload"
        try:
            ws = workbook[sheet_title]
        except:  # new sheet
            ws = self.wb.active
        else:
            return ws  # sheet exists already

        # this is a new sheet
        ws.title = sheet_title
        self._write_table_description(description=self.table_desc, sheet=ws)

        try:
            ws_conf = workbook["Conf"]
        except:  # new sheet
            ws_conf = self.wb.create_sheet("Conf")
            ws_conf["A1"] = "template ID"
            ws_conf["C1"] = "Format: Object 1234567"

            ws_conf["A2"] = "orgUnit"
            ws_conf[
                "C2"
            ] = """Um die ID Suche auf eine orgUnit (Bereich) einzuschränken. Optional. z.B. EMSudseeAustralien"""

            ws_conf["A3"] = "Filemask"
            ws_conf[
                "C3"
            ] = """Um scandir Prozess auf eine Muster zu reduzieren, z.B. '**/*' oder '**/*.jpg'."""
            ws_conf.column_dimensions["B"].width = 20

        for row in ws_conf.iter_rows(min_col=1, max_col=1):
            for cell in row:
                cell.font = Font(bold=True)

        return ws

    def _objId_for_ident(self, c) -> None:
        """
        Writes in two cells: objIds and candidate

        Lookup objIds for IdentNr. Write the objId(s) to Excel. If none is found, write
        the string "None".

        Also writes x in candidate cell if uploaded and objId cell both have "None";
        write y if schemaId is missing.
        """

        # in rare cases identNr_cell might be None, then we cant look up anything
        if c["identNr"].value is None:
            return

        if c["objIds"].value == None:
            c["objIds"].value = self._get_objIds(
                identNr=c["identNr"].value, strict=True
            )

        # used to check if c["objIds"].value == "None"
        if c["partsObjIds"].value is None:
            # print ("Looking for parts")
            objIdL = self._get_objIds_for_whole_or_parts(identNr=c["identNr"].value)
            if objIdL:
                c["partsObjIds"].value = "; ".join(objIdL)
            else:
                c["partsObjIds"].value = "None"
            c["partsObjIds"].alignment = Alignment(wrap_text=True)

    def _raise_if_excel_has_no_content(self) -> bool:
        # assuming that after scandisk excel has to have more than 2 lines
        if self.ws.max_row < 3:
            raise NoContentError(
                f"ERROR: no data found; excel contains {self.ws.max_row} rows!"
            )
        return True
        # else:
        #    print(f"* Excel has data: {self.ws.max_row} rows")

    def _suspicious_characters(self, *, identNr: str | None) -> bool:
        # print (f"***suspicious? {identNr}")

        msg = "suspicious_characters:"

        if identNr is None:
            # print ("return bc None")
            return True
        elif "  " in identNr:
            logging.info(f"{msg} double space {identNr}")
            return True
        elif "." in identNr:
            # TODO seems that identNr with . are not mrked
            logging.info(f"{msg} unwanted symbol {identNr}")
            return True
        elif " " not in identNr:
            logging.info(f"{msg} missing space {identNr}")
            return True
        elif "-a" in identNr:
            logging.info(f"{msg} combination -a {identNr}")
            return True
        elif identNr.count(",") > 1:
            logging.info(f"{msg} number of commas {identNr}")
            return True

        # print (" -> not suspicious")
        return False


if __name__ == "__main__":
    pass
