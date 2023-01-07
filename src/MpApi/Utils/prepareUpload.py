"""
Prepare Assets for Upload with regular Bildimport

- recursively scan a directory
- filter for specific files (e.g. with "-KK" or only *.jpg)
- parse identNr
- check for Dublette (assets with the same image/asset file)
- loopup identNr in RIA
- write results into spreadsheet

When using this script, editor will need to check
(1) if identNr algorithm worked as desired
(2) Dubletten (asset already online). 
    TODO: Script could move files that already exist online to separate folder
(3) Cases where multiple objIds were identified
    The following steps only relate to cases where no objId was identified
    
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

#worksheet: openpyxl.worksheet

# NSMAP = {
#    "m": "http://www.zetcom.com/ria/ws/module",
#    "o": "http://www.zetcom.com/ria/ws/module/orgunit",
# }


class PrepareUpload(BaseApp):
    def __init__(
        self, *, baseURL: str, conf_fn: str, job: str, user: str, pw: str, limit:int = -1
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
        # should we prevent writing file if it hasn't changed? not for now
        self._save_excel(path=self.excel_fn) 

    def _check_2nd_phase(self):
        if self.ws.max_row < 3:  # we assume that scan_disk has run if more than 2 lines
            raise ValueError(
                f"ERROR: no data found; excel contains {self.ws.max_row} rows!"
            )
        else:
            print(f"* Excel has data: {self.ws.max_row} rows")
        self.client = self._init_client()

    def _init_sheet(self, workbook: Workbook) -> Any: # openpyxl.worksheet  
        """
        Defines the Excel format of this app. Needs to be specific to app.
        """
        sheet_title = "prepareUpload"
        try:
            #existing sheet
            ws = workbook[sheet_title]
        except: # new sheet
            ws = self.wb.active
        else: # if sheet already exists
            return ws
        # if this is a new sheet

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

        ws.column_dimensions["A"].width = 25
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 10
        ws.column_dimensions["D"].width = 20
        ws.column_dimensions["F"].width = 30
        ws.column_dimensions["G"].width = 100
        return ws

    #
    # public
    #

    def asset_exists_already(self):
        """
        Fills in the already uploaded? cell in Excel (column C).
        Checks if an asset with that filename exists already in RIA. If so, it lists the
        corresponding mulId(s); if not None

        New: The check is now specific to an OrgUnit which is the internal name of a Bereich
        (e.g. EMSudseeAustralien).

        If the cell is empty it still needs to be checked.

        """
        def _per_row(*, row, changed)->bool:
            filename_cell = row[0] # 0-index
            uploaded_cell = row[2]  
            print(f"* mulId for filename {c} of {self.ws.max_row-2}")
            if uploaded_cell.value == None:
                changed = True
                # Let's not make org_unit optional!
                idL = self.client.fn_to_mulId(
                    fn=filename_cell.value, orgUnit=self.conf["org_unit"]
                )
                if idL is None:
                    uploaded_cell.value = "None"
                else:
                    uploaded_cell.value = ", ".join(idL)
            return changed

        self._check_2nd_phase()
        c = 1  # counter; start counting at row 3, so counts the entries more than the rows
        changed = False
        for row in self.ws.iter_rows(min_row=3):  # start at 3rd row
            changed = _per_row(row=row, changed=changed)
            #print(f"***{uploaded_cell.value}")
            if self.limit == c:
                    print ("* Limit reached")
                    break
            c += 1
        if changed is True:
            self._save_excel(path=self.excel_fn)

    def objId_for_ident(self):
        """
        Lookup objIds for IdentNr. Write the objId(s) back to Excel. If none is found,
        leave field write string "None". Do that only for rows where there that have
        "schon hochgeladen?" = None.

        Take ident from Excel, get the objId from RIA and write it back to Excel.
        """
        # currently this unnecessary, but why rely on that?
        self._check_2nd_phase()

        def _per_row(*, row, changed):       
            print(f"* objId for identNr {c} of {self.ws.max_row-2}")
            ident_cell = row[1]  # in Excel from filename; can have multiple
            uploaded_cell = row[2]
            objId_cell = row[3]  # in Excel
            if objId_cell.value == None:
                changed = True
                for singleNr in ident_cell.value.split(", "):
                    objIdL = self.client.objId_for_ident(identNr=singleNr)  # from RIA
                    if objIdL is None:
                        objId_cell.value = "None"
                    else:
                        objId_cell.value = ", ".join(objIdL)
                #print(f"***{ident_cell.value} -> {objId_cell.value}")
            #else:
            #    print("   already filled in")
            if (
                uploaded_cell.value == "None"
                and objId_cell.value == "None"
                and row[4].value is None
            ):
                changed = True
                row[4].value = "x"
            return changed
            
        c = 1  # case counter
        changed = False
        for row in self.ws.iter_rows(min_row=2):  # start at 2nd row
            changed = _per_row(row=row, changed=changed)
            if self.limit == c:
                print ("* Limit reached")
                break
            c += 1
        if changed is True: # let's only save if we changed something
            self._save_excel(path=self.excel_fn)

    def scan_disk(self):
        def _per_row(*, c: int, path: Path) -> None:
            """
            c: row count
            specific to this scandisk task of prepare command

            writes to self.ws            
            """
            identNr = _extractIdentNr(path=path)
            self.ws[f"A{c}"] = path.name
            self.ws[f"B{c}"] = identNr
            self.ws[f"G{c}"] = str(path)

            red = Font(color="FF0000", size=12)

            if identNr is None:
                cell = self.ws[f"A{c}"]
                cell.font = red
                print (f"WARNING: Likely parsing error when looking for identNr: {identNr}")
                #raise SyntaxError
            

        def _extractIdentNr(*, path: Path) -> Optional[str]:
            """
            extracts IdentNr (=identifier, Signatur) from filename specifically for KK.

            TODO
            We will need other identNr parsers in the future so we have to find load
            plugins from conf.
            """
            # stem = path.stem # assuming there is only one suffix
            stem = str(path).split(".")[0]
            # print (stem)
            m = re.search(r"([\w ,\.\-]+)\w*-KK", stem)
            # print (m)
            if m:
                return m.group(1)

        # let's not overwrite or modify file information in Excel if already written
        # 2 lines are getting written by initialization
        if self.ws.max_row > 2:
            raise Exception("Error: Scan dir info already filled in")
        
        src_dir = Path(self.conf["src_dir"])
        print(f"* Scanning source dir: {src_dir}")

        c = 3  # start writing in 3rd line
        for path in src_dir.rglob("*-KK*"):
            print (path)
            _per_row(c=c, path=path)
            if self.limit == c:
                print ("* Limit reached")
                break
            c += 1
        self._save_excel(path=self.excel_fn)

    def create_object():
        """
        Loop thru excel objId column. Act for cases which have "None".
        For those, create a new object record in RIA using template record

        Where does the template info come from? Prehaps we make another
        column with the template id and fill that in. Do we typically have
        the same template for all of them?
        """
        self._save_excel(path=self.excel_fn)


if __name__ == "__main__":
    pass
