# from mpapi.search import Search
# from mpapi.module import Module
from MpApi.Utils.Ria import RiaUtil
from MpApi.Utils.prepareUpload import PrepareUpload
from MpApi.Utils.BaseApp import ConfigError


# from lxml import etree  # type: ignore
from pathlib import Path
import pytest

# NSMAP: dict = {"m": "http://www.zetcom.com/ria/ws/module"}

credentials = Path(__file__).parents[1] / "sdata/credentials.py"
with open(credentials) as f:
    exec(f.read())


def test_constructor_ria():
    c = RiaUtil(baseURL=baseURL, user=user, pw=pw)
    assert isinstance(c, RiaUtil)


def test_prepare_fail():
    with pytest.raises(ConfigError) as e_info:
        p = PrepareUpload(
            baseURL=baseURL,
            conf_fn="doesnt_exist.ini",
            job="test",
            limit=-1,
            pw=pw,
            user=user,
        )
    # print (f"EXCEPTION ---{e_info}")


def test_prepare_new():
    p = PrepareUpload(
        baseURL=baseURL,
        conf_fn="test_prepare.ini",
        job="Test",
        limit=-1,
        pw=pw,
        user=user,
    )
