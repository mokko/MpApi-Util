"""
A little util to practice attaching (uploading) asset files to RIA and getting
(downloading) them again.

DESIGN CHOICES
- This MpApi.Util is so little it is not even using Excel, yet it stays in MpApi.Utils.
"""

from mpapi.constants import get_credentials
from MpApi.Utils.BaseApp import BaseApp
from MpApi.Utils.Ria import RIA
from MpApi.Record import Record  # tested?
from pathlib import Path


class Attacher(BaseApp):
    def __init__(self):
        user, pw, baseURL = get_credentials()
        self.client = RIA(baseURL=baseURL, user=user, pw=pw)
        print(f"Logging in as {user} {baseURL}")

    def up(self, *, ID: int, file: str):
        p = Path(file)
        if not p.exists():
            raise FileNotFoundError(f"ERROR: File {file} not found!")
        m = self.client.mpapi.getItem2(mtype="Multimedia", ID=ID)
        if m:
            print(f"asset ID {ID} exists in RIA")
            m.toFile(path=f"multimedia{ID}.xml")
            ret = self.client.upload_attachment(file=file, ID=ID)
            print(f"return value after uploading attachment: {ret}")
            r = Record(m)
            r.set_filename(path=file)
            r.set_dateexif(path=file)
            r.set_size(path=file)
            m = r.toModule()
            r = self.client.mpapi.updateItem4(data=m)
            print(f"updateItem4 multimedia-{ID} return: {r}")
        else:
            raise Exception(f"ERROR: Asset ID '{ID}' does NOT exist!")

    def down(self, *, ID):
        """
        New version: which does repeatedly overwrite
        """
        m = self.client.mpapi.getItem2(mtype="Multimedia", ID=ID)
        if m:
            print(f"asset ID {ID} exists")
            # m.toFile(path=f"multimedia{ID}.xml")
            fn = m.xpath(
                "/m:application/m:modules/m:module/m:moduleItem/m:dataField[@name = 'MulOriginalFileTxt']/m:value"
            )[0].text
            # print (fn)
            p = Path(fn)
            if p.exists():
                print(f"overwrite existing file '{fn}'")
                x = input("Really? (y/n)")
            else:
                x = False
                print(f"writing new file '{fn}'")
            if x == "y":
                self.client.mpapi.saveAttachment(module="Multimedia", id=ID, path=fn)
        else:
            raise SyntaxError(f"ERROR: multimedia {ID} does not exist!")
