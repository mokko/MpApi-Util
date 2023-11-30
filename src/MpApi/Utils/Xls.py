"""

Composition over inheritance. So we're moving Excel related stuff from BaseApp.py to this class

USAGE
xls = Xls(path="test.xlsx")
xls.save()
xls.backup()
wb = xls.get_or_create_wb()

SPK-Forum
"""

from openpyxl import Workbook, load_workbook, worksheet
from openpyxl.styles import Alignment, Font
from pathlib import Path
import shutil
import openpyxl


class Xls:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.backup_fn = self.path.joinpath(".bak")
        self.wb = self.get_or_create_wb()
        self.shutdown_requested = False

    def backup(self) -> None:
        """
        Write a new backup file of the Excel file.
        """
        try:
            shutil.copy(self.path, self.backup_fn)
        except KeyboardInterrupt:
            self._request_shutdown()

    def get_or_create_sheet(self, *, title) -> openpyxl.worksheet.worksheet.Worksheet:
        try:
            ws = self.wb[title]  # sheet exists already
        except:  # new sheet
            ws = self.wb.active
            ws.title = sheet_title
        return ws

    def get_or_create_wb(self) -> Workbook:
        """
        Given a file path for an excel file, return the respective workbook
        or make a new one if the file doesn't exist.
        """
        # let's avoid side effects, although we're not doing this everywhere
        if self.path.exists():
            # print (f"* Loading existing excel: '{data_fn}'")
            return load_workbook(self.path, data_only=True)
        else:
            # print (f"* Starting new excel: '{data_fn}'")
            return Workbook()

    def save() -> None:
        """Made this only to have same print msgs all the time"""
        print(f"   saving {self.path}")

        try:
            self.wb.save(filename=self.path)
        except KeyboardInterrupt:
            self._request_shutdown()

    def write_table_description(self, *, description: dict, sheet: worksheet):
        """
        Take the table description (a dict) and write it to the top of the specified
        worksheet.

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

    #
    #
    #

    def _request_shutdown(self):
        print("Keyboard interrupt received, requesting gentle shutdown...")
        self.shutdown_requested = True
