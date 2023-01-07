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
from MpApi.Utils.Ria import RiaUtil
from pathlib import Path
from openpyxl import Workbook, load_workbook
import sys

# from typing import Any


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
            print("Making new conf sheet")
            ws_conf = wb.create_sheet("conf")
        c = 1
        for name in conf:
            ws_conf[f"A{c}"] = name
            ws_conf[f"B{c}"] = conf[name]
            c += 1
        # return ws_conf
        # just access wb["conf"] if you need access

    def _init_client(self) -> RiaUtil:
        # avoid reinitializing although not sure that makes a significant difference
        if hasattr(self, "client"):
            return self.client
        else:
            return RiaUtil(baseURL=self.baseURL, user=self.user, pw=self.pw)

    # should we require conf_fn as a Path to be more consistent?
    def _init_conf(self, *, path: Path, job: str) -> dict:
        if not path.exists():
            raise SyntaxError("ERROR: Config file not found!")
        config = configparser.ConfigParser()
        config.read(path, "UTF-8")
        logging.info(f"config file {path} successfully loaded")
        try:
            return config[job]
        except:
            raise SyntaxError(f"Job '{job}'doesn't exist in config file!")

    def _init_excel(self, *, path: Path) -> Workbook:
        """
        Given a file path for an excel file, return the respective workbook
        or make a new one if the file doesn't exist.
        """
        if path.exists():
            # print (f"* Loading existing excel: '{data_fn}'")
            return load_workbook(path)
            # let's avoid side effects
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

    def _save_excel(self, path: Path) -> None:
        """Made this only to have same print msgs all the time"""

        print(f"* Saving {path}")
        self.wb.save(filename=path)