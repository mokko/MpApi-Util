"""
Mover - moves files that are already in RIA to storage location.

mover init	   initialize Excel
mover scanir   recursively scan a dir
mover move     go the actual moving of the files

"""

from MpApi.Utils.BaseApp import BaseApp, ConfigError
from MpApi.Utils.Ria import RIA
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from pathlib import Path
import shutil

excel_fn = Path("mover.xlsx")  # do we want a central Excel?
red = Font(color="FF0000")
# parser = etree.XMLParser(remove_blank_text=True)
teal = Font(color="008080")


class Mover(BaseApp):
    def __init__(self, *, limit):
        self.limit = int(limit)  # allows to break the go loop after number of items
        creds = self._read_credentials()
        self.client = RIA(baseURL=creds["baseURL"], user=creds["user"], pw=creds["pw"])
        self.wb = self._init_excel(path=excel_fn)

        self.table_desc = {
            "filename": {
                "label": "Dateiname",
                "desc": "aus Verzeichnis",
                "col": "A",
                "width": 20,
            },
            "fn_exists": {
                "label": "Assets mit diesem Dateinamen",
                "desc": "mulId(s) aus RIA",
                "col": "B",
                "width": 20,
            },
            "fn_exists_orgUnit": {
                "label": "Assets mit diesem Dateinamen (orgUnit)",
                "desc": "mulId(s) aus RIA",
                "col": "C",
                "width": 20,
            },
            "move": {
                "label": "Bewegen?",
                "desc": "zu Backup Verzeichnis",
                "col": "D",
                "width": 8,
            },
            "relpath": {
                "label": "relativer Pfad",
                "desc": "aus Verzeichnis",
                "col": "G",
                "width": 30,
            },
            "fullpath": {
                "label": "absoluter Pfad",
                "desc": "aus Verzeichnis",
                "col": "H",
                "width": 40,
            },
            "targetpath": {
                "label": "Zielpfad",
                "desc": "",
                "col": "I",
                "width": 40,
            },
        }

    def init(self):
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
        ws.title = "Dateien"

        self._write_table_description(ws)

        #
        # Conf Sheet
        #
        ws2 = self.wb.create_sheet("Conf")
        ws2["A1"] = "target dir"
        ws2["A2"] = "orgUnit"

        ws2.column_dimensions["A"].width = 25

        for each in "A1":  # , "A2", "A3", "A4"
            pass
            # ws2[each].font = Font(bold=True)
        self._save_excel(path=excel_fn)

    def move(self):
        self._check_move()
        mrow = self.ws.max_row
        for c, rno in self._loop_table2():
            if c["targetpath"].value is not None:
                fro = Path(c["relpath"].value)
                to = Path(c["targetpath"].value)
                if not to.parent.exists():
                    to.parent.mkdir(parents=True)
                print(f"{rno}/{mrow}: {fro}")
                # print(f"   {to}")
                if fro.exists():
                    shutil.move(fro, to)

    def scandir(self):
        # check if excel exists, has the expected shape and is writable
        self._check_scandir()
        src_dir = Path()
        c = 3
        for p in src_dir.rglob("*"):
            if p.name.startswith(".") or p.name.startswith("~") or p == excel_fn:
                continue
            elif p.suffix in (".lnk"):
                continue
            elif p.is_dir():
                continue
            elif p.name.lower() == "thumbs.db" or p.name.lower() == "desktop.ini":
                continue
            self._scan_per_file(path=p, count=c)
            if self.limit == c:
                print("* Limit reached")
                break
            c += 1
        self._save_excel(path=excel_fn)

    #
    # private
    #
    def _check_move(self) -> None:
        if not excel_fn.exists():
            raise ConfigError(f"ERROR: {excel_fn} NOT found!")

        self._save_excel(path=excel_fn)

        try:
            self.ws = self.wb["Dateien"]
        except:
            raise ConfigError("ERROR: Excel file has no sheet 'Dateien'")

        if self.ws.max_row < 3:
            raise ConfigError(f"ERROR: Excel empty!")

    def _check_scandir(self) -> None:
        if not excel_fn.exists():
            raise ConfigError(f"ERROR: {excel_fn} NOT found!")

        self._save_excel(path=excel_fn)
        try:
            self.ws = self.wb["Dateien"]
        except:
            raise ConfigError("ERROR: Excel file has no sheet 'Dateien'")

        if self.ws.max_row < 2:
            raise ConfigError(
                f"ERROR: Scandir needs an initialized Excel sheet! {self.ws.max_row}"
            )
        elif self.ws.max_row > 2:
            raise ConfigError(f"ERROR: Mover's scandir can't re-run scandir!")
        self.orgUnit = self._set_orgUnit("B2")

        conf_ws = self.wb["Conf"]
        if conf_ws["B1"] is None:
            raise ConfigError("ERROR: Need target directory!")

        self.target_dir = Path(conf_ws["B1"].value)

    def _scan_per_file(self, *, path: Path, count: int) -> None:
        """
        Writes to self.ws
        """

        def is_number(x):
            if x is None:
                return False
            try:
                float(x)
                return True
            except ValueError:
                return False

        def is_a_list(x):
            if x is None:
                return False
            if ";" in x:
                return True

        c = self._rno2dict(count)
        # only write in empty fields
        if c["filename"].value is None:
            c["filename"].value = path.name
        if c["fn_exists"].value is None:
            idL = self.client.fn_to_mulId(fn=path.name, orgUnit=None)
            if len(idL) == 0:
                c["fn_exists"].value = "None"
            else:
                c["fn_exists"].value = "; ".join(idL)
        if self.orgUnit is not None:
            if c["fn_exists_orgUnit"].value is None:
                idL = self.client.fn_to_mulId(fn=path.name, orgUnit=self.orgUnit)
                if len(idL) == 0:
                    c["fn_exists_orgUnit"].value = "None"
                else:
                    c["fn_exists_orgUnit"].value = "; ".join(idL)
        if c["move"].value is None:
            if is_number(c["fn_exists"].value) or is_number(
                c["fn_exists_orgUnit"].value
            ):
                c["move"].value = "x"
            elif is_a_list(c["fn_exists"].value) or is_a_list(
                c["fn_exists_orgUnit"].value
            ):
                c["move"].value = "x"
            else:
                c["move"].value = "None"
        if c["relpath"].value is None:
            c["relpath"].value = str(path)
        if c["fullpath"].value is None:
            c["fullpath"].value = str(path.absolute())
        if c["move"].value == "x":
            fro = Path(c["relpath"].value)
            to = self.target_dir / fro
            c["targetpath"].value = str(to)
        print(f"{count}: {path.name} [{c['move'].value}]")

        # if (count/200).is_integer():
        #    self._save_excel(path=excel_fn)
