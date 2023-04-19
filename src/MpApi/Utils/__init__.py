"""Higer-level tools for MpApi, the unofficial MuseumPlus Client"""

__version__ = "0.0.5"
import argparse

from mpapi.client import MpApi
from mpapi.search import Search
from mpapi.constants import credentials
from MpApi.Utils.AssetUploader import AssetUploader
from MpApi.Utils.Attacher import Attacher
from MpApi.Utils.du import Du
from MpApi.Utils.rename import Rename
from MpApi.Utils.reportX import ReportX
from MpApi.Utils.mover import Mover
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


def attacher():
    # load credentials inside attacher from comon file
    parser = argparse.ArgumentParser(
        description="attach an asset file to a multimedia record and download it"
    )
    parser.add_argument(
        "cmd",
        help="up or down for uploading/attaching a file to an asset record or downloaing or getting it",
    )
    parser.add_argument("-f", "--file", help="path to file for upload")
    parser.add_argument("-i", "--ID", help="ID of asset record", required=True)
    args = parser.parse_args()
    a = Attacher()
    # an asset can only have one attachment
    if args.cmd == "up":
        if not args.file:
            raise SyntaxError("ERROR: Need path to file for upload!")
        a.up(ID=args.ID, file=args.file)
    if args.cmd == "down":
        # Do we want to save with original filename?
        # We definitely dont want to overwrite existing files
        a.down(ID=args.ID)


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


def move():
    parser = argparse.ArgumentParser(
        description="move asset files that are alreay in RIA to storage location"
    )
    parser.add_argument(
        "first",
        help="command, either init, scandir or move",
        choices=["init", "move", "rescan", "scandir"],
    )
    parser.add_argument("-l", "--limit", help="stop after number of files", default=-1)
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )

    args = parser.parse_args()
    if args.version:
        print(f"Version: {__version__}")
        sys.exit(0)
    m = Mover(limit=args.limit)
    if args.first == "init":
        m.init()
    elif args.first == "move":
        m.move()
    elif args.first == "rescan":
        m.rescan()
    elif args.first == "scandir":
        m.scandir()
    else:
        print(f"Unknown command '{args.cmd}'")


def prepareUpload():
    parser = argparse.ArgumentParser(description="prepare - prepare for asset upload")
    parser.add_argument(
        "phase",
        help="phase to run",
        choices=["checkria", "createobjects", "movedupes", "scandisk"],
    )
    parser.add_argument(
        "-c", "--conf", help="location of configuration file", default="prepare.ini"
    )
    parser.add_argument("-j", "--job", help="pick a job from the config file")
    parser.add_argument("-l", "--limit", help="stop after number of items", default=-1)
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


def reportX():
    """
    Write an xlsx report on the files present in the current directory (recursively)
    """
    # parser = argparse.ArgumentParser(
    #    description="Write an xlsx report on the files present in the current directory"
    # )
    # parser.add_argument("-s", "--src", help="Scan source directory")
    # args = parser.parse_args()

    r = ReportX()
    r.write_report("reportx.xlsx")


def upload():
    """
    CLI USAGE:
    upload init    # writes empty excel file at conf.xlsx; existing files not overwritten
    upload scandir # scans current directory preparing for upload
    upload go      # initiates or continues for upload process

    """

    parser = argparse.ArgumentParser(
        description="""Upload tool that simulates hotfolder, 
        (a) creats asset records from templates, 
        (b) uploads/attaches files from directory, 
        (c) creates a reference to object record."""
    )
    parser.add_argument(
        "cmd", help="use one of the following commands: init, scandir or go"
    )
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
        print(f"Unknown command '{args.cmd}'")


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
