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

def test_create_nonempty_item():
    m = Module()
    objModule = m.module(name="Object")
    mItem = m.moduleItem(parent=objModule)
    m.dataField(parent=mItem, name="ObjSystematicClb", value="Architekturfotografie")
    objId = client.createItem3(data=m)
    assert objId

    # fails with HTTP_Error 500 Server Error
    print (objId)
