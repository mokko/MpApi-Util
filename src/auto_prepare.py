"""
Let's try to further automate the Koloß import.

(1) Loop through film dirs
(2) copy Konvolut-DS and to create template record (objId)
(3) make a prepare.xlsx with objID from template record 
(4) copy upload-empty.xlsx
(5) move -As before -Bs

New:
-start specifies the first dir to work one
-limit dirs counts from start onwards

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


def main(limit: int = -1, start: int = 0, stop: int = 0):
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
        if pp.is_dir() and no >= start:
            print(f"{c}:{pp}\n")
            # copy_upload(pp)
            # prepare_init(pp)
            # ONLY DO SCANDIR after we corrected orientation
            # how do we know if did the handwork already?
            # there is no simple test...
            prepare_scancheckcreate(pp)
            upload_assets(pp)
            upload_jpgs(pp)
            if c == limit or no >= stop:
                print("Limit reached!")
                break
            c += 1


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


def prepare_scancheckcreate(p: Path) -> None:
    """
    Does not check if steps have been executed before, but doesn't do anything bad
    if executed again.
    """
    os.chdir(p)
    prep = PrepareUpload()
    prep.scan_disk()
    prep.checkria()
    prep.create_objects()
    os.chdir("..")


def upload_assets(p: Path) -> None:
    """
    Does not check if steps have been executed before, but doesn't do anything bad
    if executed again.
    """
    _mv_As_before_Bs(p)
    os.chdir(p)
    uploader = AssetUploader()
    uploader.scandir()
    uploader.set_standardbild()
    uploader.go()
    os.chdir("..")


def upload_jpgs(p: Path) -> None:
    """
    Create an Asset (multimedia) record by copying a template and then attach two jpgs

    How can we test if jpgs are already uploaded?
    """
    filmM = _query_film_record(p.name)

    assetL = filmM.xpath(
        """/m:application/m:modules/m:module[
        @name='Object']
    /m:moduleItem/m:moduleReference[
        @name = 'ObjMultimediaRef']/m:moduleReferenceItem"""
    )
    if len(assetL) > 0:
        print("overview jpgs seem to be already attached, not doing that again")
        return

    objId = filmM.extract_first_id()
    templateM = client.getItem2(
        mtype="Multimedia", ID=7306612
    )  # 7306612 new template without attachment
    for fn in Path(p).glob("*.jpgs"):
        uploader = AssetUploader()
        uploader._create_from_template(fn=fn, objId=objId, templateM=templateM)


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
    Receive the identNr of a film record and return that record. The film record is also
    known as the Konvolut-Record.
    """
    q = Search(module="Object")
    print(f"query {identNr}")
    q.AND()
    q.addCriterion(operator="equalsField", field="ObjObjectNumberVrt", value=identNr)
    q.addCriterion(operator="contains", field="ObjTechnicalTermClb", value="Konvolut")
    q.validate(mode="search")
    m = client.search2(query=q)
    if len(m) > 1:
        raise TypeError("ERROR: More than one!")
    return m


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Automation for Heike")
    parser.add_argument(
        "-l", "--limit", help="Stop after so many steps", default=-1, type=int
    )
    parser.add_argument(
        "-s",
        "--start",
        help="Only start at given number (VIII A no)",
        default=0,
        type=int,
    )
    parser.add_argument(
        "-o",
        "--stop",
        help="Stop at given number (VIII A no)",
        default=0,
        type=int,
    )
    args = parser.parse_args()

    main(limit=args.limit, start=args.start)