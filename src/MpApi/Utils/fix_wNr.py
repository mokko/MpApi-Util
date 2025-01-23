"""
We made a booboo. Now we're trying to fix it.

first: Loop through an excel and delete all entries in Weitere Nummer

second: Loop through the same stuff and write the correct number in there.

Or can we do that in one step? Why not
"""

from lxml import etree
from mpapi.constants import get_credentials
from MpApi.Utils.BaseApp import BaseApp
from MpApi.Utils.Ria import RIA
from MpApi.Utils.Xls import Xls
from mpapi.module import Module
from mpapi.client import MpApi


class Fix_wNr(BaseApp):
    def __init__(self, *, limit: int = -1) -> None:
        user, pw, baseURL = get_credentials()
        self.client = RIA(baseURL=baseURL, user=user, pw=pw)
        self.client2 = MpApi(baseURL=baseURL, user=user, pw=pw)

        print(f"Logged in as '{user}'")
        self.limit = self._init_limit(limit)
        print(f"Using limit {self.limit}")
        self.xls = Xls(path="löschen.xlsx", description=self.desc())
        self.wb = self.xls.get_or_create_wb()
        self.ws = self.xls.get_or_create_sheet(title="Prepare")
        self.xls.raise_if_no_content(sheet=self.ws)
        self.main_loop()

    def desc(self) -> dict:
        desc = {
            "filename": {
                "label": "Asset Dateiname",
                "desc": "aus Verzeichnis",
                "col": "A",  # 0
                "width": 20,
            },
            "identNr": {
                "label": "IdentNr",
                "desc": "aus Dateinamen",
                "col": "B",  # 1
                "width": 15,
            },
            "wNr": {
                "label": "Weitere Nr",
                "desc": "aus Dateinamen",
                "col": "C",  # 1
                "width": 15,
            },
            "asset_fn_exists": {
                "label": "Assets mit diesem Dateinamen",
                "desc": "mulId(s) aus RIA",
                "col": "D",  # 2
                "width": 15,
            },
            "objIds": {
                "label": "objId(s) aus RIA",
                "desc": "exact match für diese IdentNr",
                "col": "E",  # 3
                "width": 15,
            },
            "parts_objIds": {
                "label": "Geschwister",
                "desc": "für diese IdentNr",
                "col": "F",  # 4
                "width": 20,
            },
            "whole_objIds": {
                "label": "Ganzes objId",
                "desc": "exact match für diese IdentNr",
                "col": "G",  # 5
                "width": 20,
            },
            "ref": {
                "label": "Objekte-Link",
                "desc": "automat. Vorschlag für Objekte-DS",
                "col": "H",  # 6
                "width": 9,
            },
            "notes": {
                "label": "Bemerkung",
                "desc": "für Notizen",
                "col": "I",  # 7
                "width": 20,
            },
            "photographer": {
                "label": "Fotograf*in",
                "desc": "aus Datei",
                "col": "J",  # 8
                "width": 20,
            },
            "creatorID": {
                "label": "ID Urheber*in",
                "desc": "aus RIA",
                "col": "K",  # 9
                "width": 20,
            },
            "fullpath": {
                "label": "absoluter Pfad",
                "desc": "aus Verzeichnis",
                "col": "L",  # 10
                "width": 90,
            },
            # "targetpath": {
            # "label": "nach Bewegen der Datei",
            # "desc": "wenn Upload erfolgreich",
            # "col": "L",  # 11
            # "width": 30,
            # },
            "attached": {
                "label": "Asset hochgeladen?",
                "desc": "wenn Upload erfolgreich",
                "col": "M",  # 12
                "width": 15,
            },
            "standardbild": {
                "label": "Standardbild",
                "desc": "Standardbild setzen, wenn noch keines existiert",
                "col": "N",  # 13
                "width": 5,
            },
        }
        return desc

    def main_loop(self) -> None:
        for cells, rno in self.xls.loop(sheet=self.ws, limit=self.limit):
            if cells["objIds"].value != "None":
                self._rewrite_wNr(objId=cells["objIds"].value, new=cells["wNr"].value)

    def _rewrite_wNr(self, *, objId: int, new: str) -> None:
        newN = etree.fromstring(f"""
        <repeatableGroup xmlns="http://www.zetcom.com/ria/ws/module" name="ObjOtherNumberGrp" size="1">
          <repeatableGroupItem>
            <dataField dataType="Long" name="SortLnu">
              <value>1</value>
              <formattedValue language="de">1</formattedValue>
            </dataField>
            <dataField dataType="Varchar" name="NumberTxt">
              <value>{new}</value>
            </dataField>
            <vocabularyReference name="DenominationVoc" id="77649" instanceName="ObjOtherNumberDenominationVgr">
              <vocabularyReferenceItem id="4399544" name="Sammler-Nr.">
                <formattedValue language="de">Sammler-Nr.</formattedValue>
              </vocabularyReferenceItem>
            </vocabularyReference>
          </repeatableGroupItem>
        </repeatableGroup>""")

        objId = int(objId)
        print(f"{objId=} {new=}")
        print("getting record from ria")
        m = self.client.get_template(mtype="Object", ID=objId)
        rGrpN = m.xpath("""/m:application/m:modules/m:module[
                @name ='Object'
            ]/m:moduleItem/m:repeatableGroup[
                @name = 'ObjOtherNumberGrp'
            ]""")[0]
        # rGrpN.getparent().replace(rGrpN, newN)
        m.validate()
        print("validates")
        m.uploadForm()
        m.toFile(path="debug.xml")
        print("reuploading")
        self.client2.updateItem2(mtype="Object", ID=objId, data=m)


if __name__ == "__main__":
    fix = Fix_wNr(limit=3)
