"""Higer-level tools for MpApi, the unofficial MuseumPlus Client in Python"""

__version__ = "0.0.10"  # include becky
import argparse

from mpapi.client import MpApi
from mpapi.search import Search
from mpapi.constants import get_credentials
from MpApi.Utils.AssetUploader import AssetUploader
from MpApi.Utils.Attacher import Attacher
from MpApi.Utils.attach2 import Attacher2
from MpApi.Utils.becky.becky import becky_main
from MpApi.Utils.identNr import IdentNrFactory
from MpApi.Utils.count import counter
from MpApi.Utils.mover import Mover
from MpApi.Utils.prepareUpload import PrepareUpload
from MpApi.Utils.reportX import ReportX
from MpApi.Utils.sren import Sren
from MpApi.Utils.unzipChunks import iter_chunks
from MpApi.Utils.mk_grp import MakeGroup

from pathlib import Path
import subprocess
import sys

user, pw, baseURL = get_credentials()


def attacher():
    # load credentials inside attacher from comon file
    parser = argparse.ArgumentParser(
        description="attach an asset file to a multimedia record and download it"
    )
    parser.add_argument(
        "cmd",
        choices=["up", "down"],
        help="up or down for uploading/attaching a file to an asset record or downloaing or getting it",
    )
    parser.add_argument("-f", "--file", help="path to file for upload")
    parser.add_argument("-i", "--ID", help="ID of asset record", required=True)
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )
    args = parser.parse_args()
    a = Attacher()
    # an asset can only have one attachment
    match args.cmd:
        case "up":
            if not args.file:
                raise SyntaxError("ERROR: Need path to file for upload!")
            a.up(ID=args.ID, file=args.file)
        case "down":
            # Do we want to save with original filename?
            # We definitely dont want to overwrite existing files
            a.down(ID=args.ID)
        case _:
            print(f"Unknown command '{args.cmd}'")


def attacher2():
    parser = argparse.ArgumentParser(
        description="for assets without attachment, try to locate missing files and attach them."
    )
    parser.add_argument(
        "cmd",
        choices=["ria", "scandir", "up"],
        help="",
    )
    parser.add_argument(
        "-a",
        "--act",
        help="Should we really upload or only show what to upload?",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-c",
        "--cache",
        action="store_true",
        help="run a new search (False) or use file cache with results (True)",
        default=False,
    )
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )
    args = parser.parse_args()

    a = Attacher2(cache=args.cache, act=args.act)
    match args.cmd:
        case "ria":
            a.ria()
        case "scandir":
            a.scandir()
        case "up":
            a.up()


def becky():
    parser = argparse.ArgumentParser()
    parser.add_argument("conf", help="Location of becky_conf.toml")
    parser.add_argument("-a", "--act", help="Actually change RIA", action="store_true")
    parser.add_argument(
        "-l",
        "--limit",
        help="Stop after a number of rows in Excel file are processed.",
        type=int,
    )
    args = parser.parse_args()
    becky_main(conf_fn=args.conf, limit=args.limit, act=args.act)


def count():
    parser = argparse.ArgumentParser(
        description="attach an asset file to a multimedia record and download it"
    )

    parser.add_argument(
        "-f",
        "--filemask",
        help="specify a filemask if you want; defaults to '**/*' ",
        default="**/*",
    )
    parser.add_argument(
        "-s",
        "--size",
        help="show size?",
        action="store_true",
    )
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )

    args = parser.parse_args()

    src_dir = Path()
    counter(src_dir=src_dir, filemask=args.filemask, show_size=args.size)


def mk_grp():
    parser = argparse.ArgumentParser(
        description="Create (make) a ObjectGroup in RIA based on an *.xlsx with objIds"
    )
    parser.add_argument("-c", "--col", help="column as 0-based integer", required=True)
    parser.add_argument("-f", "--file", help="location of excel file", required=True)
    parser.add_argument(
        "-l",
        "--limit",
        help="line in excel file at which tasks are interrupted",
        default=-1,
    )
    parser.add_argument("-s", "--sheet", help="Title of sheet to use", required=True)
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )
    args = parser.parse_args()
    maker = MakeGroup(col=args.col, file=args.file, sheet=args.sheet, limit=args.limit)


def move():
    parser = argparse.ArgumentParser(
        description="move asset files that are alreay in RIA to storage location"
    )
    parser.add_argument(
        "first",
        nargs="?",
        help="command, either init, scandir or move",
        choices=["init", "move", "scandir", "wipe"],
    )
    parser.add_argument("-l", "--limit", help="stop after number of files", default=-1)
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )

    args = parser.parse_args()

    m = Mover(limit=args.limit)
    match args.first:
        case "init":
            m.init()
        case "move":
            m.move()
        case "scandir":
            m.scandir()
        case "wipe":
            m.wipe()
        case _:
            print(f"Unknown command '{args.cmd}'")


