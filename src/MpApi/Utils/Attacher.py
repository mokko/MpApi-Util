"""
A little util to practice attaching (uploading) asset files to RIA and getting 
(downloading) them again.
"""

from MpApi.Utils.BaseApp import BaseApp, ConfigError
from MpApi.Utils.Ria import RIA
from pathlib import Path


class Attacher(BaseApp):
    def __init__(self):
        creds = self._read_credentials()
        self.client = RIA(baseURL=creds["baseURL"], user=creds["user"], pw=creds["pw"])

    def up(self, *, ID: int, file: str):
        p = Path(file)
        if not p.exists():
            raise FileNotFoundError(f"File {file} not found!")
        # should we check if ID exists?
        if self.client.id_exists(mtype="Multimedia", ID=ID):
            print(f"asset ID {ID} exists")
            m = self.client.mpapi.getItem2(mtype="Multimedia", ID=ID)
            m.toFile(path=f"asset{ID}.xml")
            ret = self.client.upload_attachment(file=file, ID=ID)
            print(ret)
        else:
            raise Exception(f"asset ID {ID} does NOT exist")

    def down(self, *, ID):
        print("Dowload not yet implemented!")
