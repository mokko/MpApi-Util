"""
count the files in this directory potentially recursively
"""

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
    """print and also write to message cache to later write all messages to file"""
    print(msg)
    messages.append(msg)


def write_messages():
    """
    Write the messages from cache (list in message) to disc.
    """
    fn = "count.txt"
    print(f"About to write messages to {fn}")
    with open(fn, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(msg + "\n")


def counter(src_dir: Path = Path(), filemask: str = "*", size: bool = False):
    pw(f"Looking for {filemask} in {src_dir.cwd()}")
    c = 0  # counting files
    by_ext = defaultdict(dict)
    by_ext["total"]["size"] = 0
    by_ext["total"]["number"] = 0

    problems = []
    with tqdm(desc=filemask, unit=" files") as pbar:
        for f in src_dir.glob(filemask):
            if f.is_dir():  # don't count dirs
                continue
            try:
                # may fail for files with path > 255 chars
                size = f.stat().st_size
            except:
                problems.append(str(f))
                print(f"problem '{f}'")
                continue  # ignore files with problems

            suffix = f.suffix  # .jpg != .JPG
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
    if size:
        s, unit = _convert(by_ext["total"]["size"])
        pw(f"files found: {c}; total size {s:.2f} {unit}; problems {len(problems)}")
        by_ext.pop("total", None)  #  omit the total line to reduce redundancy
        _print_info(by_ext)
        if len(problems) > 0:
            pw(f"PROBLEMS {len(problems)}")
            for f in problems:
                pw(f)
    else:
        pw(f"files found: {c}")
        _print_info(by_ext)
    write_messages()