def prepareUpload():
    parser = argparse.ArgumentParser(description="prepare - prepare for asset upload")
    parser.add_argument(
        "phase",
        nargs="?",
        help="phase to run",
        choices=["checkria", "createobjects", "init", "scandir"],
    )
    parser.add_argument("-l", "--limit", help="stop after number of items", default=-1)
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )

    args = parser.parse_args()

    if not args.phase:
        raise SyntaxError("ERROR: Phase required!")

    p = PrepareUpload(
        limit=args.limit,
    )
    match args.phase:
        case "init":
            p.init()
        case "scandir":
            p.scan_disk()
        case "checkria":
            p.checkria()
        case "movedupes":
            print("* About to move dupes; make sure you have called checkria before.")
            p.mv_dupes()
        case "createobjects":
            p.create_objects()
        case _:
            print(f"Unknown command '{args.phase}'")


def reportX():
    """
    Write an xlsx report on the files present in the current directory (recursively)
    """
    parser = argparse.ArgumentParser(
        description="Write an xlsx report on the files present in the current directory"
    )
    parser.add_argument(
        "-l",
        "--limit",
        help="Stop the scan after specified number of files",
        default=-1,
    )
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )
    args = parser.parse_args()
    r = ReportX(limit=args.limit)
    r.write_report("reportx.xlsx")


def restart():
    """
    restart a shell command several times or infinitely.
    USAGE:
        restart -x 3 echo m
        restart echo m

    Interrupt with CTRL+C
    """
    import time

    if sys.argv[1] == "-x":
        start = 3
        times = int(sys.argv[2])
    else:
        start = 1
        times = -1

    new_call = sys.argv[start:]  # e.g. restart upload cont -> upload cont
    while times > 0 or times < 0:
        retval = subprocess.run(new_call, shell=True)
        if times % 2 == 0:
            time.sleep(60)
        times -= 1
        # if retval == 0:
        #    break


def sren():
    """
    Simple tool to rename files in current directory.
    USAGE:
        sren add -KK          # adds -KK before suffix to every file
        sren add -KK -f **/*  # search is recursive
        sren add -KK -f *.jpg # normal pathlib filemask
        sren replace - _      # replace - with _ in filename excluding suffixes

    By default, sren only shows what it would do, to actually rename something use the
    -a switch.
    """

    parser = argparse.ArgumentParser(
        description="Simple tool to rename files in current directory"
    )
    parser.add_argument(
        "-a", "--act", help="actually do the changes", action="store_true"
    )
    parser.add_argument(
        "-f",
        "--filemask",
        help="supply filemask for pathlib",
    )
    parser.add_argument("-l", "--limit", help="stop after limit", default=-1)
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )
    parser.add_argument(
        "cmd",
        help="string that will be added to end of every filename",
        choices=("add", "replace", "rsuffix"),
    )

    parser.add_argument(
        "first",
        help="first string, required",
    )

    parser.add_argument("second", help="second string", nargs="?", default=False)

    args = parser.parse_args()

    r = Sren(act=args.act, filemask=args.filemask, limit=args.limit)
    match args.cmd:
        case "add":
            r.add(args.first)
        case "replace":
            r.replace(args.first, args.second)
        case "rsuffix":
            r.replace_suffix(args.first, args.second)
        case _:
            raise SyntaxError(f"Error: Unknown command {args.cmd}")


def upload():
    """
    CLI USAGE:
    upload cont    # continous upload
    upload init    # writes empty excel file at conf.xlsx; existing files not overwritten
                   # and scans current directory preparing for upload
    upload photo   # lookup photographerIDs
    upload standardbild # only set standardbild
    upload up      # initiates or continues for upload process
    upload wipe    # wipe all data rows in Excel so that init state is re-created
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
        choices=("cont", "init", "photo", "scandir", "standardbild", "up", "wipe"),
    )
    parser.add_argument(
        "-l", "--limit", help="break the go after number of items", default=-1
    )
    parser.add_argument(
        "-v", "--version", help="display version info and exit", action="store_true"
    )

    args = parser.parse_args()

    u = AssetUploader(limit=args.limit)
    match args.cmd:
        case "cont":
            c = 1
            u = AssetUploader()
            ioffset = u.initial_offset()
            print(f"   initial offset: {ioffset}")
            csize = 5000
            while True:
                limit = c * csize + ioffset
                offset = (c - 1) * csize + ioffset
                print(f"Setting {offset=} and {limit=} ")
                u = AssetUploader(limit=limit, offset=offset)
                # u.xls.backup_excel()
                u.scandir(offset=offset)
                u.go()
                c += 1
        case "photo":
            u.photo()
        case "init":
            u.init()
        case "scandir":
            u.scandir()
        case "standardbild":
            u.standardbild()
        case "up":
            u.go()
        case "wipe":
            u.wipe()
        case _:
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

    if args.excel is not None:
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
