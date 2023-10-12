from MpApi.Utils.BaseApp import BaseApp

cases = {
    "V A 106 a": False,
    "V A 146": True,
    "V A 1934 a,b": False,
    "IXIX A 1934 a,b": False,  # does not exist
}


def test_no_parts():
    ba = BaseApp()
    for identNr in cases:
        # print (f"{identNr}: {cases[identNr]}")
        if cases[identNr]:
            assert not ba.has_parts(identNr=identNr)
        else:
            assert ba.has_parts(identNr=identNr)
