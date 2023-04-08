"""Higer-level tools for MpApi, the unofficial MuseumPlus Client"""

__version__ = "0.0.5"
import argparse

from mpapi.client import MpApi
from mpapi.search import Search
from mpapi.constants import credentials
from MpApi.Utils.AssetUploader import AssetUploader
from MpApi.Utils.du import Du
from MpApi.Utils.rename import Rename
from MpApi.Utils.identNr import IdentNrFactory, IdentNr
from MpApi.Utils.unzipChunks import iter_chunks

# from MpApi.Util.scandisk import Scandisk #mpapi.util.
from MpApi.Utils.prepareUpload import PrepareUpload  # mpapi.util.
from pathlib import Path
import sys

# we require to run these apps from the a directory which has credentials file
# not ideal. We could put it User Home dir instead if that bothers us.
if Path(credentials).exists():
    with open(credentials) as f:
        exec(f.read())


def du():
    if not Path(credentials).exists():
        raise ValueError("ERROR: Credentials not found!")
    parser = argparse.ArgumentParser(
        description="du - the download/upload tool for mpapi"
    )
    parser.add_argument("-c", "--cmd", help="'down' or 'up'", required=True)
    parser.add_argument("-i", "--input", help="path to Excel sheet", required=True)
    args = parser.parse_args()
    du = Du(cmd=args.cmd, Input=args.input, baseURL=baseURL, pw=pw, user=user)


def prepareUpload():
    parser = argparse.ArgumentParser(description="prepare - prepare for asset upload")
    parser.add_argument(
        "-c", "--conf", help="location of configuration file", default="prepare.ini"
    )
    parser.add_argument("-j", "--job", help="pick a job from the config file")
    parser.add_argument("-l", "--limit", help="stop after number of items", default=-1)
    parser.add_argument(
        "-p",
        "--phase",
        help="phase to run",
        choices=["scandisk", "checkria", "createobjects", "movedupes"],
    )
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )

    args = parser.parse_args()

    if args.version:
        print(f"Version: {__version__}")
        sys.exit(0)

    if not args.phase:
        raise SyntaxError("-p parameter required!")

    p = PrepareUpload(
        baseURL=baseURL,
        conf_fn=args.conf,
        job=args.job,
        limit=args.limit,
        pw=pw,
        user=user,
    )
    if args.phase == "scandisk":
        p.scan_disk()
    elif args.phase == "checkria":
        p.asset_exists_already()
        p.objId_for_ident()
    elif args.phase == "movedupes":
        print("* About to move dupes; make sure you have called checkria before.")
        p.mv_dupes()
    elif args.phase == "createobjects":
        p.create_objects()


def rename():
    parser = argparse.ArgumentParser(
        description="Rename tool using an Excel spreadsheet for manual check and documentation"
    )
    parser.add_argument("-s", "--src", help="Scan source directory")
    parser.add_argument("-d", "--dst", help="destination directory")
    parser.add_argument("-x", "--xsl", required=True, help="Excel file path")
    parser.add_argument(
        "-e",
        "--execute",
        action="store_true",
        help="Execute the copy prepared in the specified Excel file",
    )
    args = parser.parse_args()

    r = Rename()
    if args.src:
        # let's use the dictionary cache if, and only if, we need to find the jpg sisters
        # of the tifs
        # r.mk_cache(start_dir=src_dir)
        r.scan(src_dir=args.src, dest_dir=args.dst, xls_fn=args.xsl)
    elif args.execute:
        r.execute(xls_fn=args.xsl)


def upload():
    """
    CLI USAGE:
    upload -c init    # writes empty excel file at conf.xlsx; existing files not overwritten
    upload -c scandir # scans current directory preparing for upload
    upload -c go      # initiates or continues for upload process

    """

    parser = argparse.ArgumentParser(
        description="""Upload tool that simulates hotfolder, 
        (a) creats asset records from templates, 
        (b) uploads/attaches files from directory, 
        (c) creates a reference to object record."""
    )
    parser.add_argument("-c", "--cmd", help="use one of the following commands: init, scandir or go")
    parser.add_argument(
        "-l", "--limit", help="break the go after number of items", default=-1
    )
    parser.add_argument(
        "-v", "--version", help="display version info and exit", action="store_true"
    )

    args = parser.parse_args()
    if args.version:
        print(f"Version: {__version__}")
        sys.exit(0)

    u = AssetUploader(limit=args.limit)
    if args.cmd == "init":
        u.init()
    elif args.cmd == "scandir":
        u.scandir()
    elif args.cmd == "go":
        u.go()
    else:
        print("Unknown command")

def update_schemas():
    """
    CLI USAGE
    update_schema_db -e excel.xlsx      # xlsx as written by prepare
    update_schema_db -f bla.xml         # looks thru a file
    update_schema_db -i "VII c 123 a-c" # looks identNr up online
    update_schema_db -v version

    -s (optional) use schemas.json file instead of default
    """

    parser = argparse.ArgumentParser(description="parse zml for schema information")
    parser.add_argument(
        "-e", "--excel", help="look for identNrs in excel file (from prepare)"
    )
    parser.add_argument("-f", "--file", help="use identNr from zml file")
    parser.add_argument("-i", "--identNr", help="lookup indiovidual identNr in RIA")
    parser.add_argument(
        "-s",
        "--schemas_fn",
        help="path to schemas.json file; default is flit's location 'src/data'",
    )
    parser.add_argument(
        "-v", "--version", help="display version info and exit", action="store_true"
    )
    args = parser.parse_args()

    if args.schemas_fn is None:  # setting default
        print("Using default schemas file.")
        f = IdentNrFactory()
    else:
        print(f"Using user supplied schemas file '{args.schemas_fn}'.")
        f = IdentNrFactory(schemas_fn=args.schemas_fn)

    if args.version:
        print(f"Version: {__version__}")
        sys.exit(0)
    elif args.excel is not None:
        print("Excel function not yet implemented")
        # f.update_schemas_excel(fn=args.excel)
        sys.exit(0)
    elif args.file is not None:
        for chunk_fn in iter_chunks(first=args.file):
            print(f"Loading file {chunk_fn}")
            f.update_schemas(file=chunk_fn)
        sys.exit(0)
    elif args.identNr is not None:
        c = MpApi(baseURL=baseURL, user=user, pw=pw)
        q = Search(module="Object")
        q.addCriterion(
            operator="startsWithField",
            field="ObjObjectNumberGrp.InventarNrSTxt",
            value=args.identNr,
        )
        m = c.search2(query=q)
        print(f"{len(m)} objects found...")
        f.update_schemas(data=m)
        sys.exit(0)
    else:
        raise ValueError("Nothing to do!")
