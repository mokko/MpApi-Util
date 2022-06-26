"""Higer-level tools for MpApi, the unofficial MuseumPlus Client"""

__version__ = "0.0.1"
credentials = "credentials.py"  # expect credentials in pwd

import argparse

from MpApi.Util.du import Du
from MpApi.Util.rename import Rename
from MpApi.Util.bcreate import Bcreate
from pathlib import Path

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


def bcreate():
    parser = argparse.ArgumentParser(
        description="bcreate - create Object records for assets"
    )
    parser.add_argument(
        "-c", "--conf", help="directory to start the search", required=True
    )
    parser.add_argument(
        "-j", "--job", help="job from the configuration to execute", required=True
    )
    args = parser.parse_args()
    bc = Bcreate(baseURL=baseURL, confFN=args.conf, job=args.job, pw=pw, user=user)
