"""
count the files in this directory potentially recursively
"""

import argparse
from collections import defaultdict
from pathlib import Path
from tqdm import tqdm

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
    help="speficy if you want the total size of all counted files",
    action="store_true",
)

args = parser.parse_args()

print(f"Looking for {args.filemask}")
src_dir = Path()
c = 1  # counting files
total_size: float = 0  # KB
by_ext = defaultdict(dict)
by_ext["total"]["size"] = 0
by_ext["total"]["number"] = 0

problems = []
with tqdm(desc="files") as pbar:
    for f in src_dir.glob(args.filemask):
        if f.is_dir():  # don't count dirs
            continue
        try:
            size = f.stat().st_size
            # usually fails for files with path > 255 chars
        except:
            problems.append(str(f))
            continue  # ignore files with problems

        suffix = f.suffix

        try:
            by_ext[suffix]["number"] += 1
        except:
            by_ext[suffix]["number"] = 0
            by_ext[suffix]["size"] = 0
        by_ext[suffix]["size"] += size
        by_ext["total"]["size"] += size
        pbar.update()
        c += 1
by_ext["total"]["number"] = c  # only update once

if args.size:
    size, unit = _convert(total_size)
    print(f"files found: {c}; total size {size:.2f} {unit}; problems {len(problems)}")
    _print_info(by_ext)
    if len(problems) > 0:
        print("PROBLEMS")
        for f in problems:
            print(f)
else:
    print(f"files found: {c}")
    _print_info(by_ext)

#
#
#


def _convert(size):
    units = ["bytes", "KB", "MB", "GB", "TB"]
    i = 0
    while i <= 4:
        if size > 1024:
            size /= 1024
            i += 1
        else:
            break
    return size, units[i]


def _print_info(by_ext):
    for suffix in by_ext:
        size_gb = by_ext[suffix]["size"] / 1024 / 1024 / 1024
        print(f"{by_ext[suffix]['number']} {size_gb} GB")
