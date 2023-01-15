from mpapi.module import Module
from MpApi.Utils.identNr import IdentNrFactory

# from lxml import etree  # type: ignore
from pathlib import Path
import pytest

# NSMAP: dict = {"m": "http://www.zetcom.com/ria/ws/module"}

credentials = Path(__file__).parents[1] / "sdata/credentials.py"

with open(credentials) as f:
    exec(f.read())


def test_constructor():

    f = IdentNrFactory()
    iNr = f.new_from_str(text="V A 10557")
    assert iNr
    assert iNr.text == "V A 10557"
    assert iNr.schemaId == 87
    # print (iNr.schemaId)
