from mpapi.module import Module

# from mpapi.constants import get_credentials
from MpApi.Utils.identNr import IdentNrFactory

# from lxml import etree  # type: ignore
from pathlib import Path

# import pytest

# NSMAP: dict = {"m": "http://www.zetcom.com/ria/ws/module"}

cases = {
    "V A 11189 a,b": {
        1: "V",
        2: " A",
        3: "11189",
        4: "a,b",
    },
    "V C Dlg 3 ": {
        1: "V",
        2: " C Dlg",
        3: "3",
        4: "",
    },
    "V A Dlg 11189 a,b": {
        1: "V",
        2: " A Dlg",
        3: "11189",
        4: "a,b",
    },
    "VII a 123 a-c": {
        1: "VII",
        2: " a",
        3: "123",
        4: "a-c",
    },
    "VII a 123 a-c <1>": {
        1: "VII",
        2: " a",
        3: "123",
        4: "a-c <1>",
    },
    "VIII ME 123": {
        1: "VIII",
        2: " ME",
        3: "123",
        4: "",
    },
    "VIII ME Nls 123": {
        1: "VIII",
        2: " ME Nls",
        3: "123",
        4: "",
    },
    "VIII A 22450 (1)": {
        1: "VIII",
        2: " A",
        3: "22450",
        4: "(1)",
    },
    "VIII A 23052 (126)": {
        1: "VIII",
        2: " A",
        3: "23052",
        4: "(126)",
    },
    "VII OA 1005.12": {
        1: "VII",
        2: " OA",
        3: "1005",
        4: "12",
    },
    # Hendryk möchte diesen Fall für Kamerun 24 Projekt
    "III C 1234 a-?": {
        1: "III",
        2: " C",
        3: "1234",
        4: "a-?",
    },
}


def test_constructor():
    f = IdentNrFactory()
    iNr = f.new_from_str(text="V A 10557")
    # assert iNr
    # assert iNr.text == "V A 10557"
    # assert iNr.schemaId == 87
    # print (iNr.schemaId)


def test_cases_EM():
    f = IdentNrFactory()
    for ident_str in cases:
        ident_dict = cases[ident_str]
        # print(f"***{ident_str}")
        # print(f"***{ident_dict}")
        iNr = f.new_from_str(text=ident_str)
        assert iNr.part1 == ident_dict[1]
        assert iNr.part2 == ident_dict[2]
        assert iNr.part3 == ident_dict[3]
        assert iNr.part4 == ident_dict[4]
        print(f"{ident_str} ok 4:{iNr.part4}")


def test_cases_AKu():
    f = IdentNrFactory()
    iNr = f.new_from_str(text="IV/AKu/000059", institution="AKu")
    assert iNr.part1 == "IV"
    assert iNr.part2 == "AKu"
    assert iNr.part3 == "000059"
    assert iNr.part4 == ""
