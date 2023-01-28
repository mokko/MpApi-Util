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

import copy
from lxml import etree  # type: ignore
from mpapi.constants import NSMAP
from mpapi.client import MpApi
from mpapi.module import Module
from mpapi.search import Search
from MpApi.Utils.identNr import IdentNrFactory, IdentNr
from typing import Optional

DEBUG = True

parser = etree.XMLParser(remove_blank_text=True)


class RiaUtil:
    def __init__(self, *, baseURL: str, user: str, pw: str):
        self.mpapi = MpApi(baseURL=baseURL, user=user, pw=pw)

    def create_from_template(self, *, template: Module, identNr: str = None) -> int:
        """
        Given a template record (a module Object),
        - copy that
        - replace existing identNr with new one

        Returns objId of created record; raises on some errors.
        """
        if identNr.isspace():
            raise TypeError("Ident cant only consist of space: {identNr}")

        if identNr is None:
            raise TypeError("Ident can't be None")

        if len(template) != 1:
            raise ValueError(
                "Template should be a single record; instead {len(template)} records"
            )

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
        f = IdentNrFactory()
        iNr = f.new_from_str(text=identNr)
        new_numberGrpN = iNr.get_node()

        new_item = copy.deepcopy(template)  # so we dont change the original
        # there can be only one or none
        try:
            numberGrpN = new_item.xpath(
                "//m:repeatableGroup[@name = 'ObjObjectNumberGrp']"
            )[0]
        except:
            # if no OBjObjectNumberGrp
            mItemN = new_item.xpath("//m:moduleItem")[0]
            etree.append(mItemN, new_numberGrpN)
        else:
            # if there is one already replace it
            numberGrpN.getparent().replace(numberGrpN, new_numberGrpN)

        new_item.toFile(path="DDrewritten.xml")
        print(f"About to create record {identNr}")
        objId = self.mpapi.createItem3(data=new_item)
        return objId

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

    def identNr_exists2(
        self, *, nr: str, orgUnit: Optional[str] = None, strict: bool = True
    ) -> list[tuple[int, str]]:
        """
        Returns objIds and identNr as tuple inside a list
        """
        if strict is True:
            op = "equalsField"
        else:
            op = "startsWithField"

        q = Search(module="Object", limit=-1, offset=0)
        if orgUnit is not None:
            q.AND()
        q.addCriterion(
            field="ObjObjectNumberVrt",
            operator=op,
            value=nr,
        )
        if orgUnit is not None:
            q.addCriterion(operator="equalsField", field="__orgUnit", value=orgUnit)
        q.addField(field="ObjObjectNumberTxt")
        q.addField(field="ObjObjectNumberVrt")  # dont know what's the difference
        q.validate(mode="search")  # raises if not valid
        m = self.mpapi.search2(query=q)
        if not m:
            return []

        results = list()
        m.toFile(path="debug.xml")
        for itemN in m.iter(module="Object"):
            objId = int(itemN.xpath("@id")[0])
            identNrL = itemN.xpath(
                "m:dataField[@name = 'ObjObjectNumberTxt']/m:value", namespaces=NSMAP
            )
            results.append((objId, identNrL[0].text))
        return results

    def identNr_exists(
        self, *, nr: str, orgUnit: Optional[str] = None, strict: bool = True
    ) -> list[int]:
        """
        Simple check if identNr exists in RIA. Returns a list of objIds of the
        matching records.

        identNr is compared to ObjObjectNumberVrt which exists only in Objects.

        If optional orgUnit is present it returns only objIds that are in that
        orgUnit.

        New:
        - returns a potentially empty list; empty list is falsy
        - list with items is truthy
        - has a strict mode (default). In strict mode it returns exact matches. If strict
          is False, returns searches if identNr begin with this string.

        if r := c.identNr_exists(nr="VII c 123"):
            print (len(r))
            for objId in r:
                do_something()
        """

        if strict is True:
            op = "equalsField"
        else:
            op = "startsWithField"

        q = Search(module="Object", limit=-1, offset=0)
        if orgUnit is not None:
            q.AND()
        q.addCriterion(
            field="ObjObjectNumberVrt",
            operator=op,
            value=nr,
        )
        if orgUnit is not None:
            q.addCriterion(operator="equalsField", field="__orgUnit", value=orgUnit)
        q.addField(field="__id")
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

        # m.clean()  # necessary? Eliminates Versicherungswert; let's just drop the virtual fields
        m.uploadForm()
        # if DEBUG:
        #    m.toFile(path=f"DDtemplate-{mtype}{ID}.xml")
        return m

    def rm_junk(self, text: str):
        """
        rm the <html> garbage from Zetcom's dreaded bug
        """

        if "<html>" in text:
            text = text.replace("<html>", "").replace("</html>", "")
            text = text.replace("<body>", "").replace("</body>", "")
        return text
