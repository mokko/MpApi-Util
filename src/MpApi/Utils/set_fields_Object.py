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
from MpApi.Utils.person_cache import open_cache, save_cache
from pathlib import Path
import re
import tomllib
from typing import Iterator

person_data = {}

roles = {
    "Absender*in": 4378273,
    "Auftraggeber*in": 4378279,
    "Auktionator*in": 4378280,
    "Aussteller*in": 4378283,
    "Besitzer*in des Originals": 4378291,
    "Bildhauer*in": 4378292,
    "Dargestellt": 4378298,
    "ehemalige*r Eigentümer*in": 4378304,
    "ehemalige*r Leihgeber*in": 4378305,
    "Eigentümer*in": 4378308,
    "Entwerfer*in": 4378312,
    "Expedition": 4378317,
    "Expeditionsleiter*in": 4378319,
    "Fotograf*in": 4378324,
    "Gutachter*in": 4378341,
    "Hersteller*in": 4378345,
    "Hersteller & Produzent": 4378346,
    "Linolschneider*in": 4378391,
    "Maler*in": 4378349,
    "Maler*in des Originals": 4378397,
    "Mäzen*atin": 4378399,
    "Nachlasser*in": 4378407,
    "Objektkünstler*in": 4378410,
    "Sammler*in": 4378427,
    "Sammler*in des Originals": 4378428,
    "Schnitzer*in": 4378432,
    "Treuhänder*in": 4378446,
    "Veräußerung": 4378452,
    "Vermittler*in": 4378460,
    "Vorbesitzer*in": 4378466,
    "Vorsänger*in": 4378470,
    "Zeichner*in": 4378474,
}

erwerbungsarten = {
    "Auktion": 1630981,
    "Beschlagnahmung": 1630982,
    "Kauf": 1630987,
    "Kommission": 1630988,
    "Leihe": 1630989,
    "Nachlass/Vermächtnis": 1630990,
    "Pfändung": 1630992,
    "Restitution": 1630993,
    "Rückgewinnung": 2737042,
    "Schenkung": 1630994,
    "Übereignung": 4129997,
    "Überweisung": 1630996,
    "Zugang ungeklärt": 1631000,
    "Zugang ungeklärt (Expedition)": 1631001,
}


def set_beteiligte(recordM: Module, *, beteiligte: str, conf: dict) -> None:
    """
    setting ObjPerAssociationRef
    """
    print(f"{beteiligte=}")

    mRefN = etree.fromstring(
        "<moduleReference name='ObjPerAssociationRef' targetModule='Person'/>"
    )

    for count, (name, role) in enumerate(
        _each_person(beteiligte), start=1
    ):  # enumerate(, start=1):
        nameID = _lookup_name(name=name, conf=conf)
        roleID = _lookup_role(role)
        print(f"{count} {name} [{role}] {nameID=} {roleID=}")
        mRefItemN = etree.fromstring(f"""
            <moduleReferenceItem moduleItemId="{nameID}">
              <dataField dataType="Long" name="SortLnu">
                <value>{count}</value>
              </dataField>
              <vocabularyReference name="RoleVoc" id="30423" instanceName="ObjPerAssociationRoleVgr">
                <vocabularyReferenceItem id="{roleID}"/>
              </vocabularyReference>
            </moduleReferenceItem>""")
        mRefN.append(mRefItemN)

    _new_or_replace(
        record=recordM,
        xpath="//m:moduleReference[@name = 'ObjPerAssociationRef']",
        newN=mRefN,
    )


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


def set_erwerbDatum(recordM: Module, *, datum: str) -> None:
    """
    ObjAcquisitionDateGrp

    N.B. Whe I requested to use dataField[@name = 'ObjAcquisitionDateGrp'], RIA didnn't
    delete old entries from the template.
    """
    print(f"Erwerb.datum={datum}")
    quelle = "Hauptkatalog / Kamerun 2024"
    newN = etree.fromstring(f"""
        <repeatableGroup name="ObjAcquisitionDateGrp">
          <repeatableGroupItem>
            <dataField name="DateToTxt">
              <value>{datum}</value>
            </dataField>
            <dataField name="SourceTxt">
              <value>{quelle}</value>
            </dataField>
            <dataField name="SortLnu">
              <value>1</value>
            </dataField>
            <virtualField name="PreviewVrt">
              <value>{datum}</value>
            </virtualField>
          </repeatableGroupItem>
        </repeatableGroup>
    """)
    _new_or_replace(
        record=recordM,
        xpath="//m:repeatableGroup[@name = 'ObjAcquisitionDateGrp']",
        newN=newN,
    )


def set_erwerbNr(recordM: Module, *, nr: str) -> None:
    """
    TODO
    """
    print(f"{nr=}")


