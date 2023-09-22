from MpApi.Utils.Ria import RIA
from mpapi.constants import get_credentials

user, pw, baseURL = get_credentials()

c = RIA(baseURL=baseURL, user=user, pw=pw)
assert c

cases = {"V A 1934": {2165}}


def test_identNr_exists3():
    print(f"Login as user {user} using {baseURL}")

    for ident in cases:
        result = c.identNr_exists3(ident=ident)
        assert result == cases[ident]


def test_get_photographerID():
    idL = c.get_photographerID(name="Claudia Obrocki")
    # print(f"{idL}")
    assert idL == ["3597"]
