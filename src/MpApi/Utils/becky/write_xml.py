"""
New interface to create xml for the uta application. It does not
depend on the becky generation of these function in set_fields_Object.py.

We perform xml operations and return a record (Module object) through the function
create_record which parses the configuration which contains a description of the
fields we want to work on, including callbacks that get called.


Usage:
    recordM, missing = create_record(conf=conf, row=row)

    We expect the template recordM sitting at conf["templateM"] and deep copy that in
    process so the original doesn't get modified.

    We also work on conf["fields2"] where we store a rewritten list of the fields from
    the toml configuration file.

    Then we call the callbacks for each field and return the completed new record as well
    as bool signaling if essential xml elements (fields) are missing.

    I wonder if we can and should simplify the use of missing. As it is reference, I guess
    dont need to explicitedly pass it around. On the other hand, I like to pass it around
    explicitly to show where it gets created and modified.

cluster :
    "weitereNr1" : {
        cb: "weitereNr",
        type: "set",
        fields: {
            "Bezeichnung": {"type":"constant", value:"Andere Nummer"},
            "weitereNr": {"type":"column", value: 10},
            "Bemerkung": {"type":"column", value: 11},
        }
    }
"""

from copy import deepcopy
import re
from lxml.etree import _Element
from mpapi.module import Module
from openpyxl.utils import column_index_from_string
from rich import print as rprint
from MpApi.Utils.becky.set_fields_Object import _sanitize
from MpApi.Utils.identNr import IdentNrFactory


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


def create_xml(*, conf: dict, row: tuple) -> tuple[Module, bool]:
    """
    We expect a configuration and the current row from the Excel file
    And return a full xml record ready for upload. The template object
    has to be at conf["templateM"].
    """

    if len(conf["templateM"]) != 1:
        raise TypeError("Template does not have a single record")

    recordM = deepcopy(conf["templateM"])  # currently we always begin with a template
    global missing
    missing = False  # if obligatory info is missing, the record will not be created

    for cluster in conf["fields2"]:
        print(f"DEBUG write_xml.py create records: {cluster=}")
        cb = conf["fields2"][cluster]["cb"]
        try:
            func = globals()[cb]
        except KeyError:
            raise ValueError(f"Unknown callback '{cb}'")
        func(recordM, cluster=conf["fields2"][cluster], row=row)
    recordM.uploadForm()  # we need that to delete ID
    recordM.sort_elements()
    p = conf["project_dir"] / "debug.object.xml"
    print(f">> Writing record to file '{p}'")
    recordM.toFile(path=p)
    print(">> Validating xml...")
    recordM.validate()
    print(">> Ok")
    print(f">> {missing=}")
    recordM.toFile(path="debug.create_xml.xml")
    if missing:
        raise SyntaxError("missing=True Let's stop here")
    return recordM, missing


#
# A
#


def AnzahlTeile(record: Module, *, cluster: dict, row: tuple) -> None:
    rprint("add_AnzahlTeile in write_xml not yet implemented")
    # return missing


def Aufschrift(record: Module, *, cluster: dict, row: tuple) -> None:
    """
    Assuming we can change missing here and dont need to return it explicitly
    """
    rprint("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!Aufschrift get here")
    global missing
    missing = True  # if we change it here, will it surive return?


#
# B
#


def BemerkungenSammlungen(record: Module, *, cluster: dict, row: tuple) -> None:
    pass
    # return missing


def Besitzart(record: Module, *, cluster: dict, row: tuple) -> None:
    pass
    # return missing


def Beteiligte(record: Module, *, cluster: dict, row: tuple) -> None:
    """
    Assuming we can change missing here and dont need to return it explicitly
    """
    # return missing
    pass


#
# D
#


def Datierung(record: Module, *, cluster: dict, row: tuple) -> None:
    pass
    # return missing


#
# E
#


def ErwerbDatum(record: Module, *, cluster: dict, row: tuple) -> None:
    pass
    # return missing


def ErwerbNotiz(record: Module, *, cluster: dict, row: tuple) -> None:
    pass
    # return missing


def Erwerbungsart(record: Module, *, cluster: dict, row: tuple) -> None:
    pass
    # return missing


#
# I
#


def identNr(record: Module, *, cluster: dict, row: tuple) -> None:
    """
    We take the str ident and in the rGrp ObjObjectNumberGrp, we create the following fields
    - InventarNrSTxt,
    - Part1Txt,
    - Part2Txt,
    - Part3Txt,
    - Part4Txt,
    - SortLnu,
    - DenominationVoc,
    - InvNumberSchemeRef

    But we're changing ObjObjectNumberTxt
        <dataField dataType="Varchar" name="ObjObjectNumberTxt">
          <value>III C 192</value>
        </dataField>

    Note: We are setting namespace now. Works better.
    """
    # rprint(f"yyyXXXXXXx{cluster=}")
    # how do I get the identNr from the row?
    col = cluster["fields"]["identNr"]["value"]

    ident = _sanitize(row[col].value)  # includes a .strip()
    rprint(f"DEUBG: write identNr {ident=} {col=}")
    institution = "AKu2"  # for identNr parser NOT SURE YET TODO
    # return missing
    # ObjObjectNumberGrp
    # let's not catch errors here because identNr is essential

    iFac = IdentNrFactory()
    iNr = iFac.new_from_str(text=ident, institution=institution)
    new_numberGrpN = iNr.get_node()

    if cluster["type"] == "set":
        _new_or_replace(
            record=record,
            xpath="//m:dataField[@name = 'ObjObjectNumberTxt']",
            newN=new_numberGrpN,
        )
    elif cluster["type"] == "add":
        _add(
            record=record,
            xpath="//m:dataField[@name = 'ObjObjectNumberTxt']",
            newN=new_numberGrpN,
        )
    else:
        raise TypeError(f"Unknown cluster type {cluster['type']}")


#
# M
#


def MaterialTechnik(recordM: Module, cluster: dict, row: tuple) -> None:
    pass
    # return missing


#
# O
#


def Objektreferenz(recordM: Module, *, cluster: dict, row: tuple) -> None:
    pass
    # return missing


#
# S
#


def Sachbegriff(recordM: Module, cluster: dict, row: tuple) -> None:
    pass
    # return missing


def Status(recordM: Module, cluster: dict, row: tuple) -> None:
    pass
    # return missing


def SystematikArt(recordM: Module, cluster: dict, row: tuple) -> None:
    pass
    # return missing


#
# T
#


def Titel(recordM: Module, cluster: dict, row: tuple) -> None:
    pass
    # return missing


#
# W
#


def weitereNr(recordM: Module, cluster: dict, row: tuple) -> None:
    pass
    # return missing


#
# Z
#


def Zugang(recordM: Module, cluster: dict, row: tuple) -> None:
    pass
    # return missing


##
## private
##


def _add(*, record: Module, xpath: str, newN: _Element) -> None:
    """
    We find an existing element and add a sibling.

    todo: test
    """
    oldN = record.xpath(xpath)[0]
    oldN.addnext(newN)


def _new_or_replace(*, record: Module, xpath: str, newN: _Element) -> None:
    """
    We replace an existing element defined by an xpath expression with a new node or, if
    it doesn't exist, we create a new node.

    Here we assume that there will be only one such node. So if there are multiple titles
    what happens?

    N.B. Order here is non-deterministic and does often not validate. use m.sort_elements()
    """
    try:
        oldN = record.xpath(xpath)[0]
    except IndexError:  # append
        parentN = record.xpath("//m:moduleItem")[0]
        parentN.append(newN)
    else:  # replace
        oldN.getparent().replace(oldN, newN)
