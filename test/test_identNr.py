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
}


def test_constructor():
    f = IdentNrFactory()
    iNr = f.new_from_str(text="V A 10557")
    assert iNr
    assert iNr.text == "V A 10557"
    assert iNr.schemaId == 87
    # print (iNr.schemaId)


def test_cases():
    for ident_str in cases:
        ident_dict = cases[ident_str]
        print(f"***{ident_str}")
        print(f"***{ident_dict}")
        f = IdentNrFactory()
        iNr = f.new_from_str(text=ident_str)
        assert iNr.part1 == ident_dict[1]
        assert iNr.part2 == ident_dict[2]
        assert iNr.part3 == ident_dict[3]
        assert iNr.part4 == ident_dict[4]
