"""
    So we manage to create objects with a new identNr now. But what we still cant do is
    create a record with a Bereich other than default. So in this test file we tackle
    this problem.
    
    create a record with minimal info and set the bereich
    
    Let's also re-read the Zetcom specification. It reminds we that we can get a list
    of writable orgUnits. We make a little script to do that.
    
    I've read Zetcom's page again. There is no clue how to set the orgUnit/Bereich. It 
    reminds me that orgUnit is part of their rights thing.
    
    So what fields do have something to do with the Bereich?
    
    <systemField dataType="Varchar" name="__orgUnit">
        <value>EMAllgemein</value>
    </systemField>

    <systemField dataType="Varchar" name="__orgUnit">
        <value>EMMusikethnologie</value>
    </systemField>

    <vocabularyReference name="ObjOrgGroupVoc" id="61643" instanceName="ObjOrgGroupVgr">
        <vocabularyReferenceItem id="1632801" name="EM-Musikethnologie">
            <formattedValue language="de">EM-Musikethnologie</formattedValue>
        </vocabularyReferenceItem>
    </vocabularyReference>
    id="3107523" uuid="ee4fa81a-26a1-473b-b41c-3c8d34d2231f"

    TEST was SUCCESSFUL WITH EMMusikethnologie and EMSudseeAustralien
"""

from mpapi.client import MpApi
from mpapi.module import Module
from mpapi.constants import get_credentials
from pathlib import Path

user, pw, baseURL = get_credentials()

xml = """
<application xmlns="http://www.zetcom.com/ria/ws/module">
  <modules>
    <module name="Object" totalSize="1">
      <moduleItem hasAttachments="false">
        <systemField dataType="Varchar" name="__orgUnit">
          <value>EMMusikethnologie</value>
        </systemField>
      </moduleItem>
    </module>
  </modules>
</application>
"""


if __name__ == "__main__":
    client = MpApi(baseURL=baseURL, user=user, pw=pw)
    m = Module(xml=xml)
    m.validate()
    print("m validates")
    objId = client.createItem3(data=m)

    print(f"objId {objId}")

    # print (f"Writing to {fn}")
    # m.toFile(path=fn)
