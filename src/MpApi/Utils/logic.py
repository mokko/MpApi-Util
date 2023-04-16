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

    # VII c 86 a -A x.tif    -> VII c 86 a
    # VII c 86 a <1>-A x.tif -> VII c 86 a <1>
    m = re.search(r"([\w\d +.,<>-]+)", stem)
    if m:
        astr = m.group(1).strip()
        alist = astr.split(" ")
        if "<" in astr:
            new = " ".join(alist[0:5])
        else:
            new = " ".join(alist[0:4])

        new2 = re.sub(r"-[A-Z]+", "", new).strip()
        # if there is a trailing + oder -, delete that
        new3 = re.sub(r"[\+-] *$| -3D|_ct", "", new2).strip()

        # only allow patterns that have one space separated number
        # number can be sole item if objId is used as identNr
        match = re.search(r" \d+", new3)
        if match:
            #print(new3)
            return new3
    # else
    #     return None
