"""
New Version of mkGrp2 that extends existing groups instead of making new ones

I think there are three possible situations
1. obj is already part of the groups
2. obj (objID) doesn't exist
3. we add another object to the existing group

Currently only for ObjectGroups that are filled with Objects.


<moduleReference name="OgrObjectRef"
                 targetModule="Object"
                 multiplicity="M:N"
                 size="1">
    <moduleReferenceItem moduleItemId="256199"
                         uuid="256199"
                         seqNo="0">
        <formattedValue language="de">VII b 184 b, Konustrommel, gosha naghara, Ebrahim Ehrari (1999)</formattedValue>
        <dataField dataType="Long"
                   name="SortLnu">
            <value>5</value>
            <formattedValue language="de">5</formattedValue>
        </dataField>
    </moduleReferenceItem>

assume upload form
    <moduleReferenceItem moduleItemId="256199"/>


/application/modules/module[@name = 'ObjectGroup']/moduleItem/moduleReference[@name = 'OgrObjectRef']
"""

grpId = 360397

import argparse
import lxml.etree as ET
from mpapi.client import MpApi
from mpapi.module import Module

with open("credentials.py") as f:
    exec(f.read())

NSMAP = {
    "m": "http://www.zetcom.com/ria/ws/module",
    "o": "http://www.zetcom.com/ria/ws/module/orgunit",
}


