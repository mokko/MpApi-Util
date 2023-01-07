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
        self.client = MpApi(baseURL=baseURL, user=user, pw=pw)

    def fn_to_mulId(self, *, fn, orgUnit=None) -> Optional[set]:
        """
        For a given filename check if there is one or more assets with that same filename
        in RIA.

        Return None if there is none, or the mulIds for the records in a set.
        """
        # print (f"* Getting assets for filename '{fn}'")
        q = Search(module="Multimedia")
        # if orgUnit is not None:
        #    q.AND()
        q.addCriterion(operator="equalsField", field="MulOriginalFileTxt", value=fn)
        # if orgUnit is not None:
        #    q.addCriterion(operator="equalsField", field="__orgUnit", value=orgUnit)
        q.addField(field="__id")
        q.validate(mode="search")
        m = self.client.search2(query=q)
        positiveIDs = set()

        if m.totalSize(module="Multimedia") == 0:
            return None
        else:
            for itemN in m.iter(module="Multimedia"):
                positiveIDs.add(itemN.get("id"))
            return positiveIDs

    def objId_for_ident(self, *, identNr: str) -> set:
        """
        Lookup objIds for identNr
        """
        q = Search(module="Object")
        q.addCriterion(
            operator="equalsField", field="ObjObjectNumberTxt", value=identNr
        )
        q.addField(field="ObjObjectNumberTxt")
        m = self.client.search2(query=q)
        positiveIDs = set()

        if m.totalSize(module="Object") == 0:
            return None
        else:
            for itemN in m.iter(module="Object"):
                objId = itemN.get("id")
                positiveIDs.add(objId)
            return positiveIDs
