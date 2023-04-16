"""
Mover - moves files that are already in RIA to storage location.

mover init	   initialize Excel
mover scanir   recursively scan a dir
mover move     go the actual moving of the files

"""

from MpApi.Utils.BaseApp import BaseApp, ConfigError


excel_fn = Path("mover.xlsx")  # do we want a central Excel?
red = Font(color="FF0000")
# parser = etree.XMLParser(remove_blank_text=True)
teal = Font(color="008080")


class Mover(BaseApp):
    def __init__(self):
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
                "width": 15,
            },
            "fn_exists_orgUnit": {
                "label": "Assets mit diesem Dateinamen (orgUnit)",
                "desc": "mulId(s) aus RIA",
                "col": "C",
                "width": 15,
            },
            "fullpath": {
                "label": "absoluter Pfad",
                "desc": "aus Verzeichnis",
                "col": "H",
                "width": 20,
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

        self.write_table_description(ws)

        #
        # Conf Sheet
        #
        ws2 = self.wb.create_sheet("Conf")
        ws2["A1"] = "root_dir"
        ws2["B1"] = "orgUnit"

        ws2.column_dimensions["A"].width = 25

        for each in "A1":  # , "A2", "A3", "A4"
            ws2[each].font = Font(bold=True)

        self._save_excel(path=excel_fn)

    def move(self):
        pass

    def scandir(self):
        # check if excel exists, has the expected shape and is writable
        if not excel_fn.exists():
            raise ConfigError(f"ERROR: {excel_fn} NOT found!")

        # die if not writable so that user can close it before waste of time
        self._save_excel(path=excel_fn)
        try:
            self.ws = self.wb["Assets"]
        except:
            raise ConfigError("ERROR: Excel file has no sheet 'Assets'")

        if self.ws.max_row < 2:
            raise ConfigError(
                f"ERROR: Scandir needs an initialized Excel sheet! {self.ws.max_row}"
            )

        self.orgUnit = self._set_orgUnit("B2")
