#from mpapi.search import Search
from mpapi.module import Module
from mpapi.client import MpApi
#from lxml import etree  # type: ignore
from pathlib import Path
import pytest

#NSMAP: dict = {"m": "http://www.zetcom.com/ria/ws/module"}

credentials = Path(__file__).parents[1] / "sdata/credentials.py"

with open(credentials) as f:
    exec(f.read())

# construction is tested in offline
client = MpApi(baseURL=baseURL, user=user, pw=pw)

#
# simple online tests
#

def test_create_empty_item():
    m = Module()
    objModule = m.module(name="Object")
    with pytest.raises(Exception) as e_info:
        objId = client.createItem3(data=m)
    #assert objId
    # fails with HTTP_Error 500 Server Error
    #print (objId)


def tast_create_nonempty_item():
    m = Module()
    objModule = m.module(name="Object")
    mItem = m.moduleItem(parent=objModule)
    m.dataField(parent=mItem, name="ObjSystematicClb", value="Architekturfotografie")
    objId = client.createItem3(data=m)
    assert objId
    print (objId)

def tast_create_ident_from_string(): # works
    m = Module()
    objModule = m.module(name="Object")
    mItem = m.moduleItem(parent=objModule)
    m.dataField(parent=mItem, name="ObjSystematicClb", value="Architekturfotografie")
    
    xml="""
    <application xmlns="http://www.zetcom.com/ria/ws/module">
        <modules>
            <module name="Object">
                <moduleItem> 
                    <repeatableGroup name="ObjObjectNumberGrp">
                        <repeatableGroupItem id="20934856">
                            <dataField name="InventarNrSTxt">
                                <value>VIII B 74</value>
                            </dataField>
                            <dataField name="Part1Txt">
                                <value>VIII</value>
                            </dataField>
                            <dataField name="Part2Txt">
                                <value> B</value>
                            </dataField>
                            <dataField name="Part3Txt">
                                <value>74</value>
                            </dataField>
                            <dataField name="SortLnu">
                                <value>1</value>
                            </dataField>
                            <vocabularyReference name="DenominationVoc">
                                <vocabularyReferenceItem id="2737051"/>
                            </vocabularyReference>
                            <moduleReference name="InvNumberSchemeRef" targetModule="InventoryNumber" multiplicity="N:1" size="1">
                                <moduleReferenceItem moduleItemId="68"/>
                            </moduleReference>
                        </repeatableGroupItem>
                    </repeatableGroup>
                </moduleItem>
            </module>
        </modules>
    </application>"""

    m = Module(xml=xml)

    objId = client.createItem3(data=m)
    assert objId
    print (objId)

def test_create_ident_from_shorter_string():
    
    m = Module()
    objModule = m.module(name="Object")
    mItem = m.moduleItem(parent=objModule)
    m.dataField(parent=mItem, name="ObjSystematicClb", value="Architekturfotografie")
    
    part1 = "VIII"
    part2 = " B"
    part3 = "74"
    invNrTxt = "VIII B 74"
    invNumberScheme = "68"
    
    xml=f"""
    <application xmlns="http://www.zetcom.com/ria/ws/module">
        <modules>
            <module name="Object">
                <moduleItem> 
                    <repeatableGroup name="ObjObjectNumberGrp">
                        <repeatableGroupItem>
                            <dataField name="InventarNrSTxt">
                                <value>{invNrTxt}</value>
                            </dataField>
                            <dataField name="Part1Txt">
                                <value>{part1}</value>
                            </dataField>
                            <dataField name="Part2Txt">
                                <value>{part2}</value>
                            </dataField>
                            <dataField name="Part3Txt">
                                <value>{part3}</value>
                            </dataField>
                            <dataField name="SortLnu">
                                <value>1</value>
                            </dataField>
                            <vocabularyReference name="DenominationVoc">
                                <vocabularyReferenceItem id="2737051"/>
                            </vocabularyReference>
                            <moduleReference name="InvNumberSchemeRef" targetModule="InventoryNumber" multiplicity="N:1" size="1">
                                <moduleReferenceItem moduleItemId="{invNumberScheme}"/>
                            </moduleReference>
                        </repeatableGroupItem>
                    </repeatableGroup>
                </moduleItem>
            </module>
        </modules>
    </application>"""

    print (xml)

    m = Module(xml=xml)

    objId = client.createItem3(data=m)
    assert objId
    print (objId)
