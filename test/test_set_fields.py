from becky import _load_conf

# from mpapi.constants import get_credentials
# from mpapi.search import Search
from MpApi.Utils.person_cache import open_cache, save_cache
from MpApi.Utils.set_fields_Object import _each_person, roles
from openpyxl import Workbook, load_workbook, worksheet
from pathlib import Path

conf_fn = "becky_conf.toml"  # in sdata
# roles = set()


def test_two() -> None:
    beteiligte = """
        Joachim Pfeil (30.12.1857 - 12.3.1924), Sammler*in; 
        Kaiserliches Auswärtiges Amt des Deutschen Reiches (1875), Veräußerung; 
        Bezug unklar: Paul Grade († 05.04.1894*¹)
    """
    for idx, (name, role) in enumerate(_each_person(beteiligte=beteiligte)):
        print(f"[{role}] {name}")
        match idx:
            case 0:
                assert name == "Joachim Pfeil"
                assert role == "Sammler*in"
            case 1:
                assert name == "Kaiserliches Auswärtiges Amt des Deutschen Reiches"
                assert role == "Veräußerung"
            case 2:
                assert name == "Paul Grade"
                assert role is None


def test_three() -> None:
    beteiligte = """
        Heinrich Barth (16.2.1821 - 25.11.1865), Sammler*in; 
        Königliche Preußische Kunstkammer, Ethnografische Abteilung (1801 - 1873), Vorbesitzer*in
    """
    for idx, (name, role) in enumerate(_each_person(beteiligte=beteiligte)):
        match idx:
            case 0:
                assert name == "Heinrich Barth"
                assert role == "Sammler*in"
            case 1:
                assert (
                    name
                    == "Königliche Preußische Kunstkammer, Ethnografische Abteilung"
                )
                assert role == "Vorbesitzer*in"


def test_four() -> None:
    assert 1 == 1


def test_one() -> None:
    conf = _load_conf()

    print(">> Reading workbook")
    wb = load_workbook(conf["excel_fn"], data_only=True)
    ws = wb[conf["sheet_title"]]  # sheet exists already

    print(">> Looping thru table")
    for idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
        print(f"Line {idx}")
        for name, role in _each_person(beteiligte=row[3].value):
            print(f"[{role}] {name}")
            if role is not None and role not in roles:
                assert False
