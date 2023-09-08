"""

In April 2023 we begin our 2nd app using this framework. First of all, we trying to 
improve the credenials system. We want to provide a single credentials file and we
also might restrict from all too curious eyes.

"""

from MpApi.Utils.AssetUploader import AssetUploader
import os
from pathlib import Path


def test_construction():
    u = AssetUploader()
    assert u


def test_init():
    p = Path("upload.xlsx")
    if p.exists():
        os.remove(p)
    u = AssetUploader()
    u.init()


# creates new excel which lacks config info
def tast_scandir():
    u = AssetUploader()
    u.scandir(Dir="adir")

def test_get_objIds_for_whole():
    """
    For the part-form, we want to get the corresponding wholes.
    
    Return value should be a potentially empty list with objIds [], [1234]
    """
    cases = {
        "V A 106 a": set(), # whole is "V A 106", but no DS with this Ident exists
        "V A 146": set(), # has no part info, so cannot yield results
        "V A 1934 a,b": {2165}, # "V A 1934" is 2165
        "IXIX A 1934 a,b": set(), # identNr does not exist, so no objId
    }

    u = AssetUploader()
    for identNr in cases:
        if u.has_parts(identNr=identNr):
            objIdL = u._get_objIds_for_whole(identNr=identNr)
            print (f"{identNr}: {objIdL=}")
            assert objIdL == cases[identNr]

def test_get_parts():
    cases = {
        "V A 106 a": False,
        "V A 146": True,
        "V A 1934 a,b": False,
        "IXIX A 1934 a,b": False, # identNr does not exist
    }
    #True/False signifies if _get_whole should return True
    

    u = AssetUploader()
    for identNr in cases:
        objIdL = u._get_parts(identNr=identNr)
        print (f"{identNr}: {objIdL=}")
        if cases[identNr]:
            assert objIdL
        else:
            assert not objIdL    
        #if identNr == "V A 106 a"
        #    assert ident_whole == "V A 106"
        #print (f"{identNr}: {cases[identNr]}")

