# from mpapi.search import Search
# from mpapi.module import Module
from mpapi.constants import get_credentials
from MpApi.Utils.Ria import RIA
from MpApi.Utils.prepareUpload import PrepareUpload
from MpApi.Utils.BaseApp import ConfigError


# from lxml import etree  # type: ignore
from pathlib import Path
import pytest

# NSMAP: dict = {"m": "http://www.zetcom.com/ria/ws/module"}

user, pw, baseURL = get_credentials()


def test_constructor_ria():
    c = RIA(baseURL=baseURL, user=user, pw=pw)
    assert isinstance(c, RIA)


# def test_prepare_fail():
# with pytest.raises(ConfigError) as e_info:
# p = PrepareUpload(
# limit=-1,
# )
# print (f"EXCEPTION ---{e_info}")


def test_prepare_new():
    p = PrepareUpload(
        limit=-1,
    )
