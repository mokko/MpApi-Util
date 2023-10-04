"""
count the files in this directory potentially recursively
"""

import argparse
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
c = 1  # count
total_size: float = 0  # KB
with tqdm(desc="files") as pbar:
    for f in src_dir.glob(args.filemask):
        pbar.update()
        if args.size:
            total_size += f.stat().st_size
        # print (f)
        c += 1

if args.size:
    units = ["bytes", "KB", "MB", "GB", "TB"]
    i = 0
    while i <= 4:
        if total_size > 1024:
            total_size /= 1024
            i += 1
        else:
            break
    print(f"files found: {c}; total size {total_size:.2f} {units[i]}")
else:
    print(f"files found: {c}")
