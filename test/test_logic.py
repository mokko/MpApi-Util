from MpApi.Utils.logic import extractIdentNr, is_suspicious, has_parts, whole_for_parts
from pathlib import Path


def test_extractIdent():
    cases = {
        "220222": "220222",
        "Adr_(EJ)_1__0044.jpg": "Adr (EJ) 1",
        "HK_Afr_1__0001.jpg": "HK Afr 1",
        "HK_AmArch_1__0001.jpg": "HK AmArch 1",
        "HK_AmEth_32__0001.jpg": "HK AmEth 32",
        "HK_ISL_9__0001.jpg": "HK ISL 9",
        "HK_ONA_2__0100.jpg": "HK ONA 2",
        "HK_SOA_24__0024.jpg": "HK SOA 24",
        "HK_SUA_1__0001.jpg": "HK SUA 1",
        "HK_VIII_1__0001.jpg": "HK VIII 1",
        "Inv_1__0001.jpg": "Inv 1",
        "I_MV_0401__0001.tif": "I/MV 0401",
        "I_MV_0950_a__0290.jpg": "I/MV 0950 a",
        "Verz_BGAEU_1__0001.jpg": "Verz. BGAEU 1",
        "VII a 123 c-KK.tif": "VII a 123 c",
        "VII c 86 a -A x.tif": "VII c 86 a",
        # "VII c 86 a <1>-A x.tif": "VII c 86 a <1>", # <> are not allowed in filenames
        "I_MV_0404_3__0051.jpg": "I/MV 0404 <3>",
        "P 11766.tif": "P 11766",
        "VIII C 20274 (P 10054).tif": "VIII C 20274",
        "VIII 126 -A.tif": "VIII 126",
        "VIII NA 13 b___-A.tif": "VIII NA 13 b",
        "I C 8266 mit I C 8265, I C 8300.tif": "I C 8266",
        "VI 35989 -KK RS.jpg": "VI 35989",
        "VI 35989 -KK.jpg": "VI 35989",
        "I C 972 a-h -KK -B.jpg": "I C 972 a-h",
        "V A 142 a,b___-KK-A.tif": "V A 142 a,b",
        "VIII NA 1650 Rückseite.tif": "VIII NA 1650",
    }
    for case in cases:
        case = Path(case)
        identNr = extractIdentNr(path=case, parser="EM")
        print(f"{case} -> {identNr}")
        assert cases[str(case)] == identNr


def test_has_parts():
    cases = {
        "220222": False,
        "Adr (EJ) 1": False,
        "HK Afr 1": False,
        "VII a 123 a": True,
        "VII a 123 a,b": True,
        "VII a 123 a-c": True,
        "IV 124 a": True,
        "IV 124 a,b": True,
        "HK AmArch 1": False,
        "I/MV 0401": False,
        "I/MV 0950 a": True,
        "VII c 86 p-zz": True,
        "P 11766": False,
        "I C 8266": False,
        "I C 972 a-h": True,
        "I C 8266 <1>": False,
        "I C 1577 a-g <2>": True,
        "I C 1577 A <2>": False,
    }

    for identNr in cases:
        print(f"has_parts: {identNr}: {cases[identNr]}")
        assert cases[identNr] == has_parts(identNr=identNr)


def test_is_suspicious():
    cases = {
        "Oboe oNr": True,
        "Schalenhalslaute oNr": True,
        "I/MV 0404 <3>": False,
        "III C 22851 (HK": True,
        "VII a 123 a-c <1>": False,
        "VII a 123 a-c": False,
        "VII a 123": False,
        "III C 22851   glg": True,
        "III C 22851  glg": True,
        1: True,
        " ": True,
        "III Nls(Sanduhrtrommel 2)": True,
        "III Nls)Sanduhrtrommel 2": True,
        "0123456789": False,
        "P 21847, P 21848 Rückseite": True,
    }

    for identNr in cases:
        assert cases[identNr] == is_suspicious(identNr=identNr)


def test_whole_for_parts():
    cases = {
        "220222": "220222",
        "Adr (EJ) 1": "Adr (EJ) 1",
        "VII a 123 a": "VII a 123",
        "VII a 123 a,b": "VII a 123",
        "VII a 123 a-c": "VII a 123",
        "IV 124 a": "IV 124",
        "IV 124 a,b": "IV 124",
        "HK AmArch 1": "HK AmArch 1",
        "I/MV 0950 a": "I/MV 0950",
        "VII c 86 p-zz": "VII c 86",
        "P 11766": "P 11766",
        "I C 8266": "I C 8266",
        "I C 972 a-h": "I C 972",
        "I C 8266 <1>": "I C 8266 <1>",
        "I C 1577 a-g <2>": "I C 1577 <2>",
        "I C 1577 A <2>": "I C 1577 A <2>",
    }
    for identNr in cases:
        whole_ident = whole_for_parts(identNr)
        assert cases[identNr] == whole_ident
        print(f"whole_for_parts: {identNr} -> {whole_ident}")
