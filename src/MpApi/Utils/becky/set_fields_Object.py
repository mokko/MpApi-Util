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
import xml.sax.saxutils as saxutils
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
    "Aktenvermerk": 4378276,
    "Auftraggeber*in": 4378279,
    "Auktionator*in": 4378280,
    "Aussteller*in": 4378283,
    "Bearbeiter*in der Sache": 4378290,
    "Besitzer*in des Originals": 4378291,
    "Bildhauer*in": 4378292,
    "Dargestellt": 4378298,
    "ehemalige*r Eigentümer*in": 4378304,
    "ehemalige*r Leihgeber*in": 4378305,
    "Eigentümer*in": 4378308,
    "Empfänger*in": 4378309,
    "Entwerfer*in": 4378312,
    "Expedition": 4378317,
    "Expeditionsleiter*in": 4378319,
    "Fotograf*in": 4378324,
    "Gutachter*in": 4378341,
    "Hersteller*in": 4378345,
    "Hersteller & Produzent": 4378346,
    "Kauf": 4378369,  # Käufer*in
    "Linolschneider*in": 4378391,
    "Maler*in": 4378349,
    "Maler*in des Originals": 4378397,
    "Mäzen*atin": 4378399,
    "Nachlasser*in": 4378407,
    "Notiz": 4378408,
    "Objektkünstler*in": 4378410,
    "Sammler*in": 4378427,
    "Sammler*in des Originals": 4378428,
    "Schnitzer*in": 4378432,
    "Treuhänder*in": 4378446,
    "Übernahme": 4378452,  # fake entry. id of veräußerung
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
    "Nachlass (Vermächtnis)": 1630990,
    "Nachlass/Vermächtnis": 1630990,
    "Nachlass (Vermächtnis) / Kauf": 1630990,
    "Pfändung": 1630992,
    "Restitution": 1630993,
    "Rückgewinnung": 2737042,
    "Schenkung": 1630994,
    "Tausch": 1630995,
    "Übertrag ": 000000,
    "Übernahme": 1805388,  # this is red, not sure this is working
    "Übereignung": 4129997,
    "Überweisung": 1630996,
    "Zugang ungeklärt": 1631000,
    "Zugang ungeklärt (Expedition)": 1631001,
}


prefix_cache = {
    "Erwähnung": 4399883,
    "frühere Zuschreibung": 4399885,
    "Zuordnung unsicher": 4399923,
    "zugeschrieben": 4399922,
}

NS = "xmlns='http://www.zetcom.com/ria/ws/module'"


def set_beteiligte(
    recordM: Module, *, beteiligte: str, conf: dict, missing_info: bool
) -> bool:
    """
    setting ObjPerAssociationRef. the input parameter beteiligte is the string from
    Excel. That string typically includes a date (in brackets) and a role.
    """
    try:
        beteiligteL = _sanitize_multi(beteiligte)
    except (ValueError, TypeError):
        return missing_info

    # print(f"++++++++++{beteiligteL=}")

    mRefN = etree.fromstring(
        f"<moduleReference {NS} name='ObjPerAssociationRef' targetModule='Person'/>"
    )

    for count, beteiligte in enumerate(beteiligteL, start=1):
        prefix, name, date, role = _quad_split(beteiligte)
        logger = logging.getLogger(__name__)
        if count == 1:
            sort = 1
        elif count > 1:
            sort = (count - 1) * 5
        # should raise if no kueId or name not in cache
        try:
            nameID = _lookup_name(name=name, conf=conf)
        except KeyError:
            missing_info = True
            msg = f"no ID for pk '{name}'"
            logger.error(msg)
            # print(msg)
            nameID = None
            # raise SyntaxError(f"no ID for pk '{name}'")
            # no new beteiligte*r for this entry
            # continue
        roleID = _lookup_role(role)  # raises if not part of index
        print(f"{count} {sort} {name} [{role}] {nameID=} {roleID=}")
        xml = f"""
            <moduleReferenceItem {NS} moduleItemId="{nameID}">
              <dataField dataType="Long" name="SortLnu">
                <value>{sort}</value>
              </dataField>"""
        # do we really need the None test?
        if role is None or roleID == 0:
            # at this point there is no objId yet, but we can use IdentNr instead
            identNr = _ident_from_record(recordM)
            logger.warning(f"null role for {identNr=} with {beteiligte=}")
        else:
            xml += f"""
              <vocabularyReference name="RoleVoc" id="30423" instanceName="ObjPerAssociationRoleVgr">
                <vocabularyReferenceItem id="{roleID}"/>
              </vocabularyReference>"""
        if prefix is not None:
            prefixID = prefix_cache[prefix]
            xml += f"""
              <vocabularyReference name="AttributionVoc" id="30422" instanceName="ObjPerAssociationAttributionVgr">
                <vocabularyReferenceItem id="{prefixID}"/>
              </vocabularyReference>  
            """

        xml += """
            </moduleReferenceItem>"""

        mRefItemN = etree.fromstring(xml)
        mRefN.append(mRefItemN)

    _new_or_replace(
        record=recordM,
        xpath="//m:moduleReference[@name = 'ObjPerAssociationRef']",
        newN=mRefN,
    )
    return missing_info


