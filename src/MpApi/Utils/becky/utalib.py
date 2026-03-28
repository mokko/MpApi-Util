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

New:
Workflow where we log errors and dont create record with missing info, but run through

"""

import argparse
from copy import deepcopy
from datetime import datetime
import logging
from lxml import etree  # t y p e : i g n o r e

from mpapi.constants import get_credentials
from mpapi.module import Module
from mpapi.search import Search

from MpApi.Utils.Ria import RIA, init_ria, record_exists2, record_exists3
from MpApi.Utils.becky.write_xml import create_record
from MpApi.Utils.Xls import Xls
from openpyxl import Workbook, load_workbook, worksheet
from openpyxl.cell.cell import Cell
from openpyxl.styles.colors import Color
from pathlib import Path
import re
import tomllib

#
# CONFIGURATION
#

no_records_created = 0
verbose = 0  # false for off, true for on.


def dd(msg: str) -> None:
    """Debugging print messages"""

    if verbose:
        print(msg)


def create_record(*, row: tuple, conf: dict, act: bool) -> None:
    # print(">> Create record")
    missing_info = False
    ident_row = conf[fields]["identNr"]

    if len(conf["templateM"]) != 1:
        raise TypeError("Template does not have a single record")

    recordM = deepcopy(conf["templateM"])  # so we dont change the original template
    recordM = create_xml(recordM, conf[fields], row)
    print(f"DDD: {row[ident_row].value}")
    # set_ident(
    #    recordM, ident=row[ident_row].value, institution=conf["institution"]
    # )  # from Excel as str
    # set_ident_sort(recordM, nr=int(row[1].value))
    # set_sachbegriff(recordM, sachbegriff=row[2].value)
    # set_erwerbDatum(recordM, datum=row[4].value)
    # set_erwerbungsart(recordM, art=row[5].value)
    # set_erwerbNr(recordM, nr=row[6].value)
    # set_erwerbVon(recordM, von=row[7].value)
    # set_geogrBezug(recordM, name=row[8].value)
    # missing_info = set_beteiligte(
    #    recordM, beteiligte=row[3].value, conf=conf, missing_info=missing_info
    # )
    # set_invNotiz(recordM, bemerkung=row[11].value)  # Spalte L rarely filled-in
    # missing_info = set_objRefA(
    #    recordM, Vorgang=row[9].value, conf=conf, missing_info=missing_info
    # )

    # print(recordM)
    p = conf["project_dir"] / "debug.object.xml"
    print(f">> Writing record to file '{p}'")
    recordM.toFile(path=p)
    print(">> Validating xml...")
    recordM.validate()
    print(">> Ok")
    print(f">> {missing_info=}")
    if missing_info:
        msg = f"Not creating record in RIA '{row[ident_row].value}' since missing info"
        logging.error(msg)
        print(f">> {msg}")
        return missing_info
    if act:
        # we used to count also would-be created records without act
        global no_records_created
        no_records_created += 1
        objId = conf["RIA"].create_item(item=recordM)
        msg = f"Created record {objId} in RIA '{row[ident_row].value}'"
        logging.error(msg)
        print(f">> {msg}")
    else:
        print(f">> Not creating record in RIA '{row[2].value}' (since no act)")
        # p2 = conf["project_dir"] / f"debug.object{objId}.xml"
        # print(f">> Writing to '{p2}'")
        # recordM.toFile(path=p2)


def go_display_record(line_number: int, *, conf: dict, ws: worksheet):
    import sys
    from rich.console import Console

    console = Console()
    print(f">> Display record {line_number}")
    for field in conf["fields"]:
        console.print(f"[blue]{field}[reset]:")
        for subfield in conf["fields"][field]:
            value = conf["fields"][field][subfield]
            if is_excel_column(value):
                column = value
                coord = f"{column}{line_number}"
                if ws[coord].value is not None:
                    excel = ws[coord].value
                    console.print(
                        f"   [green]{subfield}[reset]: [yellow]{excel}[reset] [red]{column}[reset]"
                    )
                else:
                    console.print(
                        f"   [green]{subfield}[reset] [red]{column}[reset] empty cell"
                    )
            else:
                console.print(f'   [green]{subfield}[reset]: "{value}" constant')

    sys.exit(0)
    # raise Exception("Stop here")


def is_excel_column(s: str) -> bool:
    # Must be 1–3 uppercase letters only; highest column XFD.
    if not isinstance(s, str) or len(s) == 0 or len(s) > 3:
        return False
    if not s.isalpha() or not s.isupper():
        return False
    # Limit to valid Excel columns (A–XFD)
    return len(s) < 3 or s <= "XFD"


def init_log(*, act: bool, conf: dict, conf_fn: str, limit: int, offset: int) -> None:
    """
    Create a simple logger at file becky20250510-0956.log
    """
    # should we only log if we actually do something with act=True?
    # to avoid plethora of log files?
    if act is True:
        now = datetime.now()
        datetime_str = now.strftime("%Y%m%d-%H%M%S")
        log_fn = f"becky{datetime_str}.log"
        logging.basicConfig(
            filename=log_fn,
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        # - %(name)s is currently not necessary
        logger = logging.getLogger(__name__)
        logger.info(f"becky started with {act=}, {offset=} and {limit=}")
        logger.info(f"loading Excel file '{conf['excel_fn']}'")
    else:
        logger = logging.getLogger(__name__)
        logger.addHandler(logging.NullHandler())


def log_print_info(msg: str) -> None:
    """
    log and print info message simultaneously
    """
    logger = logging.getLogger(__name__)
    logger.info(msg)
    print(f"   {msg}")


def per_row(*, idx: int, row: Cell, conf: dict, act: bool) -> None:
    ident_row = conf[fields]["identNr"]
    ident = row[ident_row].value  # from Excel as str

    if ident is None:
        logging.warning(f"IdentNr is None {idx}; not processing this line")
        return
    # font_color = row[0].font.color
    # if font_color and font_color.rgb == "FFFF0000":  # includes the alpha channel
    global no_records_created
    print(f"***[{no_records_created}]{idx}: {ident}")
    # record_exists2 is Hendryk's algorithm that uses schemata and fortlaufende Nummer
    # if m := record_exists2(ident=ident, conf=conf):
    # record_exists3 omits Bereich and simply uses IdentNr and exact match.
    if m := record_exists3(ident=ident, conf=conf):
        # Wollen wir hier Fehler loggen um Nachzuvollziehen, wo die Infos aus Excel
        # nicht eingetragen wurden? Nein. Nur loggen, wenn etwas in RIA verändert wird
        print(f"INFO Record '{ident}' exists already")
    else:
        create_record(row=row, conf=conf, act=act)
        if m > 1:
            logging.warning(
                f"Multiple identNr: More than one IdentNr exists already with this number {ident}"
            )


def uta_main(
    *,
    conf_fn: str,
    act: bool = False,
    limit: int = -1,
    offset: int = 2,
    display_record: int | None,
) -> None:
    conf = _load_conf(conf_fn)  # sets project_dir
    print(f">> Setting project_dir '{conf['project_dir']}'")

    wb = load_workbook(conf["excel_fn"], read_only=True)
    ws = wb[conf["sheet_title"]]  # sheet exists already

    if display_record:
        go_display_record(display_record, conf=conf, ws=ws)

    conf["RIA"] = init_ria()  # mpApi.util.Ria's client
    init_log(act=act, conf=conf, conf_fn=conf_fn, limit=limit, offset=offset)
    print(f">> Getting template from RIA Object {conf['template_id']}")
    conf["templateM"] = conf["RIA"].get_template(ID=conf["template_id"], mtype="Object")
    conf["templateM"]._dropFieldsByName(element="systemField", name="__uuid")
    conf["templateM"]._dropAttribs(xpath="//m:moduleItem", attrib="id")

    for idx, row in enumerate(ws.iter_rows(min_row=conf["excel_row_offset"]), start=2):
        dd(f"{idx=} {offset=}")
        if idx < offset:
            continue
        per_row(idx=idx, row=row, conf=conf, act=act)
        if limit == idx:
            print(f">> Limit reached {limit}")
            break


#
# more private
#


def _load_conf(conf_fn: str) -> dict:
    print(f">> Reading configuration '{conf_fn}'")
    with open(Path(conf_fn), "rb") as toml_file:
        conf = tomllib.load(toml_file)
    conf["project_dir"] = Path(__file__).parents[4] / "sdata"  # project_dir
    return conf
