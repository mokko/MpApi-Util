"""
A command line tool that makes a M+ ObjectGroup from an excel file.

Specify the column as 0-based column number.

-c | --col specify column with objId
mk_grp -c 0 -f excel.xlsx -l 1000 -s Prepare

    <moduleReference name="OgrObjectRef" targetModule="Object" multiplicity="M:N" size="1">
      <moduleReferenceItem moduleItemId="2722421" uuid="60c608ad-c649-442c-907a-14bac2d50b8a" seqNo="0">
        <formattedValue language="de">VII a 172, Oboe, Zourna, Christian Schneider (2019)</formattedValue>
        <dataField dataType="Long" name="SortLnu">
          <value>5</value>
          <formattedValue language="de">5</formattedValue>
        </dataField>
      </moduleReferenceItem>
    </moduleReference>
"""

from mpapi.client import MpApi
from mpapi.module import Module
from mpapi.constants import get_credentials
from MpApi.Utils.BaseApp import BaseApp
from MpApi.Utils.Ria import RIA
from MpApi.Utils.Xls import Xls
from pathlib import Path

header = """<application xmlns="http://www.zetcom.com/ria/ws/module">
  <modules>
    <module name="ObjectGroup">
      <moduleItem>"""

footer = """
      </moduleItem>
    </module>
  </modules>
</application>"""


class MakeGroup(BaseApp):
    def __init__(
        self,
        *,
        cmd: str,
        col: int,
        file: str,
        sheet: str,
        limit: int = -1,
        act: bool = False,
    ) -> None:
        self.limit = self._init_limit(limit)
        self.sheet = str(sheet)
        self.path = Path(file)
        self.xls = Xls(path=self.path, description={})
        self.wb = self.xls.load_workbook()
        self.ws = self.xls.get_sheet(title=sheet)
        user, pw, baseURL = get_credentials()
        self.client = MpApi(baseURL=baseURL, user=user, pw=pw)
        self.ria = RIA(baseURL=baseURL, user=user, pw=pw)
        match cmd:
            case "run":
                self.run(act, col)
            case "lookup":
                self.lookup(act, col)
            case _:
                raise TypeError("Unknown Command!")

    def lookup(self, act: bool, col: int):
        """
        We want to look up the objId behind the identNr specified in col.

        We write to the column specified in col.
        We expect IdentNr in col=1 (A)
        """

        self.xls.save()  # check if locked/open
        letter = chr(64 + col)
        print(f"writing objIds to col {col} -> {letter}")
        for row, rno in self.xls.loop2(sheet=self.ws, limit=self.limit):
            # loop starts at line 3 these days
            # only lookup if target cell is empty
            if self.ws[f"{letter}{rno}"].value is None:
                identNr = row[0].value
                objIdsL = self.ria.get_objIds_strict(identNr=identNr)
                objId = next(iter(objIdsL))
                print(f"{identNr=} {objIdsL} {objId}")
                if len(objIdsL) > 1:
                    raise KeyError("Multiple IDs. Not sure what to do here")
                print(f"{identNr=} {objId}")
                self.ws[f"{letter}{rno}"] = objId
        print("Saving excel file")
        self.xls.save()

    def mk_grp(self, col: int) -> Module:
        xml = header
        known = list()
        for row, rno in self.xls.loop2(sheet=self.ws, limit=self.limit):
            objId = row[col].value
            print(f"{rno}: {objId}")
            if objId is not None and objId != "None":
                objId = int(objId)
                if objId not in known:
                    xml += f""" 
                        <moduleReference name="OgrObjectRef" targetModule="Object">
                          <moduleReferenceItem moduleItemId="{objId}"/>
                        </moduleReference>"""
                known.append(objId)
        xml += footer
        m = Module(xml=xml)
        m.validate()
        m.toFile(path="mk_grp.debug.xml")
        return m

    def run(self, act: bool, col: int):
        m = self.mk_grp(col)
        print("validates, contacting RIA...")
        # r = self.client.createItem(module="ObjectGroup", xml=xml)
        # print(r.status_code)
        if act:
            id = self.client.createItem3(data=m)
            print(f"ObjectGroup {id} created.")
        else:
            print("Not acting because no act")
        # TODO: We do want to print out group id
