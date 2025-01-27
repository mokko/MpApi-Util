"""
We made a booboo. Now we're trying to fix it.

first: Loop through an excel and delete all entries in Weitere Nummer

second: Loop through the same stuff and write the correct number in there.

Or can we do that in one step? Why not

I am having trouble with the field "weitere Nummer". On closer inspection I notice that
this field has valid UUIDs. Can I do something with that?

        <repeatableGroup name="ObjOtherNumberGrp">
          <repeatableGroupItem id="59790729" uuid="254cf05b-aa75-446a-bbbd-1de244f86d28">
            <dataField name="SortLnu">
              <value>1</value>
            </dataField>
            <dataField name="NumberTxt">
              <value>311-11</value>
            </dataField>
            <vocabularyReference name="DenominationVoc">
              <vocabularyReferenceItem id="4399544"/>
            </vocabularyReference>
          </repeatableGroupItem>


"""

# from copy import deepcopy  # for lxml
from lxml import etree
from mpapi.constants import get_credentials, NSMAP
from MpApi.Utils.prepareUpload import PrepareUpload
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
        return PrepareUpload.desc("self")

    def main_loop(self) -> None:
        for cells, rno in self.xls.loop(sheet=self.ws, limit=self.limit):
            if cells["objIds"].value != "None":
                print(f"***{cells['identNr'].value}")
                self._rewrite_wNr(objId=cells["objIds"].value, new=cells["wNr"].value)

    #
    # more private
    #

    def _atomic_changes(self, *, doc, objId: int, new: str) -> None:
        """
        Other way tries atomic update operations on RIA. More calls. More precise
        log entries.
        """
        print(f"Atomic changes: objId {objId} {new=}")
        try:
            r = doc.xpath(
                """/m:application/m:modules/m:module[
                @name = 'Object'
            ]/m:moduleItem/m:repeatableGroup[
                @name = 'ObjOtherNumberGrp'
            ]/*""",
                namespaces=NSMAP,
            )
        except IndexError:
            print("No ObjOtherNumberGrp **Item** found")
        else:
            for idx, itemN in enumerate(r):
                refID = int(itemN.xpath("@id")[0])
                uuid = itemN.xpath("@uuid")[0]
                # print(etree.tostring(each, encoding="unicode"))
                print(f"about to rm item {refID} {uuid} {idx}/{len(r)}")
                self.client2.deleteRepeatableGroup(
                    module="Object",
                    id=objId,
                    referenceId=refID,
                    repeatableGroup="ObjOtherNumberGrp",
                )

        xml = f"""
        <application xmlns="http://www.zetcom.com/ria/ws/module">
            <modules>
                <module name="Object">
                    <moduleItem id="{objId}">
                        <repeatableGroup name="ObjOtherNumberGrp">
                          <repeatableGroupItem>
                            <dataField dataType="Long" name="SortLnu">
                              <value>1</value>
                            </dataField>
                            <dataField dataType="Varchar" name="NumberTxt">
                              <value>{new}</value>
                            </dataField>
                            <vocabularyReference name="DenominationVoc" id="77649" instanceName="ObjOtherNumberDenominationVgr">
                              <vocabularyReferenceItem id="4399544"/>
                            </vocabularyReference>
                          </repeatableGroupItem>
                        </repeatableGroup>
                    </moduleItem>
                </module>
            </modules>
        </application>
        """

        print("Creating new group item")
        self.client2.createRepeatableGroup(
            module="Object", id=objId, repeatableGroup="ObjOtherNumberGrp", xml=xml
        )

    def _global_changes(self, *, m: Module, objId: int, new: str) -> None:
        newN = etree.fromstring(f"""
            <repeatableGroup xmlns="http://www.zetcom.com/ria/ws/module" name="ObjOtherNumberGrp">
                <repeatableGroupItem>
                    <dataField dataType="Long" name="SortLnu">
                        <value>1</value>
                    </dataField>
                    <dataField dataType="Varchar" name="NumberTxt">
                        <value>{new}</value>
                    </dataField>
                    <vocabularyReference name="DenominationVoc" id="77649" instanceName="ObjOtherNumberDenominationVgr">
                        <vocabularyReferenceItem id="4399544"/>
                    </vocabularyReference>
                </repeatableGroupItem>
            </repeatableGroup>
        """)
        m.uploadForm()
        m._dropFieldsByName(element="dataField", name="ObjObjectNumberSortedTxt")
        m._dropFieldsByName(element="dataField", name="ObjObjectNumberTxt")
        m._dropFieldsByName(element="repeatableGroup", name="ObjOtherNumberGrp")
        m.toFile(path="debug2.xml")
        rGrpN = m.xpath("""/m:application/m:modules/m:module[
            @name = 'Object'
        ]/m:moduleItem/m:repeatableGroup[
            @name = 'ObjOtherNumberGrp'
        ]""")[0]
        rGrpN.getparent().replace(rGrpN, newN)
        m.toFile(path="debug.xml")
        m.validate()
        print("validates")
        # m2 = deepcopy(m)
        print("reuploading")
        self.client2.updateItem4(data=m)

    def _rewrite_wNr(self, *, objId: int, new: str) -> None:
        objId = int(objId)
        print(f"{objId=} {new=}")
        print("getting record from ria")
        m = self.client2.getItem2(mtype="Object", ID=objId)
        # self._global_changes(m=m, objId=objId, new=new)
        self._atomic_changes(doc=m.toET(), objId=objId, new=new)


if __name__ == "__main__":
    fix = Fix_wNr(limit=-1)
