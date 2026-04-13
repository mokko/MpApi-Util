"""
Unified interface to create xml for the becky/uta application

We perform xml operations and return a record (Module object)

Usage:
    recordM = create_record(template, fields=fields, row=row)

"""

from copy import deepcopy
import re
from mpapi.module import Module
from openpyxl.utils import column_index_from_string
from rich import print as rprint

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


def add_Aufschrift(record: Module, cluster: dict, missing: bool) -> bool:
    """
    Assuming we can change missing here and dont need to return it explicitly
    """
    return missing


def set_Aufschrift(record: Module, cluster: dict, missing: bool) -> bool:
    rprint(f"XXXXXXXXXXx{cluster=}")
    return missing


def add_Beteiligte(record: Module, cluster: dict, missing: bool) -> bool:
    """
    Assuming we can change missing here and dont need to return it explicitly
    """
    return missing


def set_Beteiligte(record: Module, cluster: dict, missing: bool) -> bool:
    rprint(f"XXXXXXXXXXx{cluster=}")
    return missing


def add_Datierung(recordM: Module, cluster: dict, missing: bool) -> bool:
    return missing


def set_Datierung(recordM: Module, cluster: dict, missing: bool) -> bool:
    return missing


def add_identNr(recordM: Module, cluster: dict, missing: bool) -> bool:
    return missing


def set_identNr(recordM: Module, cluster: dict, missing: bool) -> bool:
    return missing


def add_MaterialTechnik(recordM: Module, cluster: dict, missing: bool) -> bool:
    return missing


def set_MaterialTechnik(recordM: Module, cluster: dict, missing: bool) -> bool:
    return missing


def add_weitereNr(recordM: Module, cluster: dict, missing: bool) -> bool:
    return missing


def set_weitereNr(recordM: Module, cluster: dict, missing: bool) -> bool:
    return missing


def add_Sachbegriff(recordM: Module, cluster: dict, missing: bool) -> bool:
    return missing


def set_Sachbegriff(recordM: Module, cluster: dict, missing: bool) -> bool:
    return missing


def add_Titel(recordM: Module, cluster: dict, missing: bool) -> bool:
    missing = True
    return missing


def set_Titel(recordM: Module, cluster: dict, missing: bool):
    return missing


#
#
#
def create_xml(*, conf: dict, row: tuple) -> tuple[Module, bool]:
    """
    We expect a configuration and the current row from the Excel file
    And return a full xml record ready for upload. The template object
    has to be at conf["templateM"].
    """

    if len(conf["templateM"]) != 1:
        raise TypeError("Template does not have a single record")

    recordM = deepcopy(conf["templateM"])  # currently we always begin with a template
    missing = False  # if obligatory info is missing, the record will not be created

    # We can make a cell/cluster object here
    # cluster: label
    # fields: label, column, type

    for cluster in conf["fields2"]:
        print(f"DEBUG create records: {cluster=}")
        for field in conf["fields2"][cluster]:
            if field == "_cb":
                continue
            # rprint(f"   {field=} {conf['fields2'][cluster]=}")
            value = ""
            if "col" in conf["fields2"][cluster][field]:
                col = conf["fields2"][cluster][field]["col"]
                value = row[column_index_from_string(col) - 1].value  # str | None
            else:
                value = conf["fields2"][cluster][field]["constant"]
            conf["fields2"][cluster][field]["value"] = value
        # rprint(f"{conf['fields2'][cluster]=}")
        cb = conf["fields2"][cluster]["_cb"]
        try:
            func = globals()[cb]
        except KeyError:
            raise ValueError(f"Unknown callback '{cb}'")
        missing = func(recordM, cluster=conf["fields2"][cluster], missing=missing)
    recordM.uploadForm()  # we need that to delete ID
    recordM.sort_elements()
    p = conf["project_dir"] / "debug.object.xml"
    print(f">> Writing record to file '{p}'")
    recordM.toFile(path=p)
    print(">> Validating xml...")
    recordM.validate()
    print(">> Ok")
    print(f">> {missing=}")
    return recordM, missing
