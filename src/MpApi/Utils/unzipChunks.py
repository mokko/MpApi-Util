"""
Little script that unzips a series of zipped chunks

USAGE
    from unzipChunks import iter_chunks
    for chunk_fn in iter_chunks(first="path/to/chunk1.zip"):
        do_something()
    unzip
CLI USAGE
    unzipChunks -f [--first] path/to/chunk.zip 

"""

import argparse
from pathlib import Path
from zipfile import ZipFile
from typing import Iterator
import re

def iter_chunks(*, first:str) -> Iterator[str]:
    fn = Path(first)
    parent_fn = fn.parent
    stem = str(fn).split(".")[0]
    suffixes = fn.suffixes
    m = re.search(r"([-\w\d]+)(\d+)$", stem)
    if m:
        beginning = m.group(1)
        no = int(m.group(2))
    else:
        raise ValueError (f"filename not recognized {stem}")

    #print (f"{beginning} {no} {suffixes}")
    while fn.exists():
        yield fn
        no += 1
        new_name = f"{beginning}{no}" + "".join(suffixes)
        fn = parent_fn / new_name


def unzip(*, file:str) -> None:
    file = Path(file)
    if str(file.suffix).lower() == ".zip":
        parent_dir = file.parent
        member = Path(file.name).with_suffix(".xml")
        temp_fn = parent_dir / member
        with ZipFile(file, "r") as zippy:
            zippy.extract(str(member), path=parent_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="unzip a series of chunks"
    )
    parser.add_argument("-f", "--first", help="path to first chunk", required=True)
    args = parser.parse_args()

    for fn in iter_chunks(first=args.first):
        xml = fn.with_suffix(".xml")
        if xml.exists():
            print (f"{xml} exists already")
        else:
            print (f"Unzipping {fn}")
            unzip(file=fn)
    

