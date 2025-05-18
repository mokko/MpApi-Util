"""
Rewriting existing records
    from copy import deepcopy
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
        set_invNotiz,
        set_objRefA,
    )
    from MpApi.Utils.Ria import RIA, init_ria

    ria = init_ria()
    templateM = ria.get_template(ID=123456, mtype="Object")
    recordM = deepcopy(templateM) # record should contain only one moduleItem
    set_ident(recordM, ident="III c 123", institution = "EM")

Several functions that expect a Module object with a full record and rewrite/overwrite
specific elements given an appropriate value, typically of type str.

Set refers here to the following process: If there is a field overwrite it; otherwise
create it with given value.

We don't use return values here, but rather change the record in place (reference)

TODO
Do we need to check if arguments are empty? Where is that test?

"""

import logging
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

"""
Für alle manuellen Indexe gilt:
- Wenn ein unbekannter Begriff in den Daten auftaucht, bricht das Programm ab. Soll auch Fehler loggen.
- Wenn ein Begriff in diesem Index eine Null erhält (auch 000000), bleibt das Feld in RIA leer.  
- Sollen wir das auch loggen? Wohl ja, denn dann hat man nachträglich die Chance, die Daten (manuell) 
  zu korrigieren
- Brauchen wir den None-Eintrag? Nein.
"""


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
    "Nachlass (Vermächtnis) / Kauf": 1630990,
    "Pfändung": 1630992,
    "Restitution": 1630993,
    "Rückgewinnung": 2737042,
    "Schenkung": 1630994,
    "Tausch": 1630995,
    "Übertrag ": 000000,
    "Übereignung": 4129997,
    "Überweisung": 1630996,
    "Zugang ungeklärt": 1631000,
    "Zugang ungeklärt (Expedition)": 1631001,
}


NS = "xmlns='http://www.zetcom.com/ria/ws/module'"


