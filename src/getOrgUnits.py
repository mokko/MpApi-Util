"""
    Little script to get writable orgUnits.

CLI Usage
    getOrgUnits.py
    
TODO
- in the future we could make the mtype pickable thru cli   
    
"""
# import argparse
from mpapi.client import MpApi
from mpapi.module import Module
from pathlib import Path

credentials = "credentials.py"

if Path(credentials).exists():
    with open(credentials) as f:
        exec(f.read())


if __name__ == "__main__":
    client = MpApi(baseURL=baseURL, user=user, pw=pw)
    m = client.getOrgUnits2(mtype="Object")
    fn = "writableOrgUnits.xml"
    print(f"Writing to {fn}")
    m.toFile(path=fn)
