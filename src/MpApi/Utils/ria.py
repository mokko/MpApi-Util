"""
Attempt to extract functions for reuse

Should we use functions, not classes with methods?
"""

from mpapi.module import Module
from mpapi.search import Search
from mpapi.client import MpApi
from typing import Optional


class RiaUtil:
    def __init__(self, *, baseURL: str, user: str, pw: str):
        self.mpapi = MpApi(baseURL=baseURL, user=user, pw=pw)

    def add_identNr(self, *, itemN, identNr: str):
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
        part2 = " " + identNr.split()[1] # weird
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


    def create_from_template(tid:int, ttype:str, ident:str) -> int:
        """
        Given a template record (identified by a module type and an ID), copy that 
        to a new record of the same type, fill in the provided identNr and return 
        the ID of the new record.
        
        Raises on error.
        """
        if ident.isspace():
            raise TypeError ("Ident cant only consist of space: {ident}")
        #test

        

    def identExists(self, *, mtype:str, nr:str) -> int:
        """
            Simple check if identNr exists in RIA. Returns the number of matching records
            which if a positive number are truthy.
            
            Todo: Could return a list of the found IDs
        """

        s = Search(module=mtype, limit=-1, offset=0)
        # s.AND()
        s.addCriterion(
            field="ObjObjectNumberVrt",
            operator="equalsField",
            value=nr,
        )
        q.addField(field="__id") # make query faster
        q.validate(mode="search") # raises if not valid
        m = self.mpapi.search2(query=s)
        return len(m)


    def fn_to_mulId(self, *, fn, orgUnit=None) -> Optional[set]:
        """
        For a given filename check if there is one or more assets with that same filename
        in RIA.

        Return None if there is none, or the mulIds for the records in a set.
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

        if m.totalSize(module="Multimedia") == 0:
            return None
        else:
            for itemN in m.iter(module="Multimedia"):
                positiveIDs.add(itemN.get("id"))
            return positiveIDs


    def get_template(self, *, mtype, ID): 
        m = self.mpapi.getItem2(mtype=mtype, ID=ID)

        if not m:
            raise SyntaxError(f"ERROR: Template record not found: {mtype} {ID}")

        m.clean()
        m.uploadForm()
        m.toFile(path=f"DDtemplate-{mtype}{ID}.xml") # debug
        return m


    def objId_for_ident(self, *, identNr: str) -> Optional[set]:
        """
        Lookup objIds for identNr
        
        Returns a set containing the found objIds or None if none were found.
        """

        q = Search(module="Object")
        q.addCriterion(
            operator="equalsField", field="ObjObjectNumberTxt", value=identNr
        )
        q.addField(field="ObjObjectNumberTxt")
        m = self.mpapi.search2(query=q)
        positiveIDs = set()

        if m.totalSize(module="Object") == 0:
            return None
        else:
            for itemN in m.iter(module="Object"):
                objId = itemN.get("id")
                positiveIDs.add(objId)
            return positiveIDs


