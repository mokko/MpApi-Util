"""
Prepare assets for upload with regular Bildimport

With this tool we 
- recursively scan a directory
- filter for specific files (e.g. with "-KK" or only *.jpg)
- extract the identNr from filename
- check if asset has already been uploaded (sort of a Dublette)
- lookup objId by identNr
- mark cases where extracted identNr are suspicious
- figure out cases where object record doesn't exit yet
- write results into spreadsheet
- for those cases create object records by copying a template record
- write the new identNr in the new record

This tool is meant to be used by an editor. The editor runs the script multiple times
in different phases. For each phase, the edior checks the results in the Excel file
and, if necessary, corrects something. There are three phases
(1) scandisk
(2) checkria and
(3) createobjects

   $ prepare -p scandisk -c prepare.ini 
   $ prepare -p checkria -c prepare.ini 
   $ prepare -p createobjects -c prepare.ini 

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
"""


import configparser
import logging
from lxml import etree
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from pathlib import Path
import re
from typing import Any, Optional

# from MpApi.Util.prepare.scandisk import Scandisk
# from MpApi.Util.prepare.aea import Aea
# from mpapi.sar import Sar
from MpApi.Utils.BaseApp import BaseApp
from MpApi.Utils.Ria import RiaUtil
from MpApi.Utils.identNr import IdentNrFactory

# worksheet: openpyxl.worksheet

# NSMAP = {
#    "m": "http://www.zetcom.com/ria/ws/module",
#    "o": "http://www.zetcom.com/ria/ws/module/orgunit",
# }

red = Font(color="FF0000")


