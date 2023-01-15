# from mpapi.search import Search
# from mpapi.module import Module
from MpApi.Utils.Ria import RiaUtil

# from lxml import etree  # type: ignore
from pathlib import Path
import pytest

# NSMAP: dict = {"m": "http://www.zetcom.com/ria/ws/module"}

credentials = Path(__file__).parents[1] / "sdata/credentials.py"
with open(credentials) as f:
    exec(f.read())


def test_constructor():
    c = RiaUtil(baseURL=baseURL, user=user, pw=pw)
    assert isinstance(c, RiaUtil)
