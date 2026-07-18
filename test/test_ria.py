from MpApi.Utils.Ria import RIA, record_exists, record_exists2, record_exists3
from mpapi.constants import get_credentials

user, pw, baseURL = get_credentials()

c = RIA(baseURL=baseURL, user=user, pw=pw)
print(f"Login as user {user} using {baseURL}")
assert c


def test_identNr_exists3():
    # identNr_exists returns sets, may be empty set
    # curley braces creates a set
    cases = {
        "V A 1934": {2165},
        "I D 31949 (002 a)": {3825631},
        "I D 31949 (003)": {4122194},
    }

    for ident in cases:
        result = c.identNr_exists3(ident=ident)
        assert result == cases[ident]


def test_record_exists() -> None:
    conf = {
        "org_unit": "EMAfrika1",
        "RIA": c,
    }

    cases = {
        "III D 1196": 0,  # should see no result
    }
    for ident in cases:
        result = record_exists(ident=ident, conf=conf)
        assert result == cases[ident]
        result2 = record_exists3(ident=ident, conf=conf)
        assert result2 == 1  # only 1 from Leipzig-Rückführung


# todo: write test for record.exists2


def test_record_exists3() -> None:
    # record_exists2 returns numbers of matches, but not the ID
    conf = {
        "RIA": c,
    }
    cases = {
        "V A 1934": 1,
        "I D 31949 (002 a)": 1,
        "I D 31949 (003)": 1,
    }
    for ident in cases:
        result = record_exists3(ident=ident, conf=conf)
        assert result == cases[ident]


def test_get_photographerID():
    # looks up photographer by name in self.photographer_cache.
    # If cache is empty, RIA runs _get_photographerID to fill it.
    # c.photographer_cache.update({"Claudia Obrocki": 3597}) not sure this is correct
    # get_photographerID returns list of int
    idL = c.get_photographerID(name="Claudia Obrocki")
    # print(f"{idL}")
    assert idL == [3597]


def test_get_photographerID_None():
    idL = c.get_photographerID(name=None)
    # print(f"{idL}")
    assert idL == None


def test_get_objIds_startswith():
    """
    New version that returns a dictionary.
    """
    cases = {
        258381: {"identNr": "VII Nls 7", "orgUnit": "EMMusikethnologie"},
        185159: {"identNr": "I B 11804", "orgUnit": "EMIslamischerOrient"},
    }
    for objId in cases:
        identNr = cases[objId]["identNr"]
        orgUnit = cases[objId]["orgUnit"]
        adict = c.get_objIds_startswith(identNr=identNr, orgUnit=orgUnit)

        assert objId in adict.keys()
        # print(adict)
        # identNr = cases[objId]["identNr"]
        # assert objId in adict.keys()
        # assert adict[objId] == identNr


def test_get_objIds_strict():
    """
    New version that returns a dictionary.

    A record can have multiple identNr, but how many objNumbers?
    dict = {
        objId: "objNumber"
    }
    """
    cases = {
        2590344: {"identNr": "VII c 1038", "orgUnit": "EMMusikethnologie"},
        258381: {"identNr": "VII Nls 7 <1>", "orgUnit": "EMMusikethnologie"},
    }
    for objId in cases:
        identNr = cases[objId]["identNr"]
        orgUnit = cases[objId]["orgUnit"]
        adict = c.get_objIds_strict(identNr=identNr, orgUnit=orgUnit)

        print(adict)
        identNr = cases[objId]["identNr"]
        assert objId in adict.keys()
        assert adict[objId] == identNr


def test_fn_to_mulId():
    """ """
    resultS = c.fn_to_mulId(fn="I B 1895 a -B.jpg", orgUnit="EMIslamischerOrient")
    # print(f"{resultS=}")
    assert len(resultS) == 1 and "7648227" in resultS
