"""
Let's make a base class that is inherited from by every MpApi.Utils app, so we share some 
behavior.

We assume that those apps typically load config data, write data to Excel sheets.

from pathlib import path
class your_class(App):

    self._init_log() # writes to cwd/{scriptname}.log
    self.conf = self._init_conf(path=Path("path/to/conf.ini"), job="jobname")

    self.excel_fn = Path("path/to.xlsx")
    self.wb = self.init_excel(path=self.excel_fn)

    # relies on self.user, self.baseURL and self.pw being set
    self.client = self._init_client() 

So far this is near pointless, but perhaps I can still find a way to re-use significant 
parts of this class.

Let's avoid print messages from here! Not really, let's write the usual print messages

Let's typically log errors?
"""

import configparser
import logging
from MpApi.Utils.Ria import RIA
from pathlib import Path
from openpyxl import Workbook, load_workbook
import sys
import tomllib
from typing import Iterator, Union

# from typing import Any
class ConfigError(Exception):
    pass


class NoContentError(Exception):
    pass


class BaseApp:
    def _conf_to_excel(self, *, conf: dict, wb: Workbook) -> None:
        """
        Let's copy the config values to the Excel sheet titled "conf" to document
        the values that produced the results.

        Overwrites existing conf values

        Should we assume that conf comes from self.conf? No, let's be more explicit
        We assume that Excel is at self.wb
        """
        # dont create new if already exists
        if "conf" in wb.sheetnames:
            print("* Sheet 'conf' exists already")
            ws_conf = wb["conf"]
        else:
            print("* Making new conf sheet")
            ws_conf = wb.create_sheet("conf")
        c = 1
        for name in conf:
            ws_conf[f"A{c}"] = name
            ws_conf[f"B{c}"] = conf[name]
            c += 1
        # return ws_conf
        # just access wb["conf"] if you need access

    def _init_client(self) -> RIA:
        # avoid reinitializing although not sure that makes a significant difference
        if hasattr(self, "client"):
            return self.client
        else:
            return RiaUtil(baseURL=self.baseURL, user=self.user, pw=self.pw)

    # should we require conf_fn as a Path to be more consistent?
    def _init_conf(self, *, path: Path, job: str) -> dict:
        if not path.exists():
            raise ConfigError("ERROR: Config file not found!")
        config = configparser.ConfigParser()
        config.read(path, "UTF-8")
        print(f"* reading config file '{path}'")
        # logging.info(f"config file {path} successfully loaded")
        try:
            return config[job]
        except:
            raise ConfigError(f"Job '{job}'doesn't exist in config file!")

    def _init_excel(self, *, path: Path) -> Workbook:
        """
        Given a file path for an excel file, return the respective workbook
        or make a new one if the file doesn't exist.
        """
        # let's avoid side effects, although we're not doing this everywhere
        if path.exists():
            # print (f"* Loading existing excel: '{data_fn}'")
            return load_workbook(path)
            # self.wb = load_workbook(path)
        else:
            # print (f"* Starting new excel: '{data_fn}'")
            return Workbook()
            # self.wb = Workbook()

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

    def _loop_table2(self) -> dict:
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
        rno = 3  # row number; used to report a different number
        for row in self.ws.iter_rows(min_row=3):  # start at 3rd row
            cells = self._rno2dict(rno)
            yield cells, rno
            if self.limit == rno:
                print("* Limit reached")
                break
            rno += 1

    def _rno2dict(self, rno: int) -> dict:

        cells = dict()
        for label in self.table_desc:
            col = self.table_desc[label]["col"]
            cells[label] = self.ws[f"{col}{rno}"]
        return cells

    def _read_credentials(self) -> None:
        """
        New credentials systems where we read RIA credentials from a single file
        in a home directory ($HOME/.ria) instead of multiple files in many directories. We could
        also zip and encrypt this file.
        """
        cred_fn = Path.home() / ".ria"
        if not cred_fn.exists():
            raise ConfigError(f"RIA Credentials not found at {cred_fn}")

        with open(cred_fn, "rb") as f:
            return tomllib.load(f)

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

        print(f"Saving {path}")
        self.wb.save(filename=path)

    def _suspicous_character(self, *, identNr: str):
        if identNr is None or any("-", ";") in str(identNr):
            return True