def set_beteiligte(recordM: Module, *, beteiligte: str, conf: dict) -> None:
    """
    setting ObjPerAssociationRef
    """
    if _is_space_etc(beteiligte):
        return None

    print(f"{beteiligte=}")

    mRefN = etree.fromstring(
        f"<moduleReference {NS} name='ObjPerAssociationRef' targetModule='Person'/>"
    )

    for count, (name, role) in enumerate(_each_person(beteiligte), start=1):
        if count == 1:
            sort = 1
        elif count > 1:
            sort = (count - 1) * 5

        nameID = _lookup_name(name=name, conf=conf)  # raises if unknown
        roleID = _lookup_role(role)  # raises if not part of index
        print(f"{count} {sort} {name} [{role}] {nameID=} {roleID=}")
        xml = f"""
            <moduleReferenceItem {NS} moduleItemId="{nameID}">
              <dataField dataType="Long" name="SortLnu">
                <value>{sort}</value>
              </dataField>"""
        # do we really need the None test?
        if roleID == 0:
            # Untested ...
            # at this point there is no objId yet, but we can use IdentNr instead
            identNr = recordM.xpath("""
                //m:application/m:modules/m:module/m:moduleItem[1]/m:repeatableGroup[
                    @name eq 'ObjObjectNumberGrp'
                ]/m:repeatableGroupItem/m:dataField[
                    @name = 'InventarNrSTxt']""")
            logger = logging.getLogger(__name__)
            logger.warning(f"null role for {identNr=} with {beteiligte=}")
        else:
            xml += f"""
              <vocabularyReference name="RoleVoc" id="30423" instanceName="ObjPerAssociationRoleVgr">
                <vocabularyReferenceItem id="{roleID}"/>
              </vocabularyReference>"""
        xml += """
            </moduleReferenceItem>"""

        mRefItemN = etree.fromstring(xml)
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

    if _is_space_etc(str(datum)):
        return None

    print(f"Erwerb.datum={datum}")
    quelle = "Hauptkatalog / #KP24"
    newN = etree.fromstring(f"""
        <repeatableGroup {NS} name="ObjAcquisitionDateGrp">
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
    if _is_space_etc(nr):
        return None

    print(f"erwerbNr='{nr}'")
    newN = etree.fromstring(f"""
        <dataField {NS} name="ObjAcquisitionReferenceNrTxt">
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
    if _is_space_etc(art):
        return None

    global erwerbungsarten
    try:
        artID = erwerbungsarten[art]
    except IndexError:
        raise IndexError(f"Erwerbungsart unbekannt: '{art}'")
    print(f"Erwerbungsart='{art}' {artID=}")
    bemerkung = "#KP24"

    xml = f"""
        <repeatableGroup {NS} name="ObjAcquisitionMethodGrp">
          <repeatableGroupItem>
            <dataField name="NotesClb">
              <value>{bemerkung}</value>
            </dataField>"""
    if artID != 0:
        xml += f"""
            <vocabularyReference name="MethodVoc" id="62639" >
               <vocabularyReferenceItem id="{artID}"/>
            </vocabularyReference>
        """
    xml += """
          </repeatableGroupItem>
        </repeatableGroup>
    """

    newN = etree.fromstring(xml)

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
    if _is_space_etc(von):
        return None

    print(f"ErwerbungVon '{von}'")
    newN = etree.fromstring(f"""
    <repeatableGroup {NS} name="ObjAcquisitionNotesGrp">
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
    TODO: parameterize souce and notes.

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
    if _is_space_etc(name):
        return None

    print(f"geogrBezug {name=}")
    newN = etree.fromstring(f"""
        <virtualField {NS} name="ObjGeograficVrt">
          <value>{name}</value>
        </virtualField>
    """)
    _new_or_replace(
        record=recordM,
        xpath="//m:virtualField[@name = 'ObjGeograficVrt']",
        newN=newN,
    )

    source = "Hauptkatalog"
    notes = "Eintrag erstellt im Projekt #KP24"
    # placeID = _lookup_place(name)
    # assuming that there is only one item in the Excel always
    # instanceName="GenPlaceVgr"
    newN = etree.fromstring(f"""
        <repeatableGroup {NS} name="ObjGeograficGrp">
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

    Why dont I need to set the namespace? Doing that now. See if RIA likes it.
    """
    # ObjObjectNumberGrp
    if _is_space_etc(ident):
        return None

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
        <dataField {NS} name="ObjObjectNumberTxt">
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
    if not _is_int(nr):
        return None

    print(f"{nr=}")

    newN = etree.fromstring(f"""
        <dataField {NS} name="ObjObjectNumberSortedTxt">
            <value>0003 C {nr:05d}</value>
        </dataField>
    """)
    _new_or_replace(
        record=record,
        xpath="//m:dataField[@name = 'ObjObjectNumberSortedTxt']",
        newN=newN,
    )


def set_invNotiz(record: Module, bemerkung: str) -> None:
    """
    UNTESTED
    z.B. "Kein geographischer Bezug genannt" (Zeile 16255 im Excel)

    <repeatableGroup name="ObjEditorNotesGrp" size="1">
      <repeatableGroupItem id="42033280" uuid="0983f3b6-ecb5-4f5b-bba1-6d901ff766c8">
        <dataField dataType="Clob" name="NotesClb">
          <value>GeoBezug, Ansetzung angepasst</value>
        </dataField>
        <dataField dataType="Long" name="SortLnu">
          <value>5</value>
          <formattedValue language="de">5</formattedValue>
        </dataField>
        <vocabularyReference name="TypeVoc" id="61661" instanceName="ObjEditorNotesTypeVgr">
          <vocabularyReferenceItem id="4407670" name="Redaktionelle Notiz">
            <formattedValue language="de">Redaktionelle Notiz</formattedValue>
          </vocabularyReferenceItem>
        </vocabularyReference>
      </repeatableGroupItem>
    </repeatableGroup>
    4407671 = InventarNotiz
    """
    if _is_space_etc(bemerkung):
        return None

    newN = etree.fromstring(f"""
    <repeatableGroup {NS} name="ObjEditorNotesGrp">
      <repeatableGroupItem>
        <dataField dataType="Clob" name="NotesClb">
          <value>{bemerkung}</value>
        </dataField>
        <dataField dataType="Long" name="SortLnu">
          <value>5</value>
        </dataField>
        <vocabularyReference name="TypeVoc" id="61661" instanceName="ObjEditorNotesTypeVgr">
          <vocabularyReferenceItem id="4407671"/> 
        </vocabularyReference>
      </repeatableGroupItem>
    </repeatableGroup>
    """)

    _new_or_replace(
        record=recordM,
        xpath="//m:repeatableGroup[@name = 'ObjEditorNotesGrp']",
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
    if _is_space_etc(Vorgang):
        return None

    Vorgang = Vorgang.strip()
    print(f"objRefA {Vorgang=}")
    global archive_data
    if not archive_data:
        archive_data = open_archive_cache(conf)
    if Vorgang not in archive_data:
        raise TypeError(f"Archival document not in cache '{Vorgang}'")

    rel_objId = archive_data[Vorgang][0]

    newN = etree.fromstring(f"""
        <composite {NS} name="ObjObjectCre">
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
      <value>1234567, Pfeile, Testdatensatz für #KP24 (Template/Vorlage)</value>
    </virtualField>
    """
    if _is_space_etc(sachbegriff):
        return None

    print(f"{sachbegriff=}")

    # Sachbegriff Ausg
    newN = etree.fromstring(f"""
        <dataField {NS} name="ObjTechnicalTermClb">
          <value>{sachbegriff}</value>
        </dataField>
    """)
    _new_or_replace(
        record=record, xpath="//m:dataField[@name = 'ObjTechnicalTermClb']", newN=newN
    )

    newN = etree.fromstring(f"""
        <repeatableGroup {NS} name="ObjTechnicalTermGrp">
          <repeatableGroupItem>
            <dataField name="TechnicalTermTxt">
              <value>{sachbegriff}</value>
            </dataField>
            <dataField name="TechnicalTermMultipleBoo">
              <value>true</value>
            </dataField>
            <dataField name="NotesClb">
              <value>vereinfachter Sachbegriff aus Hauptkatalog (#KB24)</value>
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


def _is_int(value: int | None) -> bool:
    """
    Expects int or None. Returns True if is an integer or False otherwise.

    TODO: Test if it dies on error.
    """
    if not isinstance(value, int) and not value is None:
        raise TypeError(f"Value should be int|None, but it's not! {value}")

    match value:
        case None:
            return False
        case int():
            return True
        case _:
            return False


def _is_space_etc(value: str | None) -> bool:
    """
    Expects a string or None. Returns True if value is None or an empty string ('') or
    an de facto empty string (e.g. ' '). Otherwise return False.

    Currently, dies if you pass in an int instead of an str which is good behavior since it
    points to a problem we should be aware of.

    TODO: tests
    """

    if not isinstance(value, str) and not value is None:
        raise TypeError(f"Value should be str|None, but it's not! {value}")

    match value:
        case None | "":
            return True
        case value if value.isspace():
            return True
        case _:
            return False


def _lookup_name(*, name: str, conf: dict) -> int:
    """
    Lookup that returns the ids for a given name in the cache.

    Note it is possible that one name has multiple entries, hence we
    always return a tuple which often contains only one hit.

    For cases where there are  multiple records for one name,
    raise TypeError and log. (We used to silently take the first name record.)

    Raises TypeError if name not in cache.
    May return 0 if a name known to the cache has no valid equivalent in RIA.


    """
    global person_data
    logger = logging.getLogger(__name__)
    if not person_data:  # cache empty
        person_data = open_person_cache(conf)

    try:
        atuple = person_data[name]
    except KeyError:
        logger.error(f"Person not in cache! '{name}'")
        raise TypeError(f"Person not in cache! '{name}'")

    if len(atuple) > 1:
        logger.error(f"Ambiguous person name in cache! '{name}'")
        raise TypeError(f"Ambiguous person name in cache! '{name}'")
    return atuple[0]


def _lookup_place(*, name: str, conf: dict) -> int:
    """
    Not used at the moment
    """
    global geo_data
    logger = logging.getLogger(__name__)
    if not geo_data:
        geo_data = open_geo_cache(conf)
    try:
        return geo_data[name]
    except KeyError:
        logger.ERROR(f"Unbekannte Ort: '{name}'")
        raise TypeError(f"Unbekannter Ort: '{name}'!")


def _lookup_role(role: str) -> int:
    """
    Would only return None if that is a value in the index and that values should not be used
    in the index.
    Use 0 oder 000000 instead if you want to keep the field empty in RIA.
    """

    global roles
    logger = logging.getLogger(__name__)
    try:
        return roles[role]
    except KeyError:
        logger.ERROR(f"Unbekannte Rolle: '{role}'")
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
    except IndexError:  # append
        parentN = record.xpath("//m:moduleItem")[0]
        parentN.append(newN)
    else:  # replace
        oldN.getparent().replace(oldN, newN)
