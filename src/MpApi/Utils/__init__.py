"""Higer-level tools for MpApi, the unofficial MuseumPlus Client"""

__version__ = "0.0.6"
import argparse

from mpapi.client import MpApi
from mpapi.search import Search
from mpapi.constants import credentials
from MpApi.Utils.AssetUploader import AssetUploader
from MpApi.Utils.BaseApp import BaseApp  # , NoContentError
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
import shutil
import sys

# new style
base = BaseApp()
creds = base._read_credentials()
user = creds["user"]
pw = creds["pw"]
baseURL = creds["baseURL"]


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
        choices=["checkria", "createobjects", "init", "scandir"],
    )
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
        limit=args.limit,
    )
    if args.phase == "scandir" or args.phase == "init":
        p.scan_disk()
    elif args.phase == "checkria":
        p.checkria()
    elif args.phase == "movedupes":
        print("* About to move dupes; make sure you have called checkria before.")
        p.mv_dupes()
    elif args.phase == "createobjects":
        p.create_objects()


def ren2():
    """
    Simple rename tool that renames all files in current directory.

    You can add a string before the suffix
        ren2 add ___-KK
        before: ./file.jpg
        after:  ./file___-KK.jpg

    Or you can replace string A with another string B
        ren relpace "-" "___-KK"
        before: ./file -KK.jpg
        after:  ./file ___-KK.jpg

    Directories are untouched. Currently ren2 doesn't operate recursively.
    """

    parser = argparse.ArgumentParser(
        description="renadd - rename files in current directory by adding a string before the suffix"
    )
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )

    parser.add_argument(
        "-a", "--act", help="actually do the changes", action="store_true"
    )

    parser.add_argument(
        "cmd", help="string that will be added to end of every filename"
    )

    parser.add_argument(
        "first",
        help="first string, required",
    )

    parser.add_argument("second", help="second string", nargs="?", default=None)

    args = parser.parse_args()

    if args.version:
        print(f"Version: {__version__}")
        sys.exit(0)

    def _add(p, first):
        suffix = p.suffix
        stem = p.stem
        return f"{stem}{first}{suffix}"

    def _replace(p, first, second):
        suffix = p.suffix
        stem = p.stem
        new_stem = stem.replace(first, second)
        return f"{new_stem}{suffix}"

    if not args.act:
        print("Demo mode, not acting")
    for f in sorted(Path().glob("*")):  # not recursive
        if f.is_dir():
            continue
        if args.cmd == "add":
            new = _add(f, args.first)
        elif args.cmd == "replace":
            new = _replace(f, args.first, args.second)
        else:
            raise TypeError("ERROR: Unknown Command!")
        print(f"{f} -> {new}")
        if args.act:
            shutil.move(f, new)


def ren():
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
    upload up      # initiates or continues for upload process
    upload standardbild # only set standardbild
    """

    parser = argparse.ArgumentParser(
        description="""Upload tool that simulates hotfolder, 
        (a) creats asset records from templates, 
        (b) uploads/attaches files from directory, 
        (c) creates a reference to object record."""
    )
    parser.add_argument(
        "cmd",
        help="use one of the following commands",
        choices=("init", "scandir", "standardbild", "up"),
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
    elif args.cmd == "up":
        u.go()
    elif args.cmd == "standardbild":
        u.standardbild()
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
        print(f"looking for {args.identNr}")
        # we used to use ObjObjectNumberGrp.InventarNrSTxt
        q.addCriterion(
            operator="startsWithField",
            field="ObjObjectNumberVrt",
            value=args.identNr,
        )
        m = c.search2(query=q)
        print(f"{len(m)} objects found...")
        if len(m) > 0:
            f.update_schemas(data=m)
        sys.exit(0)
    else:
        raise ValueError("Nothing to do!")
