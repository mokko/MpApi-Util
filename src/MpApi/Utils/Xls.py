"""

Composition over inheritance. So we're moving Excel related stuff from BaseApp.py to this class

USAGE
    xls = Xls(path="test.xlsx")
    xls.save()
    xls.backup()
    wb = xls.get_or_create_wb()
"""

import openpyxl
from openpyxl import Workbook, load_workbook, worksheet
from openpyxl.styles import Alignment, Font
from pathlib import Path
import shutil
import sys


class NoContentError(Exception):
    pass


class Xls:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.backup_fn = str(self.path) + ".bak"
        self.wb = self.get_or_create_wb()
        self.shutdown_requested = False

    def backup(self) -> None:
        """
        Write a new backup file of the Excel file.
        """
        try:
            shutil.copy(self.path, self.backup_fn)
        except KeyboardInterrupt:
            self.request_shutdown()

    def get_or_create_sheet(self, *, title) -> openpyxl.worksheet.worksheet.Worksheet:
        try:
            ws = self.wb[title]  # sheet exists already
        except:  # new sheet
            ws = self.wb.active
            ws.title = title
        return ws

    def get_or_create_wb(self) -> Workbook:
        """
        Given a file path for an excel file in self.path, return the respective workbook
        or make a new one if the file doesn't exist. We also save wb internally.
        """
        try:
            return self.wb
        except:
            if self.path.exists():
                # print (f"* Loading existing excel: '{data_fn}'")
                self.wb = load_workbook(self.path, data_only=True)
                return self.wb
            else:
                # print (f"* Starting new excel: '{data_fn}'")
                self.wb = Workbook()
                return self.wb

    def raise_if_no_content(
        self, sheet: openpyxl.worksheet.worksheet.Worksheet
    ) -> bool:
        """
        Assuming that after init excel has to have more than 2 lines.
        Returns False if there is content.
        """

        if sheet.max_row < 3:
            raise NoContentError(
                f"ERROR: no data found; excel contains {sheet.max_row} rows!"
            )
        return False

    def request_shutdown(self):
        """
        Prints a message and changes class variable. To be called in except KeyboardInterrupt.
        """
        print("Keyboard interrupt received, requesting gentle shutdown...")
        self.shutdown_requested = True

    def save(self) -> None:
        """Made this only to have same print msgs all the time"""
        print(f"   saving {self.path}")

        try:
            self.wb.save(filename=self.path)
        except KeyboardInterrupt:
            self.request_shutdown()

    def shutdown_if_requested(self):
        """
        Do the shutdown if class variable is set. To be used in the loop at an appropriate time.
        """
        if self.shutdown_requested:
            self.save()
            print("Planned shutdown.")
            sys.exit(0)

    def write_table_description(
        self, *, description: dict, sheet: openpyxl.worksheet.worksheet.Worksheet
    ):
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
