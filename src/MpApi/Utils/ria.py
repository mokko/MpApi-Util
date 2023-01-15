"""
Reusable methods that interface with the low-level mpapi client

(0) Construction
    from MpApi.Util.Ria import RiaUtil
    c = RiaUtil(baseURL=b, user=u, pw=p)

(1) Inspect/modify local data (module, itemN) without online access
    ::: this stuff could go to Module :::
    self.add_identNr (itemN=n, nr="VII f 123") # changes itemN in place

(2) Check online records

    if id_exists(mtype="Object", ID=257778):
        do_something()


(3) Lookups (return one for another)

    if identNrExists(mtype="Object", orgUnit="EMMusikethnologie" nr="VII f 123"):
        do_something() 

    if identNrExists(mtype="Object", nr="VII f 123") > 1:
        currently, identExists returns number of moduleItems found
        might change to list of objIds


    objIdL = self.fn_to_mulId(fn="eins.jpg", orgUnit="EMMusikethnologie")
        returns mulIds of records with that filename; if orgUnit is specified
        search is limited to that orgUnit
    objIds = self.objId_for_ident(identNr="VII f 123")

(4) Change RIA
    objId = self.create_from_template(tid=1234, ttype="Object", ident="VII c 123")


"""

from lxml import etree  # type: ignore
from mpapi.module import Module
from mpapi.search import Search
from mpapi.client import MpApi
from typing import Optional
import copy

DEBUG = True

parser = etree.XMLParser(remove_blank_text=True)

NSMAP = {
    "m": "http://www.zetcom.com/ria/ws/module",
    "o": "http://www.zetcom.com/ria/ws/module/orgunit",
}


