"""
We read Becky's excel, parse it for names etc., look them up in RIA and write the
results in the cache file.
"""

import argparse
from mpapi.constants import get_credentials
from mpapi.search import Search
from MpApi.Utils.becky.becky import _load_conf
from MpApi.Utils.becky.cache_ops import (
    open_archive_cache,
    open_person_cache,
    save_person_cache,
    save_archive_cache,
)
from MpApi.Utils.becky.set_fields_Object import _each_person
from MpApi.Utils.Ria import RIA, init_ria
from openpyxl import Workbook, load_workbook, worksheet
from pathlib import Path


def main(conf_fn: str, mode: str, limit: int = -1) -> None:
    conf = _load_conf(conf_fn)

    print(">> Reading workbook")
    wb = load_workbook(conf["excel_fn"], data_only=True)
    ws = wb[conf["sheet_title"]]  # sheet exists already
    match mode:
        case "person":
            update_persons(conf=conf, sheet=ws, limit=limit)
        case "archive":
            update_archive(conf=conf, sheet=ws, limit=limit)
        case _:
            raise SyntaxError(f"Unknown mode '{mode}'")


def process_names(*, beteiligte: str, cache: dict) -> dict:
    if beteiligte is None:
        return cache  # it's perfectly possible that a cell is empty...
    for count, (name, role) in enumerate(_each_person(beteiligte), start=1):
        # we're counting the names in one cell here, not the lines
        # print(f"{count}:{name} [{role}]")
        # if role not in roles:
        #    roles.add(role)
        if name not in cache:
            print(f">> Name not yet in cache {name}")
            cache[name] = []
    return cache


def query_archives(*, ident: str, client: RIA) -> list:
    """
    For a given archive ident (eg. E 1012/1898), return the id or ids.

    If there is no such record, returns empty list.
    """
    if ident is None:
        #it's purrfectly allowed for an Excel cell to be empty
        return list()
    else:
        archive_ident = ident.strip()
        q = Search(module="Object", limit=-1, offset=0)
        q.AND()
        q.addCriterion(
            operator="equalsField",  # notEqualsTerm
            field="__orgUnit",  # __orgUnit is not allowed in Zetcom's own search.xsd
            value="EMArchiv",
        )
        q.addCriterion(
            field="ObjObjectNumberVrt",
            operator="equalsField",
            value=archive_ident,
        )
        q.addField(field="__id")
        q.validate(mode="search")  # raises if not valid
        m = client.mpapi.search2(query=q)
        return m.get_ids(mtype="Object")


def query_persons(*, name: str, client: RIA) -> list:
    q = Search(module="Person", limit=-1, offset=0)
    # q.AND()
    q.addCriterion(
        field="PerNennformTxt",
        operator="equalsField",
        value=name,
    )
    q.addField(field="__id")
    q.validate(mode="search")  # raises if not valid
    m = client.mpapi.search2(query=q)
    # print(m)
    return m.get_ids(mtype="Person")


def update_archive(*, conf: dict, sheet: worksheet, limit: int) -> None:
    print(f">> Loading archive cache '{conf["archive_cache"]}'")
    archive_data = open_archive_cache(conf)
    print(">> Looping thru excel looking for archival documents' idents")
    client = init_ria()
    for idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
        # print(f"Line {idx}")
        objRefA = row[9].value
        font_color = row[9].font.color  # relying on red font
        if font_color and font_color.rgb == "FFFF0000":  # includes the alpha channel
            if objRefA not in archive_data:
                print(f">> querying archives '{objRefA}'")
                idL = query_archives(ident=objRefA, client=client)
                archive_data[objRefA] = idL
        if idx % 25 == 0:
            save_archive_cache(data=archive_data, conf=conf)
        if limit == idx:
            save_archive_cache(data=archive_data, conf=conf)
            print(">> Limit reached")
            break
    save_archive_cache(data=archive_data, conf=conf)


def update_persons(*, conf: dict, sheet: worksheet, limit: int) -> None:
    print(f">> Loading person cache '{conf["person_cache"]}'")
    person_data = open_person_cache(conf)

    print(">> Looping thru excel looking for names")
    for idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
        # print(f"Line {idx}")
        person_data = process_names(beteiligte=row[3].value, cache=person_data)
        if idx % 200 == 0:
            save_person_cache(data=person_data, conf=conf)
        if limit == idx:
            print(">> Limit reached")
            break

    save_person_cache(data=person_data, conf=conf)

    client = init_ria()
    print(">> Unidentified names?")
    for idx, name in enumerate(person_data, start=1):
        if not person_data[name]:  # if tuple is empty
            idL = query_persons(client=client, name=name)
            person_data[name] = idL
            print(idL)
        if idx % 25 == 0:
            save_person_cache(data=person_data, conf=conf)
        if limit == idx:
            print(">> Limit reached")
            break
    save_person_cache(data=person_data, conf=conf)


#
# script
#


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("conf", help="Location of becky_conf.toml")
    parser.add_argument(
        "-l",
        "--limit",
        help="Stop after a number of rows in Excel file are processed.",
        type=int,
    )
    parser.add_argument(
        "-m",
        "--mode",
        type=str,
        help="Pick which cache(s) to update.",
        choices=["person", "archive"],
    )
    args = parser.parse_args()
    main(conf_fn=args.conf, limit=args.limit, mode=args.mode)
