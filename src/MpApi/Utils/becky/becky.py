"""
Script to import records from Excel for Kamerun project

Fields that have to fill in
- IdentNr
- Sachbegriff
- Beteiligte + Rolle
- Erwerb.Datum
- Erwerbungsart
- Erwerb. Nr.
- Erwerbung von
- Geogr. Bezug
- Obj. Referenz A
fraglich
- Obj. Referenz B
- Inventarnotiz

Todo:
- Why dont we need to provide a namespace?
- Put the template record into a group ("Kamerun 2024"), so all created records are in a group
"""

import argparse
from copy import deepcopy
from lxml import etree  # t y p e : i g n o r e

from mpapi.constants import get_credentials
from mpapi.module import Module
from mpapi.search import Search

from MpApi.Utils.Ria import RIA, init_ria
from MpApi.Utils.becky.set_fields_Object import (
    set_ident,
    set_ident_sort,
    set_sachbegriff,
    set_beteiligte,
    set_erwerbDatum,
    set_erwerbungsart,
    set_erwerbNr,
    set_erwerbVon,
    set_geogrBezug,
    set_objRefA,
)
from MpApi.Utils.Xls import Xls
from openpyxl import Workbook, load_workbook, worksheet
from openpyxl.cell.cell import Cell
from openpyxl.styles.colors import Color
from pathlib import Path
import tomllib

#
# CONFIGURATION
#


def becky_main(*, conf_fn: str, act: bool = False, limit: int = -1) -> None:
    conf = _load_conf(conf_fn)
    conf["project_dir"] = Path(__file__).parents[4] / "sdata"  # project_dir
    print(f">> Setting project_dir '{conf['project_dir']}'")

    wb = load_workbook(conf["excel_fn"], data_only=True)
    ws = wb[conf["sheet_title"]]  # sheet exists already

    conf["RIA"] = init_ria()

    print(f">> Getting template from RIA Object {conf['template_id']}")
    conf["templateM"] = conf["RIA"].get_template(ID=conf["template_id"], mtype="Object")

    for idx, row in enumerate(ws.iter_rows(min_row=conf["excel_row_offset"]), start=2):
        per_row(idx=idx, row=row, conf=conf, act=act)
        if limit == idx:
            print(">> Limit reached")
            break


def create_record(*, row: tuple, conf: dict, act: bool) -> None:
    # print(">> Create record")

    if len(conf["templateM"]) != 1:
        raise TypeError("Template does not have a single record")

    recordM = deepcopy(conf["templateM"])  # so we dont change the original template
    recordM
    set_ident(
        recordM, ident=row[0].value, institution=conf["institution"]
    )  # from Excel as str
    set_ident_sort(recordM, nr=int(row[1].value))
    set_sachbegriff(recordM, sachbegriff=row[2].value)
    set_beteiligte(recordM, beteiligte=row[3].value, conf=conf)
    set_erwerbDatum(recordM, datum=row[4].value)
    set_erwerbungsart(recordM, art=row[5].value)
    set_erwerbNr(recordM, nr=row[6].value)
    set_erwerbVon(recordM, von=row[7].value)
    set_geogrBezug(recordM, name=row[8].value)
    set_objRefA(recordM, keineAhnung=row[9].value)

    # print(recordM)
    recordM.uploadForm()  # we need that to delete ID
    p = conf["project_dir"] / "debug.object.xml"
    print(f">> Writing to '{p}'")
    recordM.toFile(path=p)
    if act:
        objId = conf["RIA"].create_item(item=recordM)
        print(f">> Created record {objId} in RIA ({row[0].value})")
        p2 = conf["project_dir"] / f"debug.object{objId}.xml"
        print(f">> Writing to '{p2}'")
        recordM.toFile(path=p2)


def per_row(*, idx: int, row: Cell, conf: dict, act: bool) -> None:
    ident = row[0].value  # from Excel as str
    font_color = row[0].font.color
    if font_color and font_color.rgb == "FFFF0000":  # includes the alpha channel
        print(f"{idx}: {ident} red")
        if record_exists(ident=ident, conf=conf):
            print(f"   Record '{ident}' exists already")
        else:
            create_record(row=row, conf=conf, act=act)


def record_exists(*, ident: str, conf: dict) -> bool:
    """
    Check ria if a record with a specific identNr exists. It's not relevant if one or
    multiple results exist.
    N.B. This search is not exact.
    """
    q = Search(module="Object", limit=-1, offset=0)
    q.AND()
    q.addCriterion(
        field="ObjObjectNumberVrt",
        operator="equalsField",
        value=str(ident),
    )
    q.addCriterion(field="__orgUnit", operator="equalsField", value=conf["org_unit"])
    q.addField(field="__id")
    q.validate(mode="search")  # raises if not valid
    m = conf["RIA"].mpapi.search2(query=q)
    if len(m) > 1:
        raise TypeError("Warning! more than one result in record_exists")
    if m:
        return True
    else:
        return False


#
# more private
#


def _load_conf(conf_fn: str) -> dict:
    print(f">> Reading configuration '{conf_fn}'")
    with open(Path(conf_fn), "rb") as toml_file:
        conf = tomllib.load(toml_file)
    return conf
