from MpApi.Utils.logic import extractIdentNr
from pathlib import Path

cases = {
    "I_MV_0401__0001.tif": "I/MV 0401",
    "VII a 123 c-KK.tif": "VII a 123 c",
    "VII c 86 a -A x.tif": "VII c 86 a",
    "VII c 86 a <1>-A x.tif": "VII c 86 a <1>",
}


def test_extractIdent():
    for case in cases:
        case = Path(case)
        identNr = extractIdentNr(path=case)
        print(f"{case} -> {identNr}")
        assert cases[str(case)] == identNr
