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
from MpApi.Utils.becky.cache_ops import (
    open_person_cache,
    save_person_cache,
    open_archive_cache,
    save_archive_cache,
)
from pathlib import Path
import re
import tomllib
from typing import Iterator

person_data = {}
geo_data = {}
archive_data = {}

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

    for count, (name, role) in enumerate(_each_person(beteiligte), start=1):
        if count > 1:
            count = (count - 1) * 5

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
    set ObjAcquisitionReferenceNrTxt
    """
    print(f"erwerbNr='{nr}'")
    newN = etree.fromstring(f"""
        <dataField name="ObjAcquisitionReferenceNrTxt">
          <value>{nr}</value>
        </dataField>
    """)
    _new_or_replace(
        record=recordM,
        xpath="//m:dataField[@name = 'ObjAcquisitionReferenceNrTxt']",
        newN=newN,
    )


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
    print(f"Erwerbungsart='{art}' {artID=}")
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
    I have the impression we shouldn't write to the field erwerbVon. Instead it goes to
    erwerbNotit or similar. TODO: confirm before I do anything.
    instanceName="ObjAcquisitionNotesTypeVgr"

    3570719 = Erwerbung von


    """
    print(f"ErwerbungVon '{von}'")
    newN = etree.fromstring(f"""
    <repeatableGroup name="ObjAcquisitionNotesGrp">
      <repeatableGroupItem>
        <dataField name="MemoClb">
          <value>{von}</value>
        </dataField>
        <dataField name="SortLnu">
          <value>1</value>
        </dataField>
        <vocabularyReference name="TypeVoc" id="62641">
          <vocabularyReferenceItem id="3570719"/>
        </vocabularyReference>
      </repeatableGroupItem>
    </repeatableGroup>
    """)
    _new_or_replace(
        record=recordM,
        xpath="//m:repeatableGroup[@name = 'ObjAcquisitionNotesGrp']",
        newN=newN,
    )


def set_geogrBezug(recordM: Module, *, name: str) -> None:
    """
    virtualField/@ObjGeograficVrt

    <virtualField name="ObjGeograficVrt">
      <value>Berlin</value>
    </virtualField>

    <repeatableGroup name="ObjGeograficGrp" size="1">
      <repeatableGroupItem>
        <dataField name="DetailsTxt">
          <value>Berlin (Deutschland)</value>
        </dataField>
      </repeatableGroupItem>
    </repeatableGroup>
    """

    print(f"geogrBezug {name=}")
    newN = etree.fromstring(f"""
        <virtualField name="ObjGeograficVrt">
          <value>{name}</value>
        </virtualField>
    """)
    _new_or_replace(
        record=recordM,
        xpath="//m:virtualField[@name = 'ObjGeograficVrt']",
        newN=newN,
    )

    source = "Hauptkatalog"
    notes = "Eintrag erstellt im Projekt Kamerun 2024"
    # placeID = _lookup_place(name)
    # assuming that there is only one item in the Excel always
    # instanceName="GenPlaceVgr"
    newN = etree.fromstring(f"""
        <repeatableGroup name="ObjGeograficGrp">
          <repeatableGroupItem>
            <dataField name="SourceTxt">
              <value>{source}</value>
            </dataField>
            <dataField name="NotesClb">
              <value>{notes}</value>
            </dataField>
            <dataField dataType="Long" name="SortLnu">
              <value>1</value>
            </dataField>
            <dataField name="DetailsTxt">
              <value>{name}</value>
            </dataField>
          </repeatableGroupItem>
        </repeatableGroup>
    """)
    _new_or_replace(
        record=recordM,
        xpath="//m:repeatableGroup[@name = 'ObjGeograficGrp']",
        newN=newN,
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


def set_objRefA(recordM: Module, *, Vorgang: str, conf: dict) -> None:
    """
    seqNo="0"
    <formattedValue language="de">Vorgang: E 362/1844, Erwerbung: III/8/1909: III A 2667, 2668, Dolch, Axt, (Kordofan), Schenkung Werne (übertragen von III B 2 + 3 -- eigentl. betr. EJ Kunstkammer: Nr. 2105: III A [12-183 203, 204], III E [1-2] -- General Secret. Dielitz vom 23.02.1844,über die durch den Prof. Lepsius angekaufte Wernesch(e) Sammlung ethnographischer Gegenstände aus dem oberen Nil Stromgebiete., 1844, Ferdinand Werne (3.8.1800 - 2.9.1874)</formattedValue>
    @name?
    E 362/1844: objId 225082

    4399791 Vorgang
    4399760 Object
    """
    Vorgang = Vorgang.strip()
    print(f"objRefA {Vorgang=}")
    global archive_data
    if not archive_data:
        archive_data = open_archive_cache(conf)
    if Vorgang not in archive_data:
        raise TypeError(f"Archival document not in cache '{Vorgang}'")

    rel_objId = archive_data[Vorgang][0]

    newN = etree.fromstring(f"""
        <composite name="ObjObjectCre">
          <compositeItem >
            <moduleReference name="ObjObjectARef" targetModule="Object">
              <moduleReferenceItem moduleItemId="{rel_objId}">
                <vocabularyReference name="TypeAVoc" id="30413">
                  <vocabularyReferenceItem id="4399791"/>
                </vocabularyReference>
                <vocabularyReference name="TypeBVoc" id="30413">
                  <vocabularyReferenceItem id="4399760"/>
                </vocabularyReference>
                <vocabularyReference name="PreselectTypeAVoc">
                  <vocabularyReferenceItem id="4399760"/>
                </vocabularyReference>
                <vocabularyReference name="PreselectTypeBVoc">
                  <vocabularyReferenceItem id="4399791"/>
                </vocabularyReference>
              </moduleReferenceItem>
            </moduleReference>
          </compositeItem>
        </composite>
    """)
    _new_or_replace(
        record=recordM,
        xpath="//m:composite[@name = 'ObjObjectCre']",
        newN=newN,
    )


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
        person_data = open_person_cache(conf)

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


def _lookup_place(*, name: str, conf: dict) -> int:
    """
    Not used at the moment
    """
    global geo_data
    if not geo_data:
        geo_data = open_geo_cache(conf)
    try:
        return geo_data[name]
    except KeyError:
        raise TypeError(f"Unbekannter Ort: '{name}'!")


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
