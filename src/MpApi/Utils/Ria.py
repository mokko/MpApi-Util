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
from mpapi.constants import NSMAP, get_credentials
from mpapi.client import MpApi
from mpapi.module import Module
from mpapi.search import Search
from MpApi.Utils.identNr import IdentNrFactory
from pathlib import Path
import requests
from typing import Optional

Response = requests.models.Response

DEBUG = True

parser = etree.XMLParser(remove_blank_text=True)


class RIA:
    def __init__(self, *, baseURL: str, user: str, pw: str):
        self.mpapi = MpApi(baseURL=baseURL, user=user, pw=pw)
        self.fac = IdentNrFactory()
        self.photographer_cache: dict[str, list | None] = {}

    def create_asset_from_template(self, *, templateM) -> int:
        """method not really necessary"""
        mulId = self.mpapi.createItem3(data=templateM)
        return mulId

    def create_from_template(
        self, *, template: Module, identNr: str, institution: str = "EM"
    ) -> int:
        """
        Given a template record (a module Object),
        - copy that
        - replace existing identNr with new one

        Returns objId of created record; raises on some errors.
        """
        if identNr is None:
            raise TypeError("Ident can't be None")

        # print(f"+++{identNr=}")

        if identNr.isspace():
            raise TypeError("Ident cant only consist of space: {identNr}")

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
        iNr = self.fac.new_from_str(text=identNr, institution=institution)
        new_numberGrpN = iNr.get_node()

        new_item = copy.deepcopy(template)  # so we dont change the original
        # there can be only one or none
        try:
            numberGrpN = new_item.xpath(
                "//m:repeatableGroup[@name = 'ObjObjectNumberGrp']"
            )[0]
        except KeyError:
            # if no OBjObjectNumberGrp
            mItemN = new_item.xpath("//m:moduleItem")[0]
            mItemN.append(new_numberGrpN)
        else:
            # if there is one already replace it
            numberGrpN.getparent().replace(numberGrpN, new_numberGrpN)

        # new_item.toFile(path="DDrewritten.xml")
        print(f"About to create record '{identNr}'")
        objId = self.mpapi.createItem3(data=new_item)
        return objId

    def create_item(self, *, item: Module) -> int:
        """
        Provide access to client's createItem with "modern" signature.
        """
        objId = self.mpapi.createItem3(data=item)
        return objId

    def get_objIds(
        self, *, identNr: str, strict: bool = True, orgUnit: str | None = None
    ) -> str:
        """
        For an individual identNr (provided as str), lookup matching ids in RIA and
        return them a colon separated list. If no results are found, the string "None"
        is returned.

        If the results include the dreaded <html> garbage, as MuseumPlus does sometimes
        especially for identNrs, that junk is filtered out.

        strict (optional): strict=True looks for exact matches; strict=None looks for
        identNr beginning with the provided string. Strict=True is the default.

        orgUnit (optional): If a valid orgUnit is provided, only results from that
        orgUnit are returned.
        """
        # ident = identNr.strip()  # really do this?
        objIdL = self.identNr_exists(nr=identNr, orgUnit=orgUnit, strict=strict)
        if not objIdL:
            return "None"
        return self.rm_junk("; ".join(str(objId) for objId in objIdL))

    def get_objIds2(
        self, *, identNr: str, strict: bool = True, orgUnit: str | None = None
    ) -> set:
        """
        A version of get_objIds that allows to search for Sonderzeichen. Not very
        fast, but since RIA cant search for Sonderzeichen there sometimes is no way
        around it.

        The background problem is that MuseumPlus does not allow to search for
        Sonderzeichen. So a search for "VII a 123 >" returns the same result as
        "VII a 123"

        Returns a possibly empty list with objIds.

        UPDATE
        - Used to return semicolon separated string or "None" as a string.

        TODO:
        - There is a now an exact search in RIA that might make this search obsolete.
        """
        real_parts = set()  # do we need double brackets? doubtful
        for single in identNr.split(";"):
            identNr = single.strip()
            resL = self.identNr_exists2(nr=identNr, orgUnit=orgUnit, strict=strict)
            if not resL:
                continue
            for result in resL:
                objId = result[0]
                identNr_part = self.rm_junk(result[1])
                if f"{identNr} " in identNr_part:
                    real_parts.add(objId)
        # if we tested some results, but didnt find any real parts
        # we dont want to test them again
        return real_parts

    def get_objIds_startswith(
        self, *, identNr: str, orgUnit: str | None = None
    ) -> dict[int, str]:
        """
        A lax search that finds all records that have an identNr which begins
        with a given identNr string.

        Returns a dictionary which may be empty.
            dict = {
                objId_int: "IdentNr",
                12345: "VII f 123 a,b",
            }

        We're using ObjObjectNumberVrt for the identNr returned in the hash
        assuming that there will be only one there.

        WIP: not successfully tested
        """
        q = Search(module="Object", limit=-1, offset=0)
        if orgUnit is not None:
            q.AND()
        q.addCriterion(
            field="ObjObjectNumberVrt",
            operator="startsWithField",
            value=identNr,
        )
        if orgUnit is not None:
            q.addCriterion(operator="equalsField", field="__orgUnit", value=orgUnit)
        q.addField(field="ObjObjectNumberTxt")
        q.addField(field="ObjObjectNumberVrt")  # dont know what's the difference
        q.validate(mode="search")  # raises if not valid
        m = self.mpapi.search2(query=q)
        objIds = {}
        objIdL = m.get_ids(mtype="Object")
        for objId in objIdL:
            objId = int(objId)
            objNumberL = m.xpath(
                f"""/m:application/m:modules/m:module[
                    @name = 'Object'
                ]/m:moduleItem[
                    @id = '{objId}']/m:virtualField[
                        @name = 'ObjObjectNumberVrt'
                    ]/m:value"""
            )
            if len(objNumberL) > 1:
                raise ValueError("1+ identNrs per record.")
                # If we find cases with multiple objNumbers per record we will need to
                # save lists as values...
            if objNumberL:  # if any results
                objIds[objId] = objNumberL[0].text
        return objIds

    def get_objIds_strict(self, *, identNr: str, orgUnit: str | None = None) -> dict:
        """
        Another version of the get_objIds that uses Zetcom's new exact search which
        respects Sonderzeichen. We return a dictionary which may be empty if no results.

        A single record can have multiple identNrs, but we report __only__ the one
        that we queried.

        An identNr should be unique, but there may be cases where multiple records
        have the same identNr.
            dict = {
                objId_int: "IdentNr1", # ObjObjectNumberVrt
                objId_int: "IdentNr2",
            }

        Now we need a version of dict.values that lists all distinct identNr
        """
        q = Search(module="Object", limit=-1, offset=0)
        if orgUnit is not None:
            q.AND()
        q.addCriterion(
            field="ObjObjectNumberVrt",
            operator="equalsExact",
            value=identNr,
        )
        if orgUnit is not None:
            q.addCriterion(operator="equalsField", field="__orgUnit", value=orgUnit)
        q.addField(field="ObjObjectNumberTxt")
        q.addField(field="ObjObjectNumberVrt")  # dont know what's the difference
        q.validate(mode="search")  # raises if not valid
        m = self.mpapi.search2(query=q)
        objIds = {}
        objIdL = m.get_ids(mtype="Object")
        for objId in objIdL:
            objId = int(objId)
            objNumberL = m.xpath(
                f"""/m:application/m:modules/m:module[
                    @name = 'Object'
                ]/m:moduleItem[
                    @id = '{objId}']/m:virtualField[
                        @name = 'ObjObjectNumberVrt'
                    ]/m:value"""
            )
            if len(objNumberL) > 1:
                raise ValueError("1+ identNrs per record.")
                # If we find cases with multiple objNumbers per record we will need to
                # save lists as values...
            if objNumberL:  # if any results
                objIds[objId] = objNumberL[0].text
        return objIds

    def get_photographerID(self, *, name) -> Optional[list]:
        if name is None:
            print("   WARNING: Photographer name is None!")
            return None
        if name in self.photographer_cache:
            # print (f"   photographer cache {self.photographer_cache[name]}")
            return self.photographer_cache[name]
        else:
            IDs = self._get_photographerID(name=name)
            self.photographer_cache[name] = IDs
            # print (f"   new photographer {IDs}")
            return IDs

    def id_exists(self, *, mtype: str, ID: int) -> bool:
        """
        Test if a single ID exists. Returns False if not and True if so.

        This is simple test, not even a lookup.
        """
        q = Search(module=mtype)
        q.addCriterion(operator="equalsField", field="__id", value=str(ID))
        q.addField(field="__id")
        m = self.mpapi.search2(query=q)

        if m.totalSize(module=mtype) == 0:
            return False
        else:
            return True

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

    def identNr_exists2(
        self, *, nr: str, orgUnit: str | None = None, strict: bool = True
    ) -> list[tuple[int, str]]:
        """
        Returns a list of tuples containing objIds and identNr.

        What happens if no item found. We return an empty list.

        Who wants such a complicated return value?
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
        # m.toFile(path="debug.xml")
        for itemN in m.iter(module="Object"):
            objId = int(itemN.xpath("@id")[0])
            # print(f"+*+{objId}")
            identNrL = itemN.xpath(
                "m:virtualField[@name = 'ObjObjectNumberVrt']/m:value", namespaces=NSMAP
            )
            results.append((objId, identNrL[0].text))
        return results

    def identNr_exists3(self, *, ident: str, orgUnit: Optional[str] = None) -> set[int]:
        """
        Another version that for a given identNr returns objIds as a set or empty set
        if no record is found. Uses equalsExact.
        """
        q = Search(module="Object", limit=-1, offset=0)
        if orgUnit is not None:
            q.AND()
        q.addCriterion(
            field="ObjObjectNumberVrt",
            operator="equalsExact",
            value=ident,
        )
        if orgUnit is not None:
            q.addCriterion(operator="equalsField", field="__orgUnit", value=orgUnit)
        q.addField(field="__id")

        results = set()
        m = self.mpapi.search2(query=q)
        for itemN in m.iter(module="Object"):
            objId = int(itemN.xpath("@id")[0])
            results.add(objId)
        return results

    # a simple lookup
    def fn_to_mulId(self, *, fn: str, orgUnit=None) -> set:
        """
        For a given filename check if there is one or more assets with that same filename
        in RIA.

        New:
        - Return empty set if no records found! Used to return None.
        - This used to be a lax search, not we want a strict search that respect "special"
          chars like hyphen.
        """
        # print (f"* Getting assets for filename '{fn}'")
        # print (f"----------{orgUnit}")
        if fn is None:
            raise SyntaxError("ERROR: fn can't be None")
        q = Search(module="Multimedia")
        if orgUnit is not None:
            q.AND()
        # used to be equalsField, will be equalsExact
        q.addCriterion(operator="equalsExact", field="MulOriginalFileTxt", value=fn)
        if orgUnit is not None:
            q.addCriterion(operator="equalsField", field="__orgUnit", value=orgUnit)
        q.addField(field="__id")
        # q.toFile(path=".debug.search.xml")
        q.validate(mode="search")
        m = self.mpapi.search2(query=q)
        positiveIDs = set()

        for itemN in m.iter(module="Multimedia"):
            positiveIDs.add(itemN.get("id"))
        return positiveIDs

    def get_template(self, *, mtype: str, ID: int) -> Module:
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

        expects text as string, returns cleaned text as string.
        """

        if "<html>" in text:
            text = text.replace("<html>", "").replace("</html>", "")
            text = text.replace("<body>", "").replace("</body>", "")
        return text

    def mk_asset_standardbild2(self, *, objId: int, mulId: int) -> Response | None:
        """
        Let's try another version where we only change one moduleReferenceItem, and not
        the whole record. In other words: let's use mpapi.updateRepeatableGroup()

        Now it works. I assume that previous attempts didn't work, because I needed to
        provide all the items, not only the changed one.
        """
        # print (f"Getting whole record object {objId}")
        m = self.mpapi.getItem2(mtype="Object", ID=objId)
        # the xpath could fail, but only if that object doesn't exist or doesn't have
        # this asset. These are good reasons to fail/die
        objMultimediaRefN = m.xpath(
            f"""/m:application/m:modules/m:module[
                @name = 'Object'
            ]/m:moduleItem[
                @id = '{objId}'
            ]/m:moduleReference[
                @name='ObjMultimediaRef'
            ]"""
        )[0]
        mRefItemN = objMultimediaRefN.xpath(
            f"""m:moduleReferenceItem[
                @moduleItemId = '{mulId}'
            ]""",
            namespaces=NSMAP,
        )[0]
        xml = """
            <dataField dataType="Boolean" name="ThumbnailBoo">
                <value>true</value>
            </dataField>"""
        frag = etree.XML(xml, parser=parser)
        mRefItemN.append(frag)

        mref_str = etree.tostring(
            objMultimediaRefN, pretty_print=True, encoding="unicode"
        )
        # print(mref_str)

        xml = f"""
            <application xmlns="http://www.zetcom.com/ria/ws/module">
              <modules>
                <module name="Object">
                  <moduleItem id="{objId}">
                    {mref_str}
                  </moduleItem>
                </module>
              </modules>
            </application>"""

        # is there already a Standardbild?
        resL = objMultimediaRefN.xpath(
            "m:moduleReferenceItem/m:dataField[@name = 'ThumbnailBoo']",
            namespaces=NSMAP,
        )
        if len(resL) == 0:
            # print(
            #    f"no Standardbild yet, so trying to make one objId {objId} mulId {mulId}"
            # )
            r = self.mpapi.updateRepeatableGroup(
                module="Object",
                id=objId,
                referenceId=mulId,
                repeatableGroup="ObjMultimediaRef",
                xml=xml,
            )
            print(r)
            return r
        else:
            print("Standardbild already exsts, aborting")
            return None

    def mk_asset_standardbild(self, *, objId: int, mulId: int) -> None:
        """
        For a given objId that references a known mulId, make that mulId a Standardbild.
        Probably, the asset has to be already linked to object.

        This version downloads the whole object recrd, changes it and uploads it back. This
        is not optimal because several fields get updated.

        BEFORE
        <moduleReference name="ObjMultimediaRef" targetModule="Multimedia" multiplicity="M:N" size="1">
          <moduleReferenceItem moduleItemId="6572162" uuid="5d9773fc-c746-43cb-8af6-ff8ae708bfe4" seqNo="0"/>
        </moduleReference>

        AFTER
        <moduleReference name="ObjMultimediaRef" targetModule="Multimedia" multiplicity="M:N" size="1">
          <moduleReferenceItem moduleItemId="6571823" uuid="b45e7114-8933-4e52-8cc2-9008b4dc48cb" seqNo="0">
            <dataField dataType="Boolean" name="ThumbnailBoo">
              <value>true</value>
            </dataField>
          </moduleReferenceItem>

        Get the whole record, add one static dataField and upload everything
        """
        print(f"Getting whole record object {objId}")
        m = self.mpapi.getItem2(mtype="Object", ID=objId)
        # the xpath could fail, but only if that object doesn't exist or doesn't have
        # this asset. These are good reasons to fail/die
        objMultimediaRefN = m.xpath(
            f"""/m:application/m:modules/m:module[
                @name = 'Object'
            ]/m:moduleItem[
                @id = '{objId}'
            ]/m:moduleReference[
                @name='ObjMultimediaRef'
            ]"""
        )[0]
        mRefItemN = objMultimediaRefN.xpath(
            f"""m:moduleReferenceItem[
                @moduleItemId = '{mulId}'
            ]""",
            namespaces=NSMAP,
        )[0]
        # only add a Standardbild-marker if it does not exist yet
        # at first we checked only the current asset and not all assets for a Thumbnail,
        # but one object can have only a single one Standardbild
        # Let's not set Standardbild, if object already has one, since then eyes are necessary
        # to decided which one is best.
        resL = objMultimediaRefN.xpath(
            "m:moduleReferenceItem/m:dataField[@name = 'ThumbnailBoo']",
            namespaces=NSMAP,
        )
        if len(resL) == 0:
            xml = """
                <dataField dataType="Boolean" name="ThumbnailBoo">
                    <value>true</value>
                </dataField>"""
            frag = etree.XML(xml, parser=parser)
            mRefItemN.append(frag)
            print(m.toString())
            print("Updating record in RIA...")
            #  since we're uploading the whole document, RIA logs changes to multiple
            #  fields. This is not good, but it works.
            self.mpapi.updateItem2(mtype="Object", ID=objId, data=m)
        else:
            print("Thumbnail already set!?")
            print(
                etree.tostring(objMultimediaRefN, pretty_print=True, encoding="unicode")
            )

    def upload_attachment(self, *, file: str | Path, ID: int):
        """
        Save attachment to asset/Multmedia record identified by id.

        * New: returns reponse object
        * We could debate how much error checking should happen where. Let's say there
          there should be none in the actual api. Then we could ask if it should happen
          elsewhere, e.g. in the RIA package. What we don't want it redundant (=multiple)
          checks.
        """
        p = Path(file)
        if not p.exists():
            raise TypeError(f"ERROR: Path '{file}' does not exist")
        if p.is_dir():
            raise TypeError(f"ERROR: Path '{file}' is a dir")

        return self.mpapi.updateAttachment(module="Multimedia", path=str(file), id=ID)

    #
    # more private
    #

    def _get_photographerID(self, *, name) -> Optional[list]:
        q = Search(module="Person")
        q.addCriterion(operator="equalsField", field="PerNennformTxt", value=name)
        q.addField(field="__id")
        m = self.mpapi.search2(query=q)

        if not m:
            # print("No result")
            return None
        return m.get_ids(mtype="Person")


def init_ria() -> RIA:
    user, pw, baseURL = get_credentials()
    print(f">> Logging in as {user}")
    client = RIA(baseURL=baseURL, user=user, pw=pw)
    return client


if __name__ == "__main__":
    pass
