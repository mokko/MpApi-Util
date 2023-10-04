# from mpapi.search import Search
from mpapi.module import Module
from mpapi.constants import get_credentials
from MpApi.Utils.Ria import RIA

# from lxml import etree  # type: ignore
from pathlib import Path
import pytest

# NSMAP: dict = {"m": "http://www.zetcom.com/ria/ws/module"}


# construction is tested in offline
user, pw, baseURL = get_credentials()
client = RIA(baseURL=baseURL, user=user, pw=pw)

#
# simple online tests
#


def test_id_exists():
    assert client.id_exists(mtype="Object", ID=257778)
    assert not client.id_exists(mtype="Object", ID=9999999999)


#
# LOOKUPs: test_identNr
#


def test_identNr_exists():
    ret = client.identNr_exists(nr="does not exist")
    assert isinstance(ret, list)
    assert not ret  # should be item list which is falsy
    ret = client.identNr_exists(nr="VII f 123")
    assert isinstance(ret, list)
    assert ret  # should be list with item which is truthy
    assert len(ret) == 1
    # print (ret[0])
    assert ret[0] == 258165  # implicitly tests if result is integer


def test_identNr_exists_orgUnit():
    ret = client.identNr_exists(nr="VII f 123", orgUnit="EMMusikethnologie")
    assert len(ret) == 1

    ret = client.identNr_exists(nr="VII f 123", orgUnit="EMAllgemein")
    assert len(ret) == 0


def test_identNr_exists_bad_orgUnit():
    with pytest.raises(Exception) as e_info:
        # if orgUnit does not exist, we get a HTTPError 400 bad request
        ret = client.identNr_exists(nr="VII f 123", orgUnit="doesnotexist")


#
# fn_to_mulId
#


def test_fn_to_mulId():
    r = client.fn_to_mulId(fn="VII f 123 -A x.jpg")  # , orgUnit=None
    assert r
    assert len(r) == 1
    assert isinstance(r, set)
    r = client.fn_to_mulId(fn="does not exist")  # , orgUnit=None
    assert not r
    assert isinstance(r, set)


def test_fn_to_mulId_orgUnit():
    r = client.fn_to_mulId(fn="VII f 123 -A x.jpg", orgUnit="EMMusikethnologie")
    assert len(r) == 1
    assert isinstance(r, set)
    r = client.fn_to_mulId(fn="VII f 123 -A x.jpg", orgUnit="EMAllgemein")
    assert len(r) == 0
    assert isinstance(r, set)


def test_fn_to_mulId_bad_orgUnit():
    with pytest.raises(Exception) as e_info:
        # if orgUnit does not exist, we get a HTTPError 400 bad request
        ret = client.fn_to_mulId(fn="VII f 123 -A x.jpg", orgUnit="doesnotexist")


#
# get_template
#


def test_get_template():
    m = client.get_template(mtype="Object", ID=1511764)
    assert isinstance(m, Module)
    assert len(m) == 1


def test_get_template_bad():
    # id does not exist
    with pytest.raises(Exception) as e_info:
        m = client.get_template(mtype="Object", ID=9999999999)


def test_get_template_bad2():
    # id mtype does not exist
    with pytest.raises(Exception) as e_info:
        m = client.get_template(mtype="Objekte", ID=1511764)
        print(e_info)
