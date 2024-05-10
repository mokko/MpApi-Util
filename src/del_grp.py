"""
Given the id for a object group in RIA, delete all items (records) in the group.

CAVEATS
- Deleting works only if you login with an account that has the necessary rights. If you
  dont have the correct rights, the error message is probably not very helpful
- Currently, only objects can be deleted.
"""

from mpapi.constants import get_credentials
from mpapi.client import MpApi
from mpapi.search import Search
from mpapi.module import Module
from pathlib import Path


def del_items_in_group(*, grpId: int, action: bool = False, limit: int = -1) -> None:
    print(f"Querying for group {grpId}")
    user, pw, baseURL = get_credentials()
    client = MpApi(baseURL=baseURL, user=user, pw=pw)

    out_fn = f"group-{grpId}.xml"

    if Path(out_fn).exists():
        # If you dont want the cache, delete it!
        print(f"Using cache '{out_fn}'")
        m = Module(file=out_fn)
    else:
        q = Search(module="ObjectGroup")
        q.addCriterion(operator="equalsTerm", field="__id", value=str(grpId))
        q.toFile(path="debug.query.xml")
        q.validate(mode="search")
        m = client.search2(query=q)
        m.toFile(path=f"group-{grpId}.xml")

    objL = m.xpath(
        "/m:application/m:modules/m:module/m:moduleItem/m:moduleReference/m:moduleReferenceItem/@moduleItemId"
    )  #
    for idx, objId in enumerate(objL, start=1):
        if idx > limit and limit > 0:
            print(f"Limit reached: {idx=} with limit {limit}")
            break
        if action:
            print(f"Deleting Object {objId}")
            # trying to delete a record that has already been deleted
            # results in no error message from  RIA/client atm
            client.deleteItem2(mtype="Object", ID=objId)
        else:
            print(f"Would delete Object {objId}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("grpId", type=int)
    parser.add_argument("--action", "-a", action="store_true")
    parser.add_argument("--limit", "-l", type=int, default=-1)
    args = parser.parse_args()

    del_items_in_group(grpId=args.grpId, action=args.action, limit=args.limit)
