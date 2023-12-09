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

from MpApi.Utils.Ria import RIA
from MpApi.Utils.logic import has_parts
from MpApi.Utils.Xls import Xls, ConfigError, NoContentError
from pathlib import Path
from openpyxl import Workbook, load_workbook, worksheet
from openpyxl.styles import Alignment, Font
import re
import sys
from tqdm import tqdm
from typing import Iterator, Optional, Union


class BaseApp:
    def _init_client(self) -> RIA:
        # avoid reinitializing although not sure that makes a difference
        if hasattr(self, "client"):
            return self.client
        else:
            return RiaUtil(baseURL=self.baseURL, user=self.user, pw=self.pw)

    def _get_objIds_for_whole_or_parts(self, *, identNr: str) -> set[int]:
        """
        Receive the actual identNr. If it is (a) whole-part number, look for wholes;
        (b) if it a whole number look for parts and return the respective results as list
        of objIds.

        VII a 123 a-c: whole-part form
        VII a 123 whole form

        Return the objIds as list, not a semicolon-separated string list.
        """
        if has_parts(identNr):
            self._get_objIds_for_whole(identNr=identNr)
        else:
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
        if not has_parts(identNr=identNr):
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

    # needs to go to Ria.py?
    def _rm_garbage(self, text: str) -> str:
        """
        rm the garbage from Zetcom's dreaded html bug
        """

        if "<html>" in text:
            text = text.replace("<html>", "").replace("</html>", "")
            text = text.replace("<body>", "").replace("</body>", "")
        return text

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