def set_erwerbDatum(recordM: Module, *, datum: int | str | None) -> None:
    """
    ObjAcquisitionDateGrp. When datum is None, we write usual entry but with
    empty string ("") for the actual date.

    New:
    - When datum was None, we used to stringify that to None. We dont want
    that.
    - When datum was None, we used to do nothing, but instead, we should overwrite
      the existing entry with empty string ("")
    - Apprently, openpyxl returns int sometimes. Account for that.
    """

    if isinstance(datum, int):
        datum = str(datum)
    try:
        datum = _sanitize(datum)
    except (TypeError, ValueError):
        return None

    print(f"Erwerb.datum={datum}")
    quelle = "Hauptkatalog / #ETB04"
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
    try:
        nr = _sanitize(nr)
    except (TypeError, ValueError):
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
    try:
        art = _sanitize(art)
    except (TypeError, ValueError):
        return None

    global erwerbungsarten
    try:
        artID = erwerbungsarten[art]
    except KeyError:
        # raise KeyError(f"Erwerbungsart unbekannt: '{art}'")
        logging.warning(f"KeyError: Erwerbungsart unbekannt: '{art}'")
    print(f"Erwerbungsart='{art}' {artID=}")
    bemerkung = "#ETB04"

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
    try:
        von = _sanitize(von)
    except (TypeError, ValueError):
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

    N.B. name can be a string that contains multiple entries separated by ;

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
    try:
        namesL = _sanitize_multi(name)
    except (TypeError, ValueError):
        return None

    print(f"geogrBezug {name=}")  # can be multiple names; names

    # Multiple should look like:
    # <virtualField name="ObjGeograficVrt">
    #   <value>Togo; Kabure</value>
    # </virtualField>
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
    notes = "Eintrag erstellt im Projekt #ETB04"
    # placeID = _lookup_place(name)
    # we used to assume that there is only one item in the Excel always
    # instanceName="GenPlaceVgr"
    newN = etree.fromstring(f"""
        <repeatableGroup {NS} name="ObjGeograficGrp"/>
    """)

    for idx, name2 in enumerate(namesL):
        name3 = saxutils.escape(name2)
        idx = idx * 5
        itemN = etree.fromstring(f"""
            <repeatableGroupItem {NS}>
                <dataField name="SourceTxt">
                  <value>{source}</value>
                </dataField>
                <dataField name="NotesClb">
                  <value>{notes}</value>
                </dataField>
                <dataField dataType="Long" name="SortLnu">
                  <value>{idx}</value>
                </dataField>
                <dataField name="DetailsTxt">
                  <value>{name3}</value>
                </dataField>
                <vocabularyReference name="TypeVoc" id="52617" instanceName="ObjGeographicTypeVgr">
                  <vocabularyReferenceItem id="4366951">
                  </vocabularyReferenceItem>
                </vocabularyReference>
            </repeatableGroupItem>""")
        newN.append(itemN)

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

    Note: We are setting namespace now. Works better.
    """
    # ObjObjectNumberGrp
    ident = _sanitize(ident)
    # let's not catch errors here because ident is essential

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
    try:
        nr = _sanitize(nr)
    except (TypeError, ValueError):
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


def set_invNotiz(recordM: Module, bemerkung: str) -> None:
    """
    make a new entry in Notizen Inv. / Red. with type "Inventarnotiz" if none exists
    or overwrite existing entry with string in bemerkung.

    z.B. "Kein geographischer Bezug genannt" (Zeile 16255 im Excel)
    4407670 Redaktionelle Notiz
    4407671 Inventarnotiz
    """
    # one hardcoded redakt. Notiz in any case
    xml = f"""
    <repeatableGroup {NS} name="ObjEditorNotesGrp">
          <repeatableGroupItem>
            <dataField dataType="Clob" name="NotesClb">
              <value>Dieser Datensatz wurde im Projekt #ErfassungsturboB04 erstellt.</value>
            </dataField>
            <dataField dataType="Long" name="SortLnu">
              <value>5</value>
            </dataField>
            <vocabularyReference name="TypeVoc" instanceName="ObjEditorNotesTypeVgr">
              <vocabularyReferenceItem id="4407670"/> 
            </vocabularyReference>
          </repeatableGroupItem>
    """

    try:
        bemerkung = _sanitize(bemerkung)
    except (TypeError, ValueError):
        pass
        # return None
    else:  # if try succeeds
        print(f"invNotiz='{bemerkung}'")

        xml += f"""
          <repeatableGroupItem>
            <dataField dataType="Clob" name="NotesClb">
              <value>{bemerkung}</value>
            </dataField>
            <dataField dataType="Long" name="SortLnu">
              <value>10</value>
            </dataField>
            <vocabularyReference name="TypeVoc" instanceName="ObjEditorNotesTypeVgr">
              <vocabularyReferenceItem id="4407671"/> 
            </vocabularyReference>
          </repeatableGroupItem>"""

    finally:  # in any case
        xml += """
        </repeatableGroup>
        """
        _new_or_replace(
            record=recordM,
            xpath="//m:repeatableGroup[@name = 'ObjEditorNotesGrp']",
            newN=etree.fromstring(xml),
        )


def set_objRefA(
    recordM: Module, *, Vorgang: str, conf: dict, missing_info: bool
) -> bool:
    """
    seqNo="0"
    <formattedValue language="de">Vorgang: E 362/1844, Erwerbung: III/8/1909: III A 2667, 2668, Dolch, Axt, (Kordofan), Schenkung Werne (übertragen von III B 2 + 3 -- eigentl. betr. EJ Kunstkammer: Nr. 2105: III A [12-183 203, 204], III E [1-2] -- General Secret. Dielitz vom 23.02.1844,über die durch den Prof. Lepsius angekaufte Wernesch(e) Sammlung ethnographischer Gegenstände aus dem oberen Nil Stromgebiete., 1844, Ferdinand Werne (3.8.1800 - 2.9.1874)</formattedValue>
    @name?
    E 362/1844: objId 225082

    4399791 Vorgang
    4399760 Object

    NEW: splits string at ;
    Example
    Objektbezug: III A 2610, Tabakpfeifenkopf, Karl Richard Lepsius (1810 - 1884);
    Objektbezug: VIII A 11666, Positiv, SW, Palmöl-Lampe, Kurt Grunst (*04.04.1921);
    """

    if Vorgang is None:
        return missing_info
    VorgangsL = _sanitize_multi(Vorgang)
    global archive_data
    if not archive_data:
        archive_data = open_archive_cache(conf)
    header = f"""
        <composite {NS} name="ObjObjectCre">
          <compositeItem>
            <moduleReference name="ObjObjectARef" targetModule="Object">"""
    footer = """
            </moduleReference>
          </compositeItem>
        </composite>"""

    xml = header
    logger = logging.getLogger(__name__)

    for vorgang2 in VorgangsL:
        print(f"objRefA {vorgang2=}")
        # one test is not enough (if key is there), also if key has truthy value
        if vorgang2 not in archive_data or not archive_data[vorgang2]:
            missing_info = True
            msg = f"item not in archive cache: '{vorgang2}'"
            print(f"!!!{msg}")
            logging.error(msg)
            continue
            # raise TypeError(f"Archival document not in cache '{vorgang2}'")
            #
        try:
            rel_objId = archive_data[vorgang2][0]
        except IndexError:
            missing_info = True
            msg = f"archive cache: no ID: '{vorgang2}'"
            print(f"!!!{msg}")
            logging.error(msg)
        # print (f"xxxxxxxxxxxxxxx: {rel_objId=}")
        # try:
        # rel_objId = archive_data[vorgang2][0]
        #
        # continue
        xml += f"""
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
          </moduleReferenceItem>"""

    xml += footer

    _new_or_replace(
        record=recordM,
        xpath="//m:composite[@name = 'ObjObjectCre']",
        newN=etree.fromstring(xml),
    )
    return missing_info


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
    try:
        sachbegriff = _sanitize(sachbegriff)
    except (TypeError, ValueError):
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
              <value>vereinfachter Sachbegriff aus Hauptkatalog  (#ETB04)</value>
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


def _ident_from_record(recordM: Module) -> str:
    return recordM.xpath("""/m:application/m:modules/m:module[
        @name = 'Object'
    ]/m:moduleItem/m:repeatableGroup[
        @name = 'ObjObjectNumberGrp'
    ]/m:repeatableGroupItem/m:dataField[@
        name ='InventarNrSTxt'
    ]/m:value/text()""")[0]


def _lookup_name(*, name: str, conf: dict) -> int:
    """
    Lookup that returns the ids for a given name in the cache.

    Note it is possible that one name has multiple entries, hence we
    always return a tuple which often contains only one hit.

    For cases where there are  multiple records for one name,
    raise TypeError and log. (We used to silently take the first name record.)

    Raises KeyError if name not in cache.
    Raises IndexError when there is no int to report back

    TODO: Test. Doesn't seem to raise error when I expect it to raise.
    """
    global person_data
    logger = logging.getLogger(__name__)
    if not person_data:  # cache empty
        person_data = open_person_cache(conf)

    try:
        adict = person_data[name]
    except KeyError:
        msg = f"!!Person not in cache! '{name}'"
        logger.error(msg)
        raise KeyError(msg)

    if len(adict) > 1:
        # break early especially during dry-runs
        # this has never happened so far, so die when it does
        msg = f"Ambiguous date for person in cache! '{name}' {adict}"
        logger.error(msg)
        raise TypeError(msg)

    for date in person_data[name]:
        print(f"{person_data[name][date]=}")
        IDs = person_data[name][date]

        if len(IDs) > 1:
            # break early especially during dry-runs
            msg = f"Ambiguous person name in cache! '{name}'"
            logger.error(msg)
            raise TypeError(msg)
        elif len(IDs) == 0:
            msg = f"Person has no ID {name}"
            logger.error(msg)
            raise KeyError(msg)
    return IDs[0]


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
        logger.error(f"Unbekannte Ort: '{name}'")
        raise KeyError(f"Unbekannter Ort: '{name}'!")


def _lookup_role(role: str | None) -> int | None:
    """
    Update: returns None if that role is None.

    Use 0 oder 000000 instead if you want to keep the field empty in RIA.
    """

    logger = logging.getLogger(__name__)
    if role is None:
        return None

    global roles
    try:
        return roles[role]
    except KeyError:
        logger.error(f"Unbekannte Rolle: '{role}'")
        raise KeyError(f"Unbekannte Rolle: '{role}'")


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


def _sanitize(value: str) -> str:
    """
    value comes from an Excel cell. It's probably a string, but it can be None or
    an int.

    Eliminating leading and trailing whitespace. We test for different "empty" values (None, "", isspace) and raise exception in those cases.

    Also we mask & and other things.
    """
    value = _sanitize2(value)
    return saxutils.escape(value)  # escape things like &


def _sanitize2(value: str) -> str:
    """
    A version of _sanitize that doesn't mask anything. I need
    that b/c masked char often include a colon (&amp;)
    """
    if value is None:
        raise TypeError("value is None")

    if not isinstance(value, str):
        raise TypeError(f"Value should be str, but it's not! {value}")

    astr = value.strip()

    if astr == "":
        raise ValueError(f"Empty string {value=}")
    return astr


def _sanitize_multi(astr: str) -> list:
    """
    First sanitize conventionally, then split into individual entries.
    Ignore empty entries. Raises if _sanitize2 raises, i.e. if astr is
    None or empty. Empty individual entries are silently ignored.
    """
    # print(f"xxx:{astr}")
    astr = _sanitize2(astr)
    # print(f"yyy:{astr}")
    astrL = astr.split(";")
    astrL2 = list()
    # filter out empty strings etc.
    for item in astrL:
        item = item.strip()
        if item != "":
            # item = saxutils.escape(item)
            astrL2.append(item)
    return astrL2


def _split_off_role(string_role: str) -> tuple[str | None, str | None]:
    """
    Role is something at the end of the string seaparated by a comma
    this is a string, role

    returns everything left of the comma and the role
    Not sure what to do if there is no comma.
    """
    if string_role is None:
        return None, None

    string_role = string_role.strip()

    if "," in string_role:
        parts = string_role.rsplit(",", 1)
        left = parts[0].strip()
        role = parts[1].strip() or None
    else:
        # dont fail here
        # raise SyntaxError("no comma, no role")
        left = string_role
        role = None

    if role not in roles:
        if role is not None:
            print(f"Error: Unknown role ignoring: {role}")
            if left is not None and role is not None:
                left = string_role
            else:
                left = role
            role = None

    if left == "":
        # treat an empty string as no input
        left = None

    return left, role


def _split_off_prefix(string) -> tuple[str | None, str | None]:
    """
    some string start with a prefix. THese prefixes are separted with a colon
    Prefix: rest of the string.
    """
    if string is None:
        return None, None

    string = string.strip()
    if ":" in string:
        parts = string.split(":", 1)
        prefix = parts[0].strip()
        right = parts[1].strip() or None
    else:
        # Let's not quite fail so early
        # raise SyntaxError("no colon, no prefix")
        prefix = None
        right = string

    if right == "":
        # treat an empty string as no input
        right = None

    return prefix, right


def _get_name_date(string: str) -> tuple[str | None, str | None]:
    # do we really expect a None as input
    if string is None:
        return None, None

    # try to extract a date that is the final (...) group (allowing nested/other parentheses in name)
    # take the last parenthesized block as the date
    depth = 0
    end = None
    start = None

    # find the last balanced (...) block
    for i in range(len(string) - 1, -1, -1):
        if string[i] == ")":
            if end is None:
                end = i
            depth += 1
        elif string[i] == "(":
            depth -= 1
            if depth == 0 and end is not None:
                start = i
                break

    if start is not None and end is not None:
        candidate_name = string[:start].rstrip()
        candidate_date = string[start + 1 : end].strip()

        if any(ch.isdigit() for ch in candidate_date):
            return candidate_name or None, candidate_date or None

    if string == "":
        string = None
    return string or None, None


def _quad_split(string: str) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Parse a string of the form:
      <name possibly with parentheses...> (<date or date-range>), <role>
    Returns (name, date, role). date and role may be None if missing.

    This parser does NOT accept mutliple entries separated by semicolon. Split the string
    at an earlier stage.
    """

    if string is None:
        return None, None, None, None

    string = string.strip()
    left, role = _split_off_role(string)
    prefix, right = _split_off_prefix(left)

    name, date = _get_name_date(right)

    return prefix, name, date, role
