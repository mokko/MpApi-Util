"""
Definitions
- Unless otherwise noted identNr are str extracted from filenames.
- objNumber is a value from ObjObjectNumberVrt.
- objId is the ID of an object.

We want to cache objId to reduce number of HTTP requests to RIA.

Every record can have only one objId, but it's conceivable that one identNr exists in multiple records.
It's also possible that one object has multiple different identNr.

cache = {
    "identNr1": [123456, 123457]
}

The question is if we also want to store the objNumber since we're not sure if objNumber is always equal
to the identNr?

cache = {
    "identNr1": {
        "objId": [123456, 123457]
        "objNumber": "objNumber1"
}

Do we need this for mulIds too?

Usage:
    ident_cache_strict = Ident_Cache()
    ident_cache_strict.get_strict(identNr="VII c 123 a")

    ident_cache_lax = Ident_Cache()
    beginswith_cache.get_begins_with(identNr="VII c 123 a")

"""
from dataclass import dataclass, field

class Ident_Cache:
    def __init__(self) -> None:
        cache_strict = {}
        cache_begins_with = {}

    def get_strict(self, *, as_str:str) -> IdentNr:
        if identNr in cache_strict:
            return cache_strict[identNr]
        else:
            objIds = self.ria.get_strict(identNr=identNr)
            identNr = IdentNr(as_str=identNr, objIds=objIds)
            cache_strict[identNr] = identNr 
            return objIds


    def get_begins_with(self, *, as_str:str) -> IdentNr:
        if as_str in cache_strict_begins_with:
            return cache_begins_with[as_str]
        else:
            objIds = self.ria.get_strict(identNr=as_str) # should return new identNr 
            identNr = IdentNr(as_str=identNr, objIds=objIds, objNumber)
            cache_begins_with[as_str] = identNr
            return objIds

        

@dataclass(slots=True)
class IdentNr:
    """
    To cache identNr that were extracted from filenames and their corresponding objIds.
    There can be multiple objIds for each identNr
    """
    as_str:str
    objNumber:str
    objIds:field(default_factory=list)