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

This tool is meant to be used by an editor. The editor runs the script multiple times
in different phases. For each phase, the edior checks the results in the Excel file and, 
if necessary, corrects something. There are three phases
(1) scandir (formerly: scandisk)
(2) checkria and
(3) createobjects
(4) movedupes:

   $ prepare scandir -j JobName
   $ prepare checkria -j JobName 
   $ prepare createobjects -j JobName   
   $ prepare movedupes -j JobName   

Preparation
- write/edit/update configuration (e.g. prepare.ini)
- cd to your project_dir with credentials.py file

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

How should prepare.ini be structured?
excel_fn = Excel filename, e.g. test.xlsx

Update April 2023
- We make prepare work a lot more like the mover and upload, so 
  (1) no more separate config file, instead we use prepare.xlsx 
  (2) We now scan current working directory 
  (3) We get RIA credentials from $HOME\.RIA file  
  (4) command line changd to type upload scandir (without -p for phase)
  (5) hardcoded "prepare.xlsx" file name
  (6) scandisk renamed to scandir with alias init to be more similar to mover and upload
  (7) currently filemask is not configurable so always falls back to default
TODO
- I want to put the two checks from checkria into a single loop. Is this feasable?
- Do we make scandir re-runnable?
"""


import configparser  # todo replace with toml in future
import logging
from lxml import etree
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
import openpyxl.cell.cell
from pathlib import Path
import re
import shutil
from typing import Any, Optional

# from MpApi.Util.prepare.scandisk import Scandisk
# from MpApi.Util.prepare.aea import Aea
# from mpapi.sar import Sar
from mpapi.module import Module
from MpApi.Utils.BaseApp import BaseApp, NoContentError
from MpApi.Utils.Ria import RIA
from MpApi.Utils.identNr import IdentNrFactory
from MpApi.Utils.logic import extractIdentNr

# worksheet: openpyxl.worksheet


red = Font(color="FF0000")

from MpApi.Utils.BaseApp import ConfigError


class PrepareUpload(BaseApp):
    def __init__(
        self,
        *,
        limit: int = -1,
    ) -> None:

        creds = self._read_credentials()
        self.client = RIA(baseURL=creds["baseURL"], user=creds["user"], pw=creds["pw"])

        self.limit = int(limit)

        self._init_log()
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
                "label": "Teile objId?",
                "desc": "für diese IdentNr",
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
        # die if not writable so that user can close it before waste of time
        self._save_excel(path=self.excel_fn)

    #
    # public
    #

    def checkria(self) -> None:
        """
        Attempt to unify two steps into one loop
            p.asset_exists_already()
            p.objId_for_ident()
        """
        self._raise_if_excel_has_no_content()
        # ws2 = self.wb["Conf"]
        # orgUnit = self._get_orgUnit(cell="B2") # can return None
        for c, rno in self._loop_table2(sheet=self.ws):
            print(f"{rno} of {self.ws.max_row}")
            # , end="\r", flush=True
            self._asset_exists_already(c)
            self._objId_for_ident(c)
            self._fill_in_candidate(c)

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
                new_id = self.client.create_from_template(
                    template=template, identNr=identNr
                )
                # logging.info(f"new record created: object {new_id} with {identNr} from template")
                objIds.add(new_id)
            objIds_str = "; ".join(str(objId) for objId in objIds)
            return objIds_str

        try:
            self.conf["template"]
        except:
            raise ConfigError("Config value 'template' not defined!")

        ttype, tid = self.conf["template"].split()  # do i need to strip?
        ttype = ttype.strip()
        tid = tid.strip()
        print(f"***template: {ttype} {tid}")

        self._raise_if_excel_has_no_content()
        # self.client = self._init_client()
        # we want the same template for all records
        templateM = self.client.get_template(ID=tid, mtype=ttype)
        # templateM.toFile(path="debug.template.xml")

        for row, c in self._loop_table():
            ident_cell = row[1]  # in Excel from filename; can have multiple
            candidate_cell = row[5]  # to write into
            if ident_cell.value is None:
                # without a identNr we cant fill in a identNr in template
                # should not happen, that identNr is empty and cadinate = x
                # maybe log this case?
                return
            if candidate_cell.value is not None:
                cand_str = candidate_cell.value.strip()
                if cand_str.lower() == "x":
                    objIds_str = _create_object(
                        identNrs=ident_cell.value, template=templateM
                    )
                    candidate_cell.value = objIds_str
                    # save immediately since likely to die
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
        for row in self._loop_table():  # start at 3rd row
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
        Recursively scan a dir (src_dir) for *-KK*. List the files in an Excel file trying
        to extract the proper identNr.

        Filenames with suspicious characters (e.g. '-' or ';') are flagged by coloring
        them red.
        """

        def _per_row(*, c: int, path: Path) -> None:
            """
            c: row count
            specific to this scandisk task of prepare command

            writes to self.ws
            """
            if not path.is_dir():
                identNr = extractIdentNr(path=path)
                print(f"{identNr} : {path.name}")
                self.ws[f"A{c}"] = path.name
                self.ws[f"B{c}"] = identNr
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
                    print(f"Duplikat {identNr}")
                known_idents.add(identNr)

        # let's not overwrite or modify file information in Excel if already written
        # 2 lines are getting written by initialization
        if self.ws.max_row > 2:
            raise Exception("Error: Scan dir info already filled in")

        src_dir = Path()  # Path(self.conf["src_dir"])
        print(f"* Scanning source dir: {src_dir}")

        identNrF = IdentNrFactory()
        self.schemas = identNrF.get_schemas()

        try:
            filemask = self.conf["filemask"]
            filemask2 = f"*{self.conf['filemask']}*"
        except:
            filemask = ""  # -*
            filemask2 = "*"
        # todo: i am filtering files which have *-KK*;
        # maybe I should allow all files???
        c = 3  # start writing in 3rd line
        file_list = sorted(src_dir.rglob(filemask2))
        # print (f"{filemask2} {file_list}")
        known_idents = set()  # mark duplicates
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
            print(f"{c} of {len(file_list)}")  # DDD{filemask2}
            _per_row(c=c, path=path)
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
            # Let's not make org_unit optional!
            idL = self.client.fn_to_mulId(fn=c["filename"].value, orgUnit=orgUnit)
            if len(idL) == 0:
                c["assetUploaded"].value = "None"
            else:
                c["assetUploaded"].value = "; ".join(idL)

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
                print("setting candidate")
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

    def _init_sheet(self, workbook: Workbook) -> openpyxl.worksheet.worksheet.Worksheet:
        """
        Defines the Excel format of this app. Needs to be specific to app.
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
            ws_conf["C1"] = "object"
            ws_conf["A2"] = "orgUnit"
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
            c["partsObjIds"].value = self._get_objIds2(
                identNr=c["identNr"].value, strict=False
            )
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

    def _suspicious_characters(self, *, identNr: str) -> bool:
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
