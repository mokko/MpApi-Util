from MpApi.Utils.logic import extractIdentNr
from pathlib import Path

cases = {
    "I_MV_0401__0001.tif": "I/MV 0401",
    "I_MV_0950_a__0290.jpg": "I/MV 0950 a",
    "VII a 123 c-KK.tif": "VII a 123 c",
    "VII c 86 a -A x.tif": "VII c 86 a",
    "VII c 86 a <1>-A x.tif": "VII c 86 a <1>",
    "HK_Afr_1__0001.jpg": "HK Afr 1",
    "HK_AmArch_1__0001.jpg": "HK AmArch 1",
    "HK_AmEth_32__0001.jpg": "HK AmEth 32",
    "HK_ISL_9__0001.jpg": "HK ISL 9",
    "HK_ONA_2__0100.jpg": "HK ONA 2",
    "HK_SOA_24__0024.jpg": "HK SOA 24",
    "HK_SUA_1__0001.jpg": "HK SUA 1",
    "HK_VIII_1__0001.jpg": "HK VIII 1",
    "Inv_1__0001.jpg": "Inv 1",
    "Verz_BGAEU_1__0001.jpg": "Verz. BGAEU 1",
    # objId as IdentNr doesn't work atm
    "220222": "220222",
}


def test_extractIdent():
    for case in cases:
        case = Path(case)
        identNr = extractIdentNr(path=case)
        print(f"{case} -> {identNr}")
        assert cases[str(case)] == identNr
