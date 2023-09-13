"""
Reoccuring logic that doesn't interface Excel and the RIA API. Reocurring Excel stuff goes 
into BaseApp.py. Reoccuring API stuff goes into RIA.py. Perhaps I will find a better name
for this package.

Module or a set functions?
"""

from pathlib import Path
import re
from typing import Any, Optional


def extractIdentNr(*, path: Path) -> Optional[str]:
    """
    extracts IdentNr (=identifier, Signatur) from filename (as Pathlib path). Developed
    specifically for cataogue cards and not widely tested beyond.
    """
    # stem = str(path).split(".")[0] stem is everything before first .
    stem = (
        path.stem
    )  # stem as determined by path is everything before the last .suffix.

    stem2 = re.sub("_", " ", stem)

    m = re.search(r"([\w\d +.,<>-_]+)| -KK| -\d|__\d+", stem2)
    if m:
        # restrict to max length of elements
        astr = m.group(1).strip()
        # print (f"{astr=}")
        alist = astr.split(" ")
        if "<" in astr:
            new = " ".join(alist[0:5])
        else:
            new = " ".join(alist[0:4])

        if astr.startswith("I MV"):
            new = " ".join(alist[0:3])
            new = re.sub("I MV", "I/MV", new)

        # print (f"{new=}")

        new2 = re.sub(r"___|-[A-Z]+", "", new).strip()
        # if there is a trailing + oder -, delete that
        new3 = re.sub(r"[\+-] *$| -3D|_ct", "", new2).strip()
        # print (f"{new3=}")

        # only allow patterns that have one space separated number
        # number can be sole item if objId is used as identNr
        match = re.search(r"\w \d+|d+", new3)
        if match:
            return new3
