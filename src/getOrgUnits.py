"""
    Little script to get writable orgUnits.

CLI Usage
    getOrgUnits.py

TODO
- in the future we could make the mtype pickable thru cli

"""

# import argparse
from mpapi.client import MpApi
from mpapi.constants import get_credentials


if __name__ == "__main__":
    user, pw, baseURL = get_credentials()
    client = MpApi(baseURL=baseURL, user=user, pw=pw)
    m = client.getOrgUnits2(mtype="Object")
    fn = "writableOrgUnits.xml"
    print(f"Writing to {fn}")
    m.toFile(path=fn)
