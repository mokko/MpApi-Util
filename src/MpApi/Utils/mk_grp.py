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


class Make_Group:
    def __init__(self, *, col: int, fn: Path, sheet: str, limit: int = -1) -> None:
        self.limit = self._init_limit(limit)
        self.col = int(col)
        self.path = fn
        self.xls = Xls(path=fn, description={})
        user, pw, baseURL = get_credentials()
        self.client = MpApi(baseURL=baseURL, user=user, pw=pw)
        self.wb = self.xls.load_wb()
        self.ws = self.xls.get_sheet(title=sheet)

        xml = header
        for row, rno in self.xls.loop2(sheet=self.ws, limit=self.limit):
            print("{rno} {row[self.col]}")
            objId = int(row[self.col].value)
            xml += f""" 
                <moduleReference name="OgrObjectRef" targetModule="Object">
                  <moduleReferenceItem moduleItemId="{objId}"/>
                </moduleReference>"""
        xml += footer

        print(xml)
        m = Module(xml=xml)
        m.validate()
        r = self.ria.createItem(module="ObjectGroup", xml=xml)
        # TODO: We do want to print out group id
        print(r.status_code)
