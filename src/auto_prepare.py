"""
Let's try to further automate the Koloß import.

(1) Loop through film dirs
(2) copy Konvolut-DS and to create template record (objId)
(3) make a prepare.xlsx with objID from template record 
(4) move -As before -Bs
(5) trigger prepare scandir,checkria and createobjects
(6) trigger upload scandir, go
(7) upload of jpgs
(8) TODO: delete template 
"""

from mpapi.constants import get_credentials
from mpapi.client import MpApi
from mpapi.module import Module
from mpapi.search import Search
from MpApi.Utils.AssetUploader import AssetUploader
from MpApi.Utils.prepareUpload import PrepareUpload
from MpApi.Utils.Ria import RIA
import os
from pathlib import Path
import shutil

user, pw, baseURL = get_credentials()
client = MpApi(baseURL=baseURL, pw=pw, user=user)
ria = RIA(baseURL=baseURL, user=user, pw=pw)
upload_src = r"\\pk.de\smb\Mediadaten\Projekte\AKU\MDVOS-Bildmaterial\FINAL_EM_Afrika_Dia Smlg_Koloß\upload14-empty.xlsx"


def copy_upload(p: Path) -> None:
    """
    Copy an empty upload.xlsx into the film dir.
    """
    upload_fn = p / "upload14.xlsx"
    if not upload_fn.exists():
        print("   Copying upload14.xlsx")
        shutil.copy(upload_src, upload_fn)


def main(limit: int = -1, start: int = 0, stop: int = 23_088):
    p = Path(
        r"\\pk.de\smb\Mediadaten\Projekte\AKU\MDVOS-Bildmaterial\FINAL_EM_Afrika_Dia Smlg_Koloß"
    )
    for idx, pp in enumerate(sorted(p.iterdir())):
        if pp.is_dir():
            last_item = pp.name.split()[-1]
            try:
                no = int(last_item)
            except:
                no = int(last_item[:-1])
            if no < start:
                continue
            print(f"{idx}:{no=} {start=} {stop=}")
            print(f"   {pp}\n")
            copy_upload(pp)
            prepare_init(pp)
            upload_jpgs(pp)  # Übersicht. Breaks if two records with konvolut
            _mv_As_before_Bs(pp)  # before prepare_scancheckcreate

            # ONLY DO SCANDIR after we corrected orientation
            # how do we know if did that already?
            # there is no simple test...

            # prepare_scancheckcreate(pp)
            # upload_assets(pp)

            # only after successful creation of the Object records
            # rm_template(pp)
            if no >= stop:
                print("Stop reached!")
                break
        if idx == limit:
            print("Limit reached!")
            break


def prepare_init(p: Path) -> None:
    """
    Create a prepare.xlsx if it doesn't exist yet.
    """
    prepare_fn = p / "prepare.xlsx"
    if not prepare_fn.exists():
        print("   Creating prepare...")
        m = _get_film(identNr=p.name)
        template_id = client.createItem3(data=m)
        conf = {"B1": f"Object {template_id}", "B3": "*.tif", "B2": "EMAfrika1"}
        # prepare_fn.unlink() overwrite
        os.chdir(p)
        prep = PrepareUpload()
        prep.init(conf)
        os.chdir("..")


def prepare_scancheckcreate(p: Path) -> None:
    """
    Does not check if steps have been executed before, but doesn't do anything bad
    if executed repeatedly. However, we could check if individual photo records have
    already been created. For example, we could check if film record has photos as parts
    (Objektref.).
    """
    os.chdir(p)
    prep = PrepareUpload()
    prep.scan_disk()
    prep.checkria()
    prep.create_objects()
    os.chdir("..")


def rm_template(p: Path) -> None:
    """
    Let's delete the template record after we're done.

    TODO: We should check if all assets have been uploaded or something like that
    before deleting...
    """
    templateM = _get_template(identNr=p.name)
    if not templateM:
        print("Template doesn't exist anymore.")
        return
    objId = templateM.extract_first_id()
    print(f"*** Removing template record with ID {objId}")
    client.deleteItem2(mtype="Object", ID=objId)


def upload_assets(p: Path) -> None:
    """
    Does not check if steps have been executed before, but doesn't do anything bad
    if executed repeatedly.
    However, we could check if individual photo assets have already been created.
    """
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
    filmM = _get_film(identNr=p.name)

    assetL = filmM.xpath(
        """/m:application/m:modules/m:module[
        @name='Object']
    /m:moduleItem/m:moduleReference[
        @name = 'ObjMultimediaRef']/m:moduleReferenceItem"""
    )
    if len(assetL) > 0:
        print("overview jpgs seem to be already attached, not doing that again")
        return
    print("jpgs not yet attached, let me try...")

    objId = filmM.extract_first_id()
    templateM = client.getItem2(
        mtype="Multimedia", ID=7325555  # new asset record on 24.2.2024
    )  # 7306612 new template without attachment
    for idx, fn in enumerate(Path(p).glob("*.jpg")):
        uploader = AssetUploader()
        mulId = uploader._create_from_template(fn=fn, objId=objId, templateM=templateM)
        if mulId is None:
            continue  # to make mypy happy
        ret = uploader._attach_asset(path=fn, mulId=mulId)
        print(f"{mulId=} {ret=}")
        if idx == 0:
            print("Setting standardbild")
            ria.mk_asset_standardbild2(objId=objId, mulId=mulId)


#
# private
#


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


def _get_film(*, identNr: str) -> Module:
    """
    Expect the identNr of a film record ("VIII A 22510") and return that record (or item).
    The film record is also known as the Konvolut Record. It is distinct from the
    template.
    """
    q = Search(module="Object")
    print(f"query {identNr}")
    q.AND()
    q.addCriterion(operator="equalsField", field="ObjObjectNumberVrt", value=identNr)
    q.addCriterion(operator="contains", field="ObjTechnicalTermClb", value="Konvolut")
    q.validate(mode="search")
    m = client.search2(query=q)
    if len(m) > 1:
        raise TypeError("ERROR: More than one Konvolut record!")
    return m


def _get_template(*, identNr: str) -> Module:
    """
    Expect the identNr of a film record (e.g. "VIII A 22510") and return that template record.
    N.B. Untested!
    """
    q = Search(module="Object")
    print(f"query {identNr}")
    q.AND()
    q.addCriterion(operator="equalsField", field="ObjObjectNumberVrt", value=identNr)
    q.NOT()
    q.addCriterion(operator="contains", field="ObjTechnicalTermClb", value="Konvolut")
    q.validate(mode="search")
    m = client.search2(query=q)
    if len(m) > 1:
        raise TypeError("ERROR: More than one potential template!")
    return m


if __name__ == "__main__":
    # as long as this script is only used on a single upload project (i.e. Koloß slides)
    # we don't need to make it a proper script that installs properly thru Flit. If we
    # ever generalize this script to work on a other projects as well, this decision
    # needs to be revisited.

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
        default=100_000,
        type=int,
    )
    args = parser.parse_args()

    main(limit=args.limit, start=args.start, stop=args.stop)
