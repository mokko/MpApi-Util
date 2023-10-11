"""
count the files in this directory potentially recursively
"""

import argparse
from collections import defaultdict
from pathlib import Path
from tqdm import tqdm
messages = []

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
    for suffix in sorted(by_ext):
        size, unit = _convert(by_ext[suffix]["size"])
        pw(f"'{suffix}' {by_ext[suffix]['number']} {size:.2f} {unit}")

def pw(msg):
    """print and write to file"""
    messages.append(msg)
    print(msg)

def write_messages():
    with open("count.txt", "w") as f:
        for msg in messages:
            f.write(msg+"\n") 
#
#
#    

if __name__ == "__main__":

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

    src_dir = Path()
    pw(f"Looking for {args.filemask} in {src_dir.cwd()}")
    c = 0  # counting files
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
                # may fail for files with path > 255 chars
            except:
                problems.append(str(f))
                continue  # ignore files with problems

            suffix = f.suffix
            try:
                by_ext[suffix]["number"] += 1
            except:
                by_ext[suffix]["number"] = 1
                by_ext[suffix]["size"] = 0
            by_ext[suffix]["size"] += size
            by_ext["total"]["size"] += size
            pbar.update()
            c += 1
    by_ext["total"]["number"] = c  # only update once
    if args.size:
        s, unit = _convert(by_ext["total"]["size"])
        pw(f"files found: {c}; total size {s:.2f} {unit}; problems {len(problems)}")
        _print_info(by_ext)
        if len(problems) > 0:
            pw("PROBLEMS")
            for f in problems:
                pw(f)
    else:
        pw(f"files found: {c}")
        _print_info(by_ext)
    write_messages()

