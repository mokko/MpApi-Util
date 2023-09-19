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
    # stem as determined by path is everything before the last .suffix.
    stem = path.stem

    # collapse all underlines into space
    stem2 = re.sub("_", " ", stem)
    m = re.search(r"([()\w\d +.,<>-]+)| -KK| -\d| \d+|  \d+", stem2)
    if m:
        # restrict to max length of elements
        astr = m.group(1).strip()
        # print(f"{astr=}")
        alist = astr.split(" ")
        if "<" in astr:
            new = " ".join(alist[0:5])
        else:
            new = " ".join(alist[0:4])

        # special cases
        if astr.startswith("I MV"):
            # adding a magic slash.
            # It's magic because it's not there in the filename
            # some have different length I/MV 0950 a
            new = re.sub("I MV", "I/MV", new)
            m = re.search(r"(I/MV \d+) (\d)", new)
            # add spitze klammern
            if m:
                new = f"{m.group(1)} <{m.group(2)}>"
        elif astr.startswith("Verz BGAEU"):
            # new = " ".join(alist[0:3])
            new = re.sub("Verz BGAEU", "Verz. BGAEU", new)
        elif astr.startswith("EJ ") or astr.startswith("Inv "):
            # not catching __0001 correctly...
            new = " ".join(alist[0:2])
        elif astr.startswith("Adr (EJ)"):
            new = " ".join(alist[0:3])

        # print (f"{new=}")

        # remove certain trails
        new2 = re.sub(r"   |-[A-Z]+", "", new).strip()
        # if there is a trailing + oder -, delete that
        new3 = re.sub(r"[\+-] *$| -3D|_ct", "", new2).strip()
        # print (f"{new3=}")

        # only allow patterns that have one space separated number
        if re.search(r"\w+ \d+|", new3):
            # print(f"XXXXXXXXXXXXXXXXXXX{new}")
            return new3
        elif re.search(r"\d+", stem2):
            # number can be sole item e.g. if objId is used as identNr
            return stem2