class GrpMaker2:
    def __init__(self, *, user, pw, baseURL) -> None:
        self.client = MpApi(baseURL=baseURL, user=user, pw=pw)
        # self.getWritableOrgUnits() # thinking about rights in RIA
        m = self.client.getItem2(mtype="ObjectGroup", ID=grpId)
        # if self.isOrgUnitWritable(record=m):
        #    print ("OrgUnit is writable")
        self.addObj2Grp(data=m, grpId=grpId, objId=256198)

    def addGrpItem(self, *, data: Module, objId: int):
        """
        Deprecated!

        We receive a complete ObjectGroup record and add one objId. We haven't manage to save
        this module data in RIA yet. I assume this may have something to do with the upload
        form.

        In this attempt we were working with a whole record. Next we will try updating only
        one moduleReference.
        """

        mRefItemN = data.xpath(
            """/m:application/m:modules/m:module[
            @name = 'ObjectGroup'
        ]/m:moduleItem/m:moduleReference[
            @name = 'OgrObjectRef'
        ]/m:moduleReferenceItem[last()]"""
        )[0]
        itemE = ET.Element("{http://www.zetcom.com/ria/ws/module}moduleReferenceItem")
        itemE.attrib["moduleItemId"] = str(objId)
        # itemE.attrib['uuid'] = str(objId)
        mRefItemN.addnext(itemE)

        # update size attribute
        mRefN = data.xpath(
            """/m:application/m:modules/m:module[
            @name = 'ObjectGroup'
        ]/m:moduleItem/m:moduleReference[
            @name = 'OgrObjectRef'
        ]"""
        )[0]

        itemCount = str(
            int(
                data.xpath(
                    """count(/m:application/m:modules/m:module[
            @name = 'ObjectGroup'
        ]/m:moduleItem/m:moduleReference[
            @name = 'OgrObjectRef'
        ]/m:moduleReferenceItem)"""
                )
            )
        )
        mRefN.attrib["size"] = itemCount
        # print (count)

        seqNo = 0
        for mrItemN in mRefN.xpath("./m:moduleReferenceItem", namespaces=NSMAP):
            print("_____")
            mrItemN.attrib["seqNo"] = str(seqNo)
            if "uuid" in mrItemN.attrib:
                del mrItemN.attrib["uuid"]
            seqNo += 1

    def addObj2Grp(self, *, grpId: int, objId: int):
        """
        This is the second attempt, where we get the full record, but only try to add
        one element, the moduleReference containing the list of objects in the group.

        I'm guessing we're changing data in place, like a reference.

        N.B. Parameter 'size' omitted since i dont know the size at this time.

        Todo: Test if given objId is already included or not.


        This method might become more generic:
        addMRefItem (mtype, mItemId, mRef, mRefId)
        addVRefItem (mtype, mItemId, mRef, mRefId)
        addRGrpItem (mtype, mItemId, mRef, mRefId)

        addGrpItem (mtype, mItemId, gtype, ref, refId)
        where gType is either moduleReference, vocabularyReference or repeatableGroup
        """
        rGrp = "OgrObjectRef"
        mtype = "ObjectGroup"

        xml = f"""<application xmlns="http://www.zetcom.com/ria/ws/module">
          <modules>
            <module name="{mtype}">
              <moduleItem id="{grpId}">
                <moduleReference name="{rGrp}" targetModule="Object" multiplicity="M:N">
                  <moduleReferenceItem moduleItemId="{objId}"/>
                </moduleReference>
              </moduleItem>
            </module>
          </modules>
        </application>"""

        r = self.client.createGrpItem2(
            mtype="ObjectGroup", ID=grpId, grpref=rGrp, xml=xml
        )
        return r
        # print (r)

    def checkIfObjIdsIncluded(self, *, mData: Module, objIds: list) -> list:
        """
        Check if objId is already part of the list in ObjectGroup.

        Returns a list/set of objIds that are included in the ObjectGroup mData.

        Usage:
            includedObjIds = self.checkIfObjIdIncluded(mData=m, objIds=['123', '124'])
        """

        mtype = "ObjectGroup"
        included = set()
        for objId in objIds:
            modRefItemL = mData.xpath(
                f"""/module[
                @name='{mtype}'
            ]/m:moduleItem/m:moduleReference[
                @name='OgrObjectRef'
            ]/m:moduleReferenceItem[
                @moduleItemId = '{objId}'
            ]"""
            )

            try:
                modRefItemL[0]
            except:
                pass
            else:
                included.add(objId)
        return included

    def isOrgUnitWritable(self, *, record: Module):
        """
        For a single record, we test if orgUnit is writable then we call RIA to check
        writable orgUnits and check if it's included.

        Todo: If we want to abstract this method, we need to make it available for all
        mtypes.
        """
        orgUnit = record.xpath(
            "//m:moduleItem[1]/m:systemField[@name = '__orgUnit']/m:value"
        )[0]
        # print (f"orgUnit in record: {orgUnit.text}")
        writableUnits = self.client.getOrgUnits()
        result = writableUnits.xpath(
            f"/o:application/o:modules/o:module/o:orgUnits/o:orgUnit[@name = '{orgUnit.text}']"
        )
        # print (result[0].attrib)
        try:
            result[0]
        except:
            return False
        else:
            return True

    def obj2Grp(self, *, objId, grpId):
        # mrN = m.xpath("m:/application/m:modules/m:module/m:moduleReference)[0]
        # updateRepeatableGroup2(mtype="ObjectGroup",ID=grpId, referenceId=rId, repeatableGroup, node=mrN)
        print(r)  # 204 is success without return value

    def touch(self, *, mtype, ID):
        """
        We want to save the record so that that get update the stamp, but dont really change
        any data, much like the Unix command touch.

        So we download the record and save it. This only seems to work if we actually changes
        something.

        This method is NOT particularly well test.
        """
        m = self.client.getItem2(mtype=mtype, ID=ID)
        r = self.client.updateItem2(mtype=mtype, ID=ID, data=m)

    def updateWholeObjectGroup(self, *, objId):
        m = self.client.getItem2(mtype="ObjectGroup", ID=grpId)
        m.uploadForm()
        self.addGrpItem(data=m, objId=256198)
        m.toFile(path="debug.xml")


if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description="make a group in RIA from Excel input")
    # parser.add_argument('-a', '--act', help='act or not to act', action='store_true')
    # parser.add_argument(
    #    "-c", "--column", help="specify the excel column with IDs", required=True
    # )
    # parser.add_argument("-i", "--input", help="path to Excel input file", required=True)
    # parser.add_argument("-n", "--name", help="name of new group", required=True)

    # args = parser.parse_args()
    gm = GrpMaker2(user=user, pw=pw, baseURL=baseURL)
    # gm.new(
    #    Input=args.input, column=args.column, name=args.name
    # )  # no return value planned ATM
