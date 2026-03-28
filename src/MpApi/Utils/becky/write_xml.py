"""
Unified interface to create xml for the becky/uta application

We perform xml operations and return a record (Module object)

Usage:
    recordM = create_record(xml, template, fields, row)

"""

import re
from mpapi.module import Module
# from MpApi.Utils.becky.make_fields (
#    set_beteiligte,
#    set_erwerbDatum,
#    set_erwerbungsart,
#    set_erwerbNr,
#    set_erwerbVon,
#    set_geogrBezug,
#    set_ident,
#    set_ident_sort,
#    set_invNotiz,
#    set_objRefA,
#    set_sachbegriff,
# )


def set_beteiligte(record: Module, cell: str):
    pass


def add_beteiligte(record: Module, cell: str):
    pass


def create_record(templateM: Module, fields: dict, row: list) -> Module:
    recordM = templateM  # currently we always begin with a template
    for field in fields:
        print(f"DEBUG create records: {field}")
        recordM = field_router(recordM, field, cell)

    recordM.uploadForm()  # we need that to delete ID
    recordM.sort_elements()
    return recordM


def field_router(recordM: Module, field: str, cell: str) -> Module:
    """
    We route the field to the right function that generates xml
    """
    field2, no = field_splitter(field)
    match (field2, no):
        case ("beteiligte", 1):
            xml = set_beteiligte(recordM, cell)
        case ("beteiligte", no) if no > 1:
            print("Case 2")
            xml = add_beteiligte(recordM, cell)
    return recordM


def field_splitter(field: str) -> tuple[str, int]:
    """
    Split off trailing number and return both separately. If number doesn't exist, return field name as is and a 0.
    """
    match = re.match(r"(.*?)(\d+)$", field)
    if match:
        field2, no = match.groups()
        return field2, no
    else:
        return field, 0