class PrepareUpload(BaseApp):
    def __init__(
        self,
        *,
        baseURL: str,
        conf_fn: str,
        job: str,
        user: str,
        pw: str,
        limit: int = -1,
    ) -> None:
        self.baseURL = baseURL
        self.conf_fn = Path(conf_fn)
        self.job = job  # let's not load RiaUtil here, bc we dont need it for
        self.limit = int(limit)
        self.user = user  # scandisk phase
        self.pw = pw

        self._init_log()
        self.conf = self._init_conf(path=self.conf_fn, job=job)
        self.excel_fn = Path(self.conf["excel_fn"])
        if self.excel_fn.exists():
            print(f"* {self.excel_fn} exists already")
        else:
            print(f"* About to make new Excel '{self.excel_fn}'")
        self.wb = self._init_excel(path=self.excel_fn)
        self.ws = self._init_sheet(workbook=self.wb)  # explicit is better than implicit
        self._conf_to_excel(
            conf=self.conf, wb=self.wb
        )  # overwrites existing conf values

        # die if not writable so that user can close it before waste of time
        self._save_excel(path=self.excel_fn)

    def _init_sheet(self, workbook: Workbook) -> Any:  # openpyxl.worksheet
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
        ws["A1"] = "Dateiname"
        ws["A2"] = "aus Verzeichnis"
        ws["B1"] = "Signatur"
        ws["B2"] = "aus Dateiname"
        ws["C1"] = "schon hochgeladen?"
        ws["C2"] = "mulId(s) aus RIA"
        ws["D1"] = "objId(s) aus RIA"
        ws["D2"] = "für diese Signatur"
        ws["E1"] = "Kandidat"
        ws["E2"] = "neue Objekte erzeugen?"
        ws["F1"] = "Bemerkung"
        ws["G1"] = "Pfad"
        ws["G2"] = "aus Verzeichnis"
        ws["H1"] = "Inv.Nr.Schema"
        ws["H2"] = "aus IdentNr"
        ws["I1"] = "SchemaID"
        ws["I2"] = "aus Schema"

        ws.column_dimensions["A"].width = 25
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 10
        ws.column_dimensions["D"].width = 20
        ws.column_dimensions["F"].width = 30
        ws.column_dimensions["G"].width = 100
        return ws

    def _raise_if_excel_has_no_content(self):
        # assuming that after scandisk excel has to have more than 2 lines
        if self.ws.max_row < 3:
            raise ValueError(
                f"ERROR: no data found; excel contains {self.ws.max_row} rows!"
            )
        return True
        # else:
        #    print(f"* Excel has data: {self.ws.max_row} rows")

    # I lost an old version of this method. Where did it go?
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

    #
    # public
    #

    def asset_exists_already(self):
        """
        Fills in the "already uploaded?" cell in Excel (column C).

        Checks if an asset with that filename exists already in RIA. If so, it lists the
        corresponding mulId(s); if not None

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

        def _per_row(*, row, changed) -> bool:
            filename_cell = row[0]  # 0-index
            uploaded_cell = row[2]
            print(f"* mulId for filename {c} of {self.ws.max_row-2}")
            if uploaded_cell.value == None:
                # Let's not make org_unit optional!
                # print (f"xxxxxxxxxxxxxxxxxx {self.conf['org_unit']}")
                idL = self.client.fn_to_mulId(
                    fn=filename_cell.value, orgUnit=self.conf["org_unit"]
                )
                if len(idL) == 0:
                    uploaded_cell.value = "None"
                else:
                    uploaded_cell.value = "; ".join(idL)
                changed = True
            return changed

        self._raise_if_excel_has_no_content()
        self.client = self._init_client()

        c = 1  # counter; start counting at row 3, so counts the entries more than the rows
        changed = False
        for row in self.ws.iter_rows(min_row=3):  # start at 3rd row
            changed = _per_row(row=row, changed=changed)
            # print(f"***{uploaded_cell.value}")
            if self.limit == c:
                print("* Limit reached")
                break
            c += 1
        if changed is True:
            self._save_excel(path=self.excel_fn)

    def create_objects(self):
        """
        Loop thru excel objId column. Act for rows where candidates = "x" or "X".
        For those, create a new object record in RIA using template record mentioned in
        the configuration (templateID).

        Write the objId(s) of the newly created records in candidate column.
        """

        def _per_row(*, row, template) -> None:
            ident_cell = row[1]  # in Excel from filename; can have multiple
            if ident_cell.value is None:
                # without a identNr we cant fill in a identNr in template
                # should not happen, that identNr is empty and cadinate = x
                # maybe log this case?
                return
            identL = ident_cell.value.split(";")
            candidate_cell = row[4]  # to write into
            if candidate_cell.value is not None:
                cand_str = candidate_cell.value.strip()
                if cand_str.lower() == "x":
                    objIds = set()
                    for ident in identL:
                        identNr = ident.strip()
                        new_id = self.client.create_from_template(
                            template=template, identNr=identNr
                        )
                        # logging.info(f"new record created: object {new_id} with {identNr} from template")
                        objIds.add(new_id)
                    candidate_cell.value = "; ".join(str(objId) for objId in objIds)
                    # save immediately since likely to die
                    self._save_excel(path=self.excel_fn)

        try:
            self.conf["template"]
        except:
            raise SyntaxError("Config value 'template' not defined!")

        ttype, tid = self.conf["template"].split()  # do i need to strip?
        ttype = ttype.strip()
        tid = tid.strip()
        print(f"***template: {ttype} {tid}")

        self._raise_if_excel_has_no_content()
        self.client = self._init_client()
        # we want the same template for all records
        templateM = self.client.get_template(ID=tid, mtype=ttype)
        # templateM.toFile(path="debug.template.xml")

        c = 1  # counter; start counting at row 3, so counts the entries more than the rows
        for row in self.ws.iter_rows(min_row=3):  # start at 3rd row
            _per_row(row=row, template=templateM)
            if self.limit == c:
                print("* Limit reached")
                break
            c += 1

    def objId_for_ident(self):
        """
        Lookup objIds for IdentNr. Write the objId(s) to Excel. If none is found,
        write the string "None".

        Write x in candidate cell if uploaded and objId cell both have None; write
        y if schemaId is missing.


        """
        # currently this is unnecessary, but why rely on that?
        self._raise_if_excel_has_no_content()
        self.client = self._init_client()

        # c has not been passed here, but still works
        # that's cool scope, just slightly magic?
        def _per_row(*, row, changed):
            print(f"* objId for identNr {c} of {self.ws.max_row-2}")
            ident_cell = row[1]  # in Excel from filename; can have multiple
            uploaded_cell = row[2]  # can have multiple
            objId_cell = row[3]  # to write into
            candidate_cell = row[4]  # to write into
            schema_id_cell = row[8]  # to color candidate

            # in rare cases identNr_cell might be None
            # then we cant look up anything
            if ident_cell.value is None:
                return changed

            if objId_cell.value == None:
                changed = True
                for single in ident_cell.value.split(";"):
                    ident = single.strip()
                    objIdL = self.client.identNr_exists(nr=ident)
                    if len(objIdL) == 0:
                        objId_cell.value = "None"
                    else:
                        objId_cell.value = "; ".join(str(objId) for objId in objIdL)
                # print(f"***{ident_cell.value} -> {objId_cell.value}")
            if (
                uploaded_cell.value == "None"
                and objId_cell.value == "None"
                and candidate_cell.value is None
            ):
                changed = True
                if schema_id_cell.value is None:
                    candidate_cell.value = "y"
                    candidate_cell.font = red
                else:
                    candidate_cell.value = "x"
            return changed

        c = 1  # case counter
        changed = False
        for row in self.ws.iter_rows(min_row=2):  # start at 2nd row
            changed = _per_row(row=row, changed=changed)
            if self.limit == c:
                print("* Limit reached")
                break
            c += 1
        if changed is True:  # let's only save if we changed something
            self._save_excel(path=self.excel_fn)

    def scan_disk(self):
        """
        Recursively scan a dir (src_dir) for *-KK*. List a files in an Excel file trying
        to extract the proper identNr.

        Filenames with suspicious characters (e.g. '-' or ';') are flagged by coloring
        them red.
        """

        def _extractIdentNr(*, path: Path) -> Optional[str]:
            """
            extracts IdentNr (=identifier, Signatur) from filename specifically for KK.

            TODO
            We will need other identNr parsers in the future so we have to find load
            plugins from conf.
            """
            # stem = str(path).split(".")[0]  # stem is everything before first .
            stem = path.stem
            m = re.search(r"([\w\d +.,-]+)-KK", stem)
            if m:
                return m.group(1).strip()

        def _per_row(*, c: int, path: Path) -> None:
            """
            c: row count
            specific to this scandisk task of prepare command

            writes to self.ws
            """
            identNr = _extractIdentNr(path=path)
            print(f"{identNr} : {path.name}")
            self.ws[f"A{c}"] = path.name
            self.ws[f"B{c}"] = identNr
            self.ws[f"G{c}"] = str(path)
            if identNr is not None:
                schema = IdentNrFactory._extractSchema("self", text=identNr)
            else:
                schema = "None"
            self.ws[f"H{c}"] = schema

            try:
                schemaId = self.schemas[schema]["schemaId"]
                self.ws[f"I{c}"] = schemaId
            except:
                self.ws[f"I{c}"] = "None"
                self.ws[f"I{c}"].font = red

            if self._suspicious_characters(identNr=identNr):
                self.ws[f"A{c}"].font = red
                self.ws[f"B{c}"].font = red
                self.ws[f"E{c}"].font = red
                print(
                    f"WARNING: identNr is suspicious - file correctly named? {identNr}"
                )
            # If the original files are misnamed, perhaps best to correct them instead of
            # adapting the parser to errors.

        # let's not overwrite or modify file information in Excel if already written
        # 2 lines are getting written by initialization
        if self.ws.max_row > 2:
            raise Exception("Error: Scan dir info already filled in")

        src_dir = Path(self.conf["src_dir"])
        print(f"* Scanning source dir: {src_dir}")

        f = IdentNrFactory()
        self.schemas = f.get_schemas()

        # todo: i am filtering files which have *-KK*;
        # maybe I should allow all files???
        c = 3  # start writing in 3rd line
        for path in src_dir.rglob("*-KK*"):
            # print(path)
            _per_row(c=c, path=path)
            if self.limit == c:
                print("* Limit reached")
                break
            c += 1
        self._save_excel(path=self.excel_fn)


if __name__ == "__main__":
    pass
