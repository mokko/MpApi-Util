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
from MpApi.Utils.Xls import Xls, ConfigError
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
    def __init__(self, *, col: int, file: str, sheet: str, limit: int = -1) -> None:
        self.limit = self._init_limit(limit)
        self.col = int(col)
        self.sheet = str(sheet)
        self.path = Path(file)
        self.xls = Xls(path=self.path, description={})
        user, pw, baseURL = get_credentials()
        self.client = MpApi(baseURL=baseURL, user=user, pw=pw)
        self.wb = self.xls.load_workbook()
        self.ws = self.xls.get_sheet(title=sheet)

        xml = header
        known = list()
        for row, rno in self.xls.loop2(sheet=self.ws, limit=self.limit):
            objId = row[self.col].value
            print(f"{rno} {objId}")
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
        print("validates, contacting RIA...")
        # r = self.client.createItem(module="ObjectGroup", xml=xml)
        # print(r.status_code)
        id = self.client.createItem3(data=m)
        # TODO: We do want to print out group id
        print(f"ObjectGroup {id} created.")
