import argparse
from datetime import datetime
import logging
from lxml import etree  # t y p e : i g n o r e

from mpapi.constants import get_credentials
from mpapi.module import Module
from mpapi.search import Search

from MpApi.Utils.Ria import RIA, init_ria, record_exists2, record_exists3
from MpApi.Utils.becky.write_xml import create_xml
from MpApi.Utils.Xls import Xls
from openpyxl import Workbook, load_workbook, worksheet
from openpyxl.cell.cell import Cell
from openpyxl.styles.colors import Color
from openpyxl.utils import column_index_from_string
from pathlib import Path
import re
from rich import print as rprint
import tomllib

#
# CONFIGURATION
#

no_records_created = 0
verbose = 0  # false for off, true for on.


def cluster_splitter(label: str) -> tuple[str, int]:
    """
    for a given cluster label, split off trailing number and return both separately.
    If number doesn't exist, return field name as is and a 0.

    So technically speaking we have no proper and inproper cluster labels. And the
    toml config uses improper cluster names. Improper refers to the number at the
    end that now gets translated to the add/set type.
    """
    match = re.match(r"(.*?)(\d+)$", label)
    if match:
        label2, no = match.groups()
        return label2, int(no)
    else:
        return label, 0


def create_callback(name: str) -> str:
    """
    We receive the name of field from the configuration toml file and return the
    name of the Python function we want to call.
    """
    (name2, no) = cluster_splitter(name)
    # print(f"++create callback {name2=}")
    return name2


def create_record(*, row: tuple, conf: dict, act: bool) -> None:
    # print(">> Create record")
    # missing_info = False NOT HERE
    # ident_col = conf["fields"]["identNr"]["identNr"]

    recordM, missing_info = create_xml(conf=conf, row=row)
    ident = get_ident(conf, row)  # for messages
    print(f"DDD: {ident}")

    # print(recordM)
    if missing_info:
        msg = f"Not creating record in RIA '{ident}' since missing info"
        logging.error(msg)
        print(f">> {msg}")
    elif act:
        # we used to count also would-be created records without act
        global no_records_created
        no_records_created += 1
        objId = conf["RIA"].create_item(item=recordM)
        msg = f"Created record {objId} in RIA '{ident}'"
        logging.error(msg)
        print(f">> {msg}")
    else:
        print(f">> Not creating record in RIA '{ident}' (since no act)")

    # raise Exception("utalib.py: create_record - Stop here!")


def dd(msg: str) -> None:
    """Debugging print messages"""

    if verbose:
        print(msg)


def decide_type(label: str) -> str:
    """
    For a given cluster label or name, return the type "add" or "set".

    add adds another xml element with the same name keeping the existing one.
    set overwrites existing elements of that name and replaces them with given item.
    """
    (label2, no) = cluster_splitter(label)
    # print(f"{name2=}{no=}")
    if no <= 1:  # can be 0
        return "set"
    elif no > 1:
        return "add"


def get_ident(conf: dict, row: list) -> str | None:
    """
    Assuming you defined a cluster identNr with the field identNr, this returns the identNr
    for the current row. Returns None if cell value is None and if cell is empty ("").

    Do we still need this? Do we want to generalize it?
    """

    ident_col = column_index_from_string(conf["fields"]["identNr"]["identNr"]) - 1
    ident = row[ident_col].value  # from Excel as str
    # rprint(f"{ident_col=} {ident=}")
    if ident is None:
        raise TypeError(f"{ident=} {ident_col}")
        logging.warning(f"IdentNr is None; not processing this line")
        return None
    if ident == "":
        raise TypeError(f"{ident=} {ident_col}")
        logging.warning(f"IdentNr is empty; not processing this line")
        return None
    return ident


