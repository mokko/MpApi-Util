"""
Several functions that expect a Module object with a full record and rewrite/overwrite
specific elements given an appropriate value, typically of type str.

Set refers here to the following process: If there is a field already, overwrite it. If
there is none, we create it.

We don't use return values here, but rather change the record in place (reference)
"""

from lxml import etree
from lxml.etree import _Element
from mpapi.module import Module
from MpApi.Utils.identNr import IdentNrFactory


def set_beteiligte(recordM: Module, *, beteiligte: str) -> None: ...


def set_ident(record: Module, *, ident: str, institution: str) -> None:
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

    Why dont I need to set the namespace?
    """
    # ObjObjectNumberGrp
    ident = ident.strip()
    iFac = IdentNrFactory()
    iNr = iFac.new_from_str(text=ident, institution=institution)
    new_numberGrpN = iNr.get_node()
    _new_or_replace(
        record=record,
        xpath="//m:repeatableGroup[@name = 'ObjObjectNumberGrp']",
        newN=new_numberGrpN,
    )

    # ObjObjectNumberTxt
    newN = etree.fromstring(f"""
        <dataField name="ObjObjectNumberTxt">
          <value>{ident}</value>
        </dataField>
    """)
    _new_or_replace(
        record=record, xpath="//m:dataField[@name = 'ObjObjectNumberTxt']", newN=newN
    )


def set_ident_sort(record: Module, *, nr: int) -> None:
    """
    Setting ObjObjectNumberSortedTxt
    """
    print(f"{nr=}")
    newN = etree.fromstring(f"""
        <dataField name="ObjObjectNumberSortedTxt">
            <value>0003 C {nr:05d}</value>
        </dataField>
    """)
    _new_or_replace(
        record=record,
        xpath="//m:dataField[@name = 'ObjObjectNumberSortedTxt']",
        newN=newN,
    )


def set_erwerbDatum(recordM: Module, *, datum: str) -> None: ...


def set_erwerbNr(recordM: Module, *, nr: str) -> None: ...


def set_erwerbungsart(recordM: Module, *, art: str) -> None: ...


def set_erwerbVon(recordM: Module, *, von: str) -> None: ...


def set_geogrBezug(recordM: Module, *, name: str) -> None: ...


def set_objRefA(recordM: Module, *, keineAhnung: str) -> None: ...


def set_sachbegriff(record: Module, *, sachbegriff: str) -> None:
    """
    We're filling in/overwriting 
    - dataField: ObjTechnicalTermClb and 
    - repeatableGroup: ObjTechnicalTermGrp

    We will NOT fill this out
    <virtualField name="ObjObjectVrt">
      <value>1234567, Pfeile, Testdatensatz für Kamerun-Projekt (Template/Vorlage)</value>
    </virtualField>
    """
    print("{sachbegriff=}")

    newN = etree.fromstring(f"""
        <dataField name="ObjTechnicalTermClb">
          <value>{sachbegriff}</value>
        </dataField>
    """)
    _new_or_replace(
        record=record, xpath="//m:dataField[@name = 'ObjTechnicalTermClb']", newN=newN
    )

    newN = tree.fromstring(f"""
        <repeatableGroup name="ObjTechnicalTermGrp">
          <repeatableGroupItem>
            <dataField name="TechnicalTermTxt">
              <value>{sachbegriff}</value>
            </dataField>
            <dataField name="TechnicalTermMultipleBoo">
              <value>true</value>
            </dataField>
            <dataField name="NotesClb">
              <value>vereinfachter Sachbegriff aus Hauptkatalog (Kamerumn2023)</value>
            </dataField>
            <dataField name="SortLnu">
              <value>1</value>
            </dataField>
          </repeatableGroupItem>
        </repeatableGroup>
    """)
    _new_or_replace(
        record=record,
        xpath="//m:repeatableGroup[@name = 'ObjTechnicalTermClb']",
        newN=newN,
    )

    try:
        ObjTechnicalTermN = record.xpath(
            "//m:repeatableGroup[@name = 'ObjObjectNumberGrp']"
        )[0]
    except KeyError:
        mItemN = record.xpath("//m:moduleItem")[0]
        mItemN.append(new_ObjTechnicalTermN)
    else:
        ObjTechnicalTermN.getparent().replace(ObjTechnicalTermN, new_ObjTechnicalTermN)

    print(f"{sachbegriff=}")


#
# private: not meant for export
#


def _new_or_replace(*, record: Module, xpath: str, newN: _Element) -> None:
    """
    We replace an existing element defined by an xpath expression with a new node or, if
    it doesn't exist, we create a new node.

    Here we assume that there will be only one such node. So if there are multiple titles
    what happens?
    """
    try:
        oldN = record.xpath(xpath)[0]
    except KeyError:
        parentN = record.xpath("//m:moduleItem")[0]
        parentN.append(newN)
    else:
        oldN.getparent().replace(oldN, newN)
