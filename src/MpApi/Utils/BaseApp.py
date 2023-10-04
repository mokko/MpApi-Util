"""
Let's make a base class that is inherited from by every MpApi.Utils app, so we share some 
behavior.

We assume that those apps typically load config data, write data to Excel sheets.

from pathlib import path
class your_class(App):

    self._init_log() # writes to cwd/{scriptname}.log

    self.excel_fn = Path("path/to.xlsx")
    self.wb = self.init_excel(path=self.excel_fn)

    # relies on self.user, self.baseURL and self.pw being set
    self.client = self._init_client() 

So far this is near pointless, but perhaps I can still find a way to re-use significant 
parts of this class.

Let's avoid print messages from here! Not really, let's write the usual print messages

Let's typically log errors?
"""

import logging
from MpApi.Utils.Ria import RIA
from pathlib import Path
from openpyxl import Workbook, load_workbook, worksheet
from openpyxl.styles import Alignment, Font
import re
import sys
from tqdm import tqdm
from typing import Iterator, Optional, Union

# from typing import Any
class ConfigError(Exception):
    pass


class NoContentError(Exception):
    pass


class BaseApp:
    def _init_client(self) -> RIA:
        # avoid reinitializing although not sure that makes a difference
        if hasattr(self, "client"):
            return self.client
        else:
            return RiaUtil(baseURL=self.baseURL, user=self.user, pw=self.pw)

    def _drop_rows_if_file_gone(self, *, col: str = "A", cont: bool = False) -> None:
        """
        Loop thru Excel sheet "Assets" and check if the files still exist. We use
        relative filename for that, so update has to be executed in right dir.
        If the file no longer exists on disk (e.g. because it has been renamed),
        we delete it from the excel sheet by deleting the row.

        This is for the scandir step. NOT USED AT THE MOMENT.
        """
        if cont:
            print("   continous mode, not looking for changes on disk")
            return

        print("Checking for file changes")
        c = 3
        with tqdm(total=self.ws.max_row - c) as pbar:
            for row in self.ws.iter_rows(min_row=c):  # start at 3rd row
                filename = self.ws[f"{col}{c}"].value
                pbar.update()
                if filename is not None:
                    if not Path(filename).exists():
                        print(f"Deleting Excel row {c} file gone '{filename}'")
                        self.ws.delete_rows(c)
                c += 1
        print("   done")

    def _get_objIds_for_whole_or_parts(self, *, identNr: str) -> set[int]:
        """
        Receive the actual identNr. If it is (a) whole-part number, look for wholes;
        (b) if it a whole number look for parts and return the respective results as list
        of objIds.

        VII a 123 a-c: whole-part form
        VII a 123 whole form

        Return the objIds as list, not a semicolon-separated string list.
        """
        if self._has_parts(identNr):
            # look for whole equivalent
            self._get_objIds_for_whole(identNr=identNr)
        else:  # look for parts
            self._get_objIds_for_part(identNr=identNr)

    def _get_objIds_for_part(self, *, identNr: str) -> set[int]:
        # the return value is messy here
        return self.client.get_objIds2(
            # no orgUnit. Should that remain that way?
            identNr=identNr,
            strict=False,
        )

    def _get_objIds_for_whole(self, *, identNr: str) -> set[int]:
        """
        Provided an identNr with parts, return objIds for the whole.

        What happens if a whole is provided? Then it checks for a two part
        signature which makes little sense.
        """
        if not self._has_parts(identNr=identNr):
            print("WARNING: _get_objIds_for_whole already received a whole")
            return {}  # empty set

        # chop_off_last_part assuming there is part information
        ident_whole = " ".join(identNr.split()[:-1])
        # print(f"WHOLE: {ident_whole}")
        objId_set = self.client.identNr_exists3(
            # no orgUnit. Should it remain that way?
            ident=ident_whole,
        )
        return objId_set

    def _init_excel(self, *, path: Path) -> Workbook:
        """
        Given a file path for an excel file, return the respective workbook
        or make a new one if the file doesn't exist.
        """
        # let's avoid side effects, although we're not doing this everywhere
        if path.exists():
            # print (f"* Loading existing excel: '{data_fn}'")
            return load_workbook(path, data_only=True)
        else:
            # print (f"* Starting new excel: '{data_fn}'")
            return Workbook()

    def _init_log(self) -> Path:
        fn: str = Path(sys.argv[0]).stem + ".log"
        print(f"* Using logfile '{fn}'")
        logging.basicConfig(
            datefmt="%Y%m%d %I:%M:%S %p",
            filename=fn,
            filemode="w",  # a =append?
            level=logging.INFO,
            format="%(asctime)s: %(message)s",
        )
        return Path(fn)

    def _loop_table(self) -> Union[Iterator, int]:
        """
        Loop thru the data part of the Excel table. Return row and number of row.

        row = {
            "filename": row[0],

        }
        """
        c = 3  # counter; used report different number
        for row in self.ws.iter_rows(min_row=3):  # start at 3rd row
            yield row, c
            if self.limit == c:
                print("* Limit reached")
                break
            c += 1

    def _loop_table2(self, *, sheet: worksheet, offset: int = 3) -> Iterator:
        """
        Loop thru the data part of the Excel table. For convenience, return cells in dict by column
        names. For this to work, we require a description of the table in the following form:

        self.table_desc = {
            "filename": {
                "label": "Asset Dateiname",
                "desc": "aus Verzeichnis",
                "col": "A",
                "width": 20,
            },
        }

        for c,rno in _loop_table2():
            print (f"row number {rno} {c['filename']}")
        """
        rno = offset  # row number; used to report a different number
        for row in sheet.iter_rows(min_row=offset):  # start at 3rd row
            cells = self._rno2dict(rno)
            yield cells, rno
            if self.limit == rno:
                print("* Limit reached")
                break
            rno += 1

    def _path_in_list(self, path: Path | str, cno: int) -> Optional[int]:
        """
        Returns row number as int if filename is already in list, else None.

        We were using the first column, no column no (cno).

        Currently, we're using the filename from column A which SHOULD be unique
        in the MuseumPlus context, but which is strange requirement in the world
        of directories, where multiple dirs may contain files with the same name.

        We could switch to full path here for the identity test, if we wanted to.

        What happens if filenames are not unique? Files on disk will not be
        uploaded listed in scandir and hence not uploaded and hence not moved.
        """
        rno = 3
        for row in self.ws.iter_rows(min_row=3):  # start at 3rd row
            fn = row[cno].value
            # print (f"_path_in_list: {fn=}{name=}")
            if fn == str(path):
                return rno
            rno += 1
        return None

    def _plus_one(self, p: Path) -> Path:
        """
        Receive a path and add or increase the number at the end to make filename unique

        We're adding "_1" before the suffix.
        """
        suffix = p.suffix  # returns str
        stem = p.stem  # returns str
        parent = p.parent  # returns Path
        m = re.search(r"_(\d+)$", stem)
        if m:
            digits = int(m.group(1))
            stem_no_digits = stem.replace(f"_{digits}", "")
            digits += 1
            new = parent / f"{stem_no_digits}_{digits}{suffix}"
        else:
            digits = 1
            new = parent / f"{stem}_{digits}{suffix}"
        return new

    def _rno2dict(self, rno: int) -> dict:
        """
        We read the provide a dict with labels as keys based on table description
        (self.table_desc).
        """
        cells = dict()
        for label in self.table_desc:
            col = self.table_desc[label]["col"]
            cells[label] = self.ws[f"{col}{rno}"]
        return cells

    # needs to go to Ria.py?
    def _rm_garbage(self, text: str) -> str:
        """
        rm the garbage from Zetcom's dreaded html bug
        """

        if "<html>" in text:
            text = text.replace("<html>", "").replace("</html>", "")
            text = text.replace("<body>", "").replace("</body>", "")
        return text

    def _save_excel(self, path: Path) -> None:
        """Made this only to have same print msgs all the time"""

        print(f"   saving Excel {path}")
        try:
            self.wb.save(filename=path)
        except KeyboardInterrupt:
            print("Catching keyboard interrupt during Excel operation; try again...")

    def _get_orgUnit(self, *, cell: str) -> Optional[str]:
        """
        Stores the value specified in the paramter cell in self.orgUnit.
        cell is a string like B2.

        Some empty values are turned into None
        """
        conf_ws = self.wb["Conf"]
        orgUnit = conf_ws[cell].value  # can be None
        if orgUnit is None:
            pass
        elif orgUnit.strip() == "":
            orgUnit = None
        return orgUnit

    def _suspicous_character(self, *, identNr: str):
        if identNr is None or any("-", ";") in str(identNr):
            return True

    def _wipe(self) -> None:
        rno = 3
        with tqdm(total=self.ws.max_row - 2) as pbar:
            while rno <= self.ws.max_row:
                # print(f"wiping row {rno}")
                pbar.update()
                self.ws.delete_rows(rno)
                # rno += 1
        self._save_excel(path=excel_fn)

    def _write_table_description(self, *, description: dict, sheet: worksheet):
        """
        Take the table description and write it to the top of the specified worksheet.

        Expect a table description at self.table_desc and use that to write the first
        two lines to an empty Excel sheet.

        The table description is a dictionary structured as follows
        self.table_desc = {
            "filename": {
                "label": "Asset Dateiname",
                "desc": "aus Verzeichnis",
                "col": "A",
                "width": 20,
            },
        }

        """

        for itemId in description:
            col = description[itemId]["col"]  # letter
            sheet[f"{col}1"] = description[itemId]["label"]
            sheet[f"{col}1"].font = Font(bold=True)
            # print (f"{col} {self.table_desc[itemId]['label']}")
            if "desc" in description[itemId]:
                desc_txt = description[itemId]["desc"]
                sheet[f"{col}2"] = desc_txt
                sheet[f"{col}2"].font = Font(size=9, italic=True)
                # print (f"\t{desc_txt}")
            if "width" in description[itemId]:
                width = description[itemId]["width"]
                # print (f"\t{width}")
                sheet.column_dimensions[col].width = width
