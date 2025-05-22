# from mpapi.constants import get_credentials
# from mpapi.search import Search
from copy import deepcopy
from MpApi.Utils.becky.cache_ops import open_person_cache, save_person_cache
from MpApi.Utils.becky.set_fields_Object import (
    _each_person,
    _lookup_name,
    roles,
    set_ident,
    set_ident_sort,
    set_sachbegriff,
    set_beteiligte,
    set_erwerbDatum,
    set_erwerbungsart,
    set_erwerbNr,
    set_erwerbVon,
    set_geogrBezug,
    set_invNotiz,
    set_objRefA,
)
from MpApi.Utils.Ria import RIA, init_ria
from pathlib import Path
import pytest

# conf_fn = Path(__file__).parents[1] / "sdata" / "becky_conf.toml"


def test_each_person1() -> None:
    beteiligte = """
        Joachim Pfeil (30.12.1857 - 12.3.1924), Sammler*in; 
        Kaiserliches Auswärtiges Amt des Deutschen Reiches (1875), Veräußerung; 
        Bezug unklar: Paul Grade († 05.04.1894*)
    """
    for idx, (name, role, date) in enumerate(_each_person(beteiligte=beteiligte)):
        print(f"[{role}] {name}")
        match idx:
            case 0:
                assert name == "Joachim Pfeil"
                assert role == "Sammler*in"
                assert date == "30.12.1857 - 12.3.1924"
            case 1:
                assert name == "Kaiserliches Auswärtiges Amt des Deutschen Reiches"
                assert role == "Veräußerung"
                assert date == "1875"
            case 2:
                assert name == "Paul Grade"
                assert role is None
                assert date == "† 05.04.1894*"


def test_each_person2() -> None:
    beteiligte = """
        Heinrich Barth (16.2.1821 - 25.11.1865), Sammler*in; 
        Königliche Preußische Kunstkammer, Ethnografische Abteilung (1801 - 1873), Vorbesitzer*in
    """
    for idx, (name, role, date) in enumerate(_each_person(beteiligte=beteiligte)):
        match idx:
            case 0:
                assert name == "Heinrich Barth"
                assert role == "Sammler*in"
                assert date == "16.2.1821 - 25.11.1865"
            case 1:
                assert (
                    name
                    == "Königliche Preußische Kunstkammer, Ethnografische Abteilung"
                )
                assert role == "Vorbesitzer*in"
                assert date == "1801 - 1873"


def test_lookup_person() -> None:
    conf = {
        "person_cache": "person_cache.toml",
        "project_dir": Path(__file__).parents[1] / "sdata",
    }

    valid_cases = {
        "Henriquez & Petersen": 335532,
    }

    # why is this person problematic? Because he used to exist twice in index?
    # Should be solved soon
    problematic = {"Carl Ritter": [2438]}

    for name in valid_cases:
        assert _lookup_name(name=name, conf=conf) == valid_cases[name]

    for name in problematic:
        assert _lookup_name(name=name, conf=conf) == problematic[name]
    # doesn't raise anymore
    # for name in problematic:
    #    with pytest.raises(TypeError):
    #        _lookup_name(name=name, conf=conf)


#
# live tests requiring access to RIA
#


def test_set_ident() -> None:
    """
    TODO: I should be testing all of the fields that are set
    - InventarNrSTxt,
    - Part1Txt,
    - Part2Txt,
    - Part3Txt,
    - Part4Txt,
    - SortLnu,
    - DenominationVoc,
    - InvNumberSchemeRef
    """

    client = init_ria()
    templateM = client.get_template(ID=625690, mtype="Object")
    recordM = deepcopy(templateM)  # record should contain only one moduleItem
    set_ident(recordM, ident="III C 123", institution="EM")
    # print(recordM)
    # recordM.toFile(path="test.debug.xml")
    InventarNrSTxt = recordM.xpath("""/m:application/m:modules/m:module[
        @name = 'Object'
    ]/m:moduleItem/m:repeatableGroup[
        @name = 'ObjObjectNumberGrp'
    ]/m:repeatableGroupItem/m:dataField[@name ='InventarNrSTxt']/m:value/text()""")[0]

    assert InventarNrSTxt == "III C 123"


def test_set_beteiligte() -> None:
    # test doesn't work yet in a meaningful way
    conf = {
        "person_cache": "person_cache.toml",
        "project_dir": Path(__file__).parents[1] / "sdata",
    }

    client = init_ria()
    templateM = client.get_template(ID=625690, mtype="Object")
    recordM = deepcopy(templateM)  # record should contain only one moduleItem
    set_beteiligte(recordM, beteiligte="Henriquez & Petersen", conf=conf)
    # print(recordM)
    # recordM.toFile(path="test.debug.xml")
    InventarNrSTxt = recordM.xpath("""/m:application/m:modules/m:module[
        @name = 'Object'
    ]/m:moduleItem/m:repeatableGroup[
        @name = 'ObjObjectNumberGrp'
    ]/m:repeatableGroupItem/m:dataField[@
        name ='InventarNrSTxt'
    ]/m:value/text()""")[0]