class RiaUtil:
    def __init__(self, *, baseURL: str, user: str, pw: str):
        self.mpapi = MpApi(baseURL=baseURL, user=user, pw=pw)

    def add_identNr(self, *, itemN, nr: str):
        """
        Expect a moduleItem fragment and create/overwrite the identNr ObjObjectNumberGrp

        Side-effect:Changes itemN in place.

        Todo:
        - Create a new identNr or change an existing one
        - decide if I want a whole document or just an itemN
        - test it

        Assume that
        - I dont need or may not have InventarNrSTxt, ModifiedByTxt, ModifiedDateDat,
        - have to have Part1Txt, Part2Txt, Part3Txt and
        - want to have SortLnu
        <repeatableGroup name="ObjObjectNumberGrp">
          <repeatableGroupItem>
            <dataField name="InventarNrSTxt">
              <value>VIII B 74</value>
            </dataField>
            <dataField name="ModifiedByTxt">
              <value>EM_EM</value>
            </dataField>
            <dataField name="ModifiedDateDat">
              <value>2010-05-07</value>
            </dataField>
            <dataField name="Part1Txt">
              <value>VIII</value>
            </dataField>
            <dataField name="Part2Txt">
              <value> B</value>
            </dataField>
            <dataField name="Part3Txt">
              <value>74</value>
            </dataField>
            <dataField name="SortLnu">
              <value>1</value>
            </dataField>
            ...

            Note the leading space in Part2!

        <repeatableGroup name="ObjObjectNumberGrp">
          <repeatableGroupItem>
            <dataField name="InventarNrSTxt">
              <value>{identNr}</value>
            </dataField>
            <dataField name="Part1Txt">
              <value>{part1}</value>
            </dataField>
            <dataField name="Part2Txt">
              <value> {part2}</value>
            </dataField>
            <dataField name="Part3Txt">
              <value>{part3}</value>
            </dataField>
            <dataField name="SortLnu">
              <value>1</value>
            </dataField>
          </repeatableGroupItem>
        </repeatableGroup>
        """

        part1 = identNr.split()[0]
        part2 = " " + identNr.split()[1]  # weird
        part3 = " ".join(identNr.split()[2:])
        print(f"DEBUG:{part1}|{part2}|{part3}|")

        itemN = data.xpath("/m:application/m:modules/m:module/m:moduleItem[1]")[0]
        # assume that ObjObjektNumberGrp exists already, which is a reasonable expectation
        # only api-created records may have no identNr
        rGrpN = data.repeatableGroup(parent=itemN, name="ObjObjectNumberGrp")
        grpItemN = data.repeatableGroupItem(parent=rGrpN)
        data.dataField(parent=grpItemN, name="InventarNrSTxt", value=identNr)
        data.dataField(parent=grpItemN, name="Part1Txt", value=part1)
        data.dataField(parent=grpItemN, name="Part2Txt", value=part2)
        data.dataField(parent=grpItemN, name="Part3Txt", value=part3)
        data.dataField(parent=grpItemN, name="SortLnu", value="1")
        vr = data.vocabularyReference(parent=grpItemN, name="DenominationVoc")
        data.vocabularyReferenceItem(parent=vr, ID=2737051)  # Ident. Nr.
        mrN = data.moduleReference(parent=grpItemN, name="InvNumberSchemeRef")
        data.moduleReferenceItem(
            parent=mrN, moduleItemId="68"
        )  # EM-Südsee/Australien VIII B
        # return m we change the object in-place

    def create_from_template(self, *, template: Module, identNr: str = None) -> int:
        """
        Given a template record (a module Object), copy that
        to a new record of the same type, fill in the provided identNr and return
        the ID of the new record.

        Raises on some errors.

        Returns objId of newly created record as int.
        """
        if identNr.isspace():
            raise TypeError("Ident cant only consist of space: {identNr}")

        if identNr is None:
            raise TypeError("Ident can't be None")

        if len(template) != 1:
            raise ValueError(
                "Template should be a single record; instead {len(template)} records"
            )
        mtype = template.extract_mtype()
        print(f"mtype {mtype}")

        """
        the identNr issue: usually we dont want to duplicate a template with an
        identNr. Instead we want typically supply a new identNr or leave the field
        empty. So we might want to test if identNr is empty of not. We could even 
        require it to be empty
        
        SPECIFIC TO OBJECTS
        BTW: any way that deals with identNr will only work in the Object module,
        so currently we're specific to this module.
        
        IDENT NR ISSUE
        
        Let's first identify where in the record the identNr is present. The issue here
        is that it exists in multiple places
        (1) virtualFields: already deleted
        (2) dataField:ObjObjectNumberTxt 
        (3) repeatableGroup:ObjObjectNumberGrpt
        ISSUE Wrong orgUnit and possible rights issues
        Next issue of the orgUnit. Since I dont have the rights for writing in the 
        Bereich of the template, RIA changes the Bereich internally to one that I have
        write rights to (EM-Allgemein). This is a hypothesis. Should go away if program
        is executed with the correct rights. But I might automate a corresponding test.
        
        I dont have the rights to delete identNr from record in RIA. So let's do this
        in here.
        
        """
        t2 = copy.deepcopy(template)  # so we dont change the original
        # discard __all__ existing identNrs of the template
        # this might be a bit heavy-handed, but let's do it anyways for now
        ObjNumberGrpL = t2.xpath("//m:repeatableGroup[@name = 'ObjObjectNumberGrp']")
        for ObjNumberGrpN in ObjNumberGrpL:
            ObjNumberGrpN.getparent().remove(ObjNumberGrpN)
        t2.toFile(path="DDrewritten.xml")
        t2.newObjNumberGrp(identNr=identNr)

        # raise SyntaxError ("SH")
        # objId = self.mpapi.createItem3(data=tnew)
        # return objId
        raise RuntimeError("Stop here!")

    # a simple test - not even a lookup
    def id_exists(self, *, mtype: str, ID: int) -> bool:
        """
        Test if an ID exists. Returns False if not and True if so.

        """
        q = Search(module=mtype)
        q.addCriterion(operator="equalsField", field="__id", value=str(ID))
        q.addField(field="__id")
        m = self.mpapi.search2(query=q)

        if m.totalSize(module=mtype) == 0:
            return False
        else:
            return True

    # a simple loopup
    def identNr_exists(self, *, nr: str, orgUnit: Optional[str] = None) -> list[int]:
        """
        Simple check if identNr exists in RIA. Returns a list of objIds of the
        matching records.

        identNr is compared to ObjObjectNumberVrt which exists only in Objects.

        If optional orgUnit is present it returns only objIds that are in that
        orgUnit.

        New:
        - returns a potentially empty list; empty list is falsy
        - list with items is truthy

        if r := c.identNr_exists(nr="VII c 123"):
            print (len(r))
            for objId in r:
                do_something()
        """

        q = Search(module="Object", limit=-1, offset=0)
        if orgUnit is not None:
            q.AND()
        q.addCriterion(
            field="ObjObjectNumberVrt",
            operator="equalsField",
            value=nr,
        )
        if orgUnit is not None:
            q.addCriterion(operator="equalsField", field="__orgUnit", value=orgUnit)
        q.addField(field="__id")  # make query faster
        q.validate(mode="search")  # raises if not valid
        m = self.mpapi.search2(query=q)
        # this are all moduleItem's ids, but the query makes sure we only have those
        # that we want; xpath returns str
        objIdL = m.xpath("/m:application/m:modules/m:module/m:moduleItem/@id")
        return [int(x) for x in objIdL]

    # a simple lookup
    def fn_to_mulId(self, *, fn, orgUnit=None) -> set:
        """
        For a given filename check if there is one or more assets with that same filename
        in RIA.

        New: Return empty set if no records found! (Used to return None.)
        """
        # print (f"* Getting assets for filename '{fn}'")
        q = Search(module="Multimedia")
        if orgUnit is not None:
            q.AND()
        q.addCriterion(operator="equalsField", field="MulOriginalFileTxt", value=fn)
        if orgUnit is not None:
            q.addCriterion(operator="equalsField", field="__orgUnit", value=orgUnit)
        q.addField(field="__id")
        q.validate(mode="search")
        m = self.mpapi.search2(query=q)
        positiveIDs = set()

        for itemN in m.iter(module="Multimedia"):
            positiveIDs.add(itemN.get("id"))
        return positiveIDs

    def get_template(self, *, mtype, ID):
        """
        Returns a Module object in upload form.
        """
        m = self.mpapi.getItem2(mtype=mtype, ID=ID)

        if not m:
            raise SyntaxError(f"ERROR: Template record not found: {mtype} {ID}")

        m.clean()  # necessary? Eliminates Versicherungswert; let's just drop the virtual fields
        m.uploadForm()
        # if DEBUG:
        #    m.toFile(path=f"DDtemplate-{mtype}{ID}.xml")
        return m

    # deprecated: objId_for_identNr -> use identNr_exists instead
