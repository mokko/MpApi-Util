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
from MpApi.Utils.BaseApp import BaseApp, NoContentError


if __name__ == "__main__":
    base = BaseApp()
    creds = base._read_credentials()
    client = MpApi(baseURL=creds["baseURL"], user=creds["user"], pw=creds["pw"])
    m = client.getOrgUnits2(mtype="Object")
    fn = "writableOrgUnits.xml"
    print(f"Writing to {fn}")
    m.toFile(path=fn)
