"""
Let's try to further automate the Koloß import.

(1) Loop through film dirs
(2) copy Konvolut-DS and to create template record (objId)
(3) make a prepare.xlsx with objID from template record 
(4) copy upload-empty.xlsx
(5) move -As before -Bs
"""

from mpapi.constants import get_credentials
from mpapi.client import MpApi
from mpapi.module import Module
from mpapi.search import Search
from MpApi.Utils.AssetUploader import AssetUploader
from MpApi.Utils.prepareUpload import PrepareUpload
import os
from pathlib import Path
import shutil

user, pw, baseURL = get_credentials()
client = MpApi(baseURL=baseURL, pw=pw, user=user)
upload_src = r"\\pk.de\smb\Mediadaten\Projekte\AKU\MDVOS-Bildmaterial\FINAL_EM_Afrika_Dia Smlg_Koloß\upload14-empty.xlsx"


def copy_upload(p: Path) -> None:
    """
    Copy an empty upload.xlsx into the film dir.
    """
    upload_fn = p / "upload14.xlsx"
    if not upload_fn.exists():
        print("   Copying upload14.xlsx")
        shutil.copy(upload_src, upload_fn)
    # else:
    #    print("   Upload.xlsx exists already")


def main(limit: int = -1):
    p = Path(
        r"\\pk.de\smb\Mediadaten\Projekte\AKU\MDVOS-Bildmaterial\FINAL_EM_Afrika_Dia Smlg_Koloß"
    )
    c = 1
    for pp in sorted(p.iterdir()):
        try:
            no = int(pp.name.split()[-1])
        except:
            no = 0
        print(f"{no=}")
        if pp.is_dir():
            print(f"{c}:{pp}\n")
            # prepare_init(pp)
            # copy_upload(pp)
            # if no >= 22511:
            #    prepare_scandir(pp)
            if no >= 22512 and no < 22528:  # 22528:
                # prepare_checkria(pp)
                # prepare_createobjects(pp)
                upload_assets(pp)
            if no == 22528:
                print("Highest no reached!")
                break
        if c == limit:
            print("Limit reached!")
            break
        c += 1


def prepare_checkria(p: Path) -> None:
    os.chdir(p)
    prep = PrepareUpload()
    prep.checkria()
    os.chdir("..")


def prepare_createobjects(p: Path) -> None:
    os.chdir(p)
    prep = PrepareUpload()
    prep.create_objects()
    os.chdir("..")


def prepare_init(p: Path) -> None:
    """
    Create a prepare.xlsx if it doesn't exist yet.
    """
    prepare_fn = p / "prepare.xlsx"
    if not prepare_fn.exists():
        print("   Creating prepare...")
        m = _query_film_record(p.name)
        template_id = _copy_film(m)
        # prepare_fn.unlink() overwrite
        _init_prepare(p, template_id)
    # else:
    #    print(f"{prepare_fn} exists already")


def prepare_scandir(p: Path) -> None:
    os.chdir(p)
    prep = PrepareUpload()
    prep.scan_disk()
    os.chdir("..")


def upload_assets(p: Path) -> None:
    _mv_As_before_Bs(p)
    os.chdir(p)
    uploader = AssetUploader()
    uploader.scandir()
    uploader.set_standardbild()
    uploader.go()
    os.chdir("..")


#
# private
#


def _copy_film(data: Module) -> int:
    """
    Receive a record and copy that to be used a template. Return the objId of the newly
    created record.
    """
    objId = client.createItem3(data=data)
    return objId


def _init_prepare(p: Path, objId: int):
    """
    Execute init prepare -s objId
    """
    os.chdir(p)
    prep = PrepareUpload()
    prep.init(objId)
    os.chdir("..")


def _mv_As_before_Bs(p: Path):
    print("mv As before Bs")
    for pp in Path(p).glob("**/* -B.tif"):
        parts = pp.stem.split()[:-1]
        parts.append("-A.tif")
        correspondinga = pp.parent / " ".join(parts)
        # print(f"{pp}")
        # print(".", end="")
        if correspondinga.exists() and correspondinga.parent != "Ausrichtung":
            new_dir = pp.parent / "Ausrichtung"
            if not new_dir.exists():
                print(f"mkdir {new_dir}")
                new_dir.mkdir(exist_ok=True)
            print(f"Moving {correspondinga.name}")
            shutil.move(correspondinga, new_dir)
            # raise Exception("Wait")


def _query_film_record(identNr: str) -> Module:
    """
    Receive the identNr of a film record and return that record
    """
    q = Search(module="Object")
    print(f"query {identNr}")
    q.addCriterion(operator="equalsField", field="ObjObjectNumberVrt", value=identNr)
    q.validate(mode="search")
    m = client.search2(query=q)
    if len(m) > 1:
        raise TypeError("ERROR: More than one!")
    return m


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Automation for Heike")
    parser.add_argument("-l", "--limit", help="Stop after limit steps", default=-1)
    args = parser.parse_args()

    main(limit=int(args.limit))