def go_display_record(line_number: int, *, conf: dict, ws: worksheet):
    import sys
    from rich.console import Console

    console = Console()
    print(f">> Display record {line_number}")
    for cluster in conf["fields"]:
        console.print(f"[blue]{cluster}[reset]:")
        for field in conf["fields"][cluster]:
            value = conf["fields"][cluster][field]
            if is_excel_column(value):
                column = value
                coord = f"{column}{line_number}"
                if ws[coord].value is not None:
                    excel = ws[coord].value
                    console.print(
                        f"   [green]{field}[reset]: [yellow]{excel}[reset] [red]{column}[reset]"
                    )
                else:
                    console.print(
                        f"   [green]{field}[reset] [red]{column}[reset] empty cell"
                    )
            else:
                console.print(f'   [green]{field}[reset]: "{value}" constant')

    # TODO temporary: exits the process so the half-finished display path can be
    # tried out without running the import. Replace with a plain return, and put
    # the return at the call site in uta_main, where the mode is chosen — a
    # function that ends the interpreter cannot be called from a test or from
    # another tool, and exits 0 as if something had been done.
    sys.exit(0)
    # raise Exception("Stop here")


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


def is_excel_column(s: str) -> bool:
    """
    Test if a string is an Excel column (e.g. AAA) or just a regular string.
    Columns must be 1–3 uppercase letters only; highest column XFD.
    """
    if not isinstance(s, str) or len(s) == 0 or len(s) > 3:
        return False
    if not s.isalpha() or not s.isupper():
        return False
    return len(s) < 3 or s <= "XFD"


def log_print_info(msg: str) -> None:
    """
    log and print info message simultaneously
    """
    logger = logging.getLogger(__name__)
    logger.info(msg)
    print(f"   {msg}")


def per_row(*, idx: int, row: Cell, conf: dict, act: bool) -> None:
    # rprint(conf["fields"])
    ident = get_ident(conf, row)  # should it die on no ident? Die early?

    # font_color = row[0].font.color
    # if font_color and font_color.rgb == "FFFF0000":  # includes the alpha channel
    global no_records_created
    print(f"***[{no_records_created}]{idx}: {ident}")
    # record_exists2 is Hendryk's algorithm that uses schemata and fortlaufende Nummer
    # if m := record_exists2(ident=ident, conf=conf):
    # record_exists3 omits Bereich and simply uses IdentNr and exact match.
    n = record_exists3(ident=ident, conf=conf)
    if n == 0:
        print(f"INFO Record '{ident}' DOES NOT YET exist")  # low priority message
        create_record(row=row, conf=conf, act=act)
    elif n == 1:
        # Wollen wir hier Fehler loggen um Nachzuvollziehen, wo die Infos aus Excel
        # nicht eingetragen wurden? Nein. Nur loggen, wenn etwas in RIA verändert wird
        print(f"INFO Record '{ident}' exists already")
    else:
        logging.warning(
            f"{n} records already carry IdentNr '{ident}' — not creating another"
        )


def prepare_fields(conf: dict) -> None:
    """
    Rewrite the fields so we have less work later. I am not sure when to do this. At
    this point early in the game it's efficient because we only have to do this part
    once. But then we will have to do the next part later. If we only do it later, we
    can do it for indivdual cells and we only have to do it once.

    Coming back to this months later. Why dont we do the columns and constants and other
    values here? Doesn't make sense and looks old-school perlish. Aha. At this point,
    we only have the config file. We cant know the contents of the excel yet. But we
    need only convert column letter to number. So now we have all the processing in one
    place.
    """
    conf["fields2"] = {}
    for cluster in conf["fields"]:
        print(f"c:{cluster}")
        conf["fields2"][cluster] = {
            "cb": create_callback(cluster),
            "type": decide_type(cluster),
            "fields": {},
        }

        for field in conf["fields"][cluster]:
            if is_excel_column(conf["fields"][cluster][field]):
                atype = "column"
                value = column_index_from_string(conf["fields"][cluster][field]) - 1
            else:
                atype = "constant"
                value = conf["fields"][cluster][field]

            conf["fields2"][cluster]["fields"][field] = {
                "type": atype,
                "value": value,
            }

    rprint("Debugging prepare_fields")
    rprint(conf["fields2"])
    # raise SyntaxError("Stop here")


def prepare_template(conf: dict) -> Module:
    """
    Get the template record from RIA and rewrite it to approximate upload form.
    """
    print(f">> Getting template from RIA Object {conf['template_id']}")
    templateM = conf["RIA"].get_template(ID=conf["template_id"], mtype="Object")
    templateM._dropFieldsByName(element="systemField", name="__uuid")
    templateM._dropAttribs(xpath="//m:moduleItem", attrib="id")
    return templateM


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
    conf["templateM"] = prepare_template(conf)

    prepare_fields(conf)

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