def set_erwerbungsart(recordM: Module, *, art: str) -> None:
    """
    ObjAcquisitionMethodGrp

    instanceName="ObjAcquisitionMethodVgr"
    """
    global erwerbungsarten
    try:
        artID = erwerbungsarten[art]
    except IndexError:
        raise IndexError(f"Erwerbungsart unbekannt: '{art}'")
    print(f"Erwerbungsart={art} {artID=}")
    bemerkung = "Kamerun 2024"

    newN = etree.fromstring(f"""
        <repeatableGroup name="ObjAcquisitionMethodGrp">
          <repeatableGroupItem>
            <dataField name="NotesClb">
              <value>{bemerkung}</value>
            </dataField>
          <vocabularyReference name="MethodVoc" id="62639" >
            <vocabularyReferenceItem id="{artID}"/>
          </vocabularyReference>
          </repeatableGroupItem>
        </repeatableGroup>
    """)
    _new_or_replace(
        record=recordM,
        xpath="//m:repeatableGroup[@name = 'ObjAcquisitionMethodGrp']",
        newN=newN,
    )


def set_erwerbVon(recordM: Module, *, von: str) -> None:
    """
    TODO
    """
    print(f"{von=}")


def set_geogrBezug(recordM: Module, *, name: str) -> None:
    """
    TODO
    """
    print(f"geogrBezug {name=}")


def set_objRefA(recordM: Module, *, keineAhnung: str) -> None:
    """
    TODO
    """
    print(f"objRefA {keineAhnung=}")


def set_sachbegriff(record: Module, *, sachbegriff: str) -> None:
    """
    We're filling in/overwriting
    - dataField: ObjTechnicalTermClb (Sachbegriff Ausg.) and
    - repeatableGroup: ObjTechnicalTermGrp (Sachbegriff Cluster)

    We will NOT fill this out
    <virtualField name="ObjObjectVrt">
      <value>1234567, Pfeile, Testdatensatz für Kamerun-Projekt (Template/Vorlage)</value>
    </virtualField>
    """
    print(f"{sachbegriff=}")

    # Sachbegriff Ausg
    newN = etree.fromstring(f"""
        <dataField name="ObjTechnicalTermClb">
          <value>{sachbegriff}</value>
        </dataField>
    """)
    _new_or_replace(
        record=record, xpath="//m:dataField[@name = 'ObjTechnicalTermClb']", newN=newN
    )

    newN = etree.fromstring(f"""
        <repeatableGroup name="ObjTechnicalTermGrp">
          <repeatableGroupItem>
            <dataField name="TechnicalTermTxt">
              <value>{sachbegriff}</value>
            </dataField>
            <dataField name="TechnicalTermMultipleBoo">
              <value>true</value>
            </dataField>
            <dataField name="NotesClb">
              <value>vereinfachter Sachbegriff aus Hauptkatalog (Kamerun 2024)</value>
            </dataField>
            <dataField name="SortLnu">
              <value>1</value>
            </dataField>
          </repeatableGroupItem>
        </repeatableGroup>""")

    _new_or_replace(
        record=record,
        xpath="//m:repeatableGroup[@name = 'ObjTechnicalTermGrp']",
        newN=newN,
    )


#
# private: not meant for export
#


def _each_person(beteiligte: str) -> Iterator[tuple[str, str]]:
    """
    - We split the string at ";"
    - We assume the role is the thing before the last comma
    - We ignore Zusätze in front of ":"
    - and things like Lebensdaten in brackets
    """
    exceptions = [  # name_roles with a comma, but no role
        "Erwähnung: Musée Ribauri - Art Primitif, Ethnographie, Haute Epoque, Curiosités (1964/1965)",
        "Königliche Preußische Kunstkammer, Ethnografische Abteilung (1801 - 1873)",
    ]

    if beteiligte is not None:
        beteiligteL = beteiligte.split(";")
        for name_role in beteiligteL:
            name_role = name_role.strip()
            if name_role in exceptions:
                name = name_role
                role = None
            elif "," in name_role:
                partsL = name_role.split(",")
                name = ",".join(partsL[:-1]).strip()
                role = partsL[-1].strip()
            else:
                name = name_role
                role = None
            # cut off the dates in brackets
            name = name.split("(")[
                0
            ].strip()  # returns list with orignal item if not split

            # cut off the remarks in the beginning
            try:
                name = name.split(":")[1].strip()
            except IndexError:
                pass

            yield (name, role)


def _lookup_name(*, name: str, conf: dict) -> int | None:
    global person_data
    if not person_data:  # cache empty
        person_data = open_cache(conf)

    try:
        atuple = person_data[name]  # currently ALWAYS using first name
    except KeyError:
        # production should use raise, development may warn
        raise TypeError(f"Person not in cache! '{name}'")
        # print(f">> WARN Person not in cache! '{name}'")

    if len(atuple) > 0:
        return atuple[0]
    else:
        return None


def _lookup_role(role: str) -> int:
    global roles
    try:
        return roles[role]
    except KeyError:
        raise TypeError(f"Unbekannte Rolle: '{role}'!")


def _new_or_replace(*, record: Module, xpath: str, newN: _Element) -> None:
    """
    We replace an existing element defined by an xpath expression with a new node or, if
    it doesn't exist, we create a new node.

    Here we assume that there will be only one such node. So if there are multiple titles
    what happens?
    """
    try:
        oldN = record.xpath(xpath)[0]
    except IndexError:  # KeyError,
        parentN = record.xpath("//m:moduleItem")[0]
        parentN.append(newN)
    else:
        oldN.getparent().replace(oldN, newN)
