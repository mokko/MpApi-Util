"""Higer-level tools for MpApi, the unofficial MuseumPlus Client"""

__version__ = "0.0.3"
credentials = "credentials.py"  # expect credentials in pwd

import argparse

from mpapi.client import MpApi
from MpApi.Utils.du import Du
from MpApi.Utils.rename import Rename
from MpApi.Utils.bcreate import Bcreate
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


def bcreate():
    parser = argparse.ArgumentParser(
        description="bcreate - create Object records for assets"
    )
    parser.add_argument(
        "-c", "--conf", help="location of configuration file", default="bcreate.ini"
    )
    parser.add_argument(
        "-j", "--job", help="job from the configuration to execute", default="test"
    )
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )
    args = parser.parse_args()

    if args.version:
        print (f"Version: {__version__}")
        sys.exit(0)

    if not args.conf or not args.job:
        raise SyntaxError ("-p parameter and -j job name required!")

    if not baseURL or not user or not pw:
        raise SyntaxError ("Missing user baseURL or pw. Are you in the right dir?")

    bc = Bcreate(baseURL=baseURL, confFN=args.conf, job=args.job, pw=pw, user=user)


def prepareUpload():
    parser = argparse.ArgumentParser(description="prepare - prepare for asset upload")
    parser.add_argument(
        "-c", "--conf", help="location of configuration file", default="prepare.ini"
    )
    parser.add_argument("-j", "--job", help="job inside config file", default="test")
    parser.add_argument("-l", "--limit", help="stop after number of items", default=-1)
    parser.add_argument(
        "-p", "--phase", help="phase to run (scandir, checkria, create)", 
        choices = ['scandisk','checkria', 'createobjects']
    )
    parser.add_argument(
        "-v", "--version", help="display version information", action="store_true"
    )

    args = parser.parse_args()

    if args.version:
        print (f"Version: {__version__}")
        sys.exit(0)

    if not args.phase:
        raise SyntaxError ("-p parameter required!")
        
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
    elif args.phase == "createobjects":  
        p.create_objects()

def update_schemas():

    """
        CLI USAGE
        update_schema_db -e excel.xlsx      # xlsx as written by prepare
        update_schema_db -f bla.xml         # looks thru a file
        update_schema_db -i "VII c 123 a-c" # looks identNr up online
        update_schema_db -v version

        -s (optional) use schemas.json file instead of default
    """
            

    parser = argparse.ArgumentParser(
        description="parse zml for schema information"
    )
    parser.add_argument("-e", "--excel", help="Look for identNrs in excel file (from prepare)")
    parser.add_argument("-f", "--file", help="Use identNr from zml file")
    parser.add_argument("-i", "--individual", help="Lookup indiovidual identNr in RIA")
    parser.add_argument("-s", "--schemas_fn", help="Path to schemas.json file; default is flit's location 'src/data'")
    parser.add_argument("-v", "--version", help="Display version info and exit", action="store_true")
    args = parser.parse_args()

    if args.schemas_fn is None: # setting default
        print ("Using default schemas file.")
        f = IdentNrFactory()
    else:
        print (f"Using user supplied schemas file '{args.schemas_fn}'.")
        f = IdentNrFactory(schemas_fn=args.schemas_fn)

    if args.version:
        print (f"Version: {__version__}")
        sys.exit(0)
    elif args.excel is not None:
        print ("Excel function not yet implemented")
        #f.update_schema_db(excel_fn=args.excel)        
        sys.exit(0)
    elif args.file is not None:
        for chunk_fn in iter_chunks(first=args.file):
            print (f"Loading file {chunk_fn}")
            f.update_schemas(file=chunk_fn)
        sys.exit(0)
    elif args.individual is not None:
        c = MpApi(baseURL, user=user, pw=pw)
        q = Search(module="Object")
        q.addCriterion()
        m = c.search2(query=q)
        f.update_schema_db(data=m)
        sys.exit(0)
    else:
        raise ValueError ("Nothing to do!")


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
