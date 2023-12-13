"""
Operations (functions) on filenames that typically have to do with IdentNr.

e.g.
- extract IdentNr from filename
- check if filename is suspicious

Reoccuring logic that doesn't interface Excel and the RIA API. Reocurring Excel stuff goes 
into BaseApp.py. Reoccuring API stuff goes into RIA.py. Perhaps I will find a better name
for this package.

Module or a set ?
"""

from pathlib import Path
import re
from typing import Any


def extractIdentNr(*, path: Path) -> str | None:
    """
    extracts IdentNr (=identifier, Signatur) from filename (as Pathlib path). Developed
    specifically for cataogue cards and not widely tested beyond.
    """
    # stem as determined by path is everything before the last .suffix.
    stem = path.stem

    # step 1: collapse all underlines into space
    stem2 = re.sub("_", " ", stem)
    # step 2: all allowed chars
    m = re.search(r"([()\w\d +.,<>-]+)", stem2)
    if m:
        astr = m.group(1).strip()
        # step 3: cut the tail
        astr = re.sub(r" -KK[ \w]*| -\w+", "", astr)
        # print(f"{astr=}")

        # restrict to max length of elements
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
            # add a magic dot
            new = re.sub("Verz BGAEU", "Verz. BGAEU", new)
        elif astr.startswith("EJ ") or astr.startswith("Inv "):
            # not catching __0001 correctly...
            new = " ".join(alist[0:2])
        elif astr.startswith("Adr (EJ)"):
            new = " ".join(alist[0:3])
        elif astr.startswith("VIII "):
            new = " ".join(alist[0:3])
        elif astr.startswith("I C "):
            new = astr.split(" mit ")[0]
        # print (f"{new=}")

        # remove certain trails
        new2 = re.sub(r"   |-[A-Z]+", "", new).strip()
        # if there is a trailing + oder -, delete that
        new3 = re.sub(r"[\+-] *$| -3D|_ct", "", new2).strip()
        # print (f"{new3=}")

        # only allow patterns that have one space separated number
        if re.search(r"\w+ \d+|", new3):
            # print(f"XXXXXXXXXXXXXXXXXXX{new3}")
            return new3
        elif re.search(r"\d+", stem2):
            # number can be sole item e.g. if objId is used as identNr
            return stem2
    return None  # make mypy happy


def has_parts(identNr: str) -> bool:
    """
    For a given identNr determine if it describes a part of not.

    Examples for parts:
    VII a 123 a
    VII a 123 a,b
    VII a 123 a-c
    IV 124 a <1>
    IV 124 a,b
    """
    parts = identNr.split(" ")
    if "<" in parts[-1] and ">" in parts[-1]:
        parts.pop()
    if re.search("[a-z]+|[a-z]+-[a-z]+|[a-z],[a-z]", parts[-1]):
        return True
    return False


def is_suspicious(identNr: str) -> bool:
    """
    Checks whether identNr looks suspicious or like a valid identNr.
    Returns True if it looks suspicious, False if it looks good.
    """
    # print(f"***{identNr}")
    if not isinstance(identNr, str):
        return True

    if identNr.isspace():
        return True  # consists only of space

    # more than five parts
    partsL = identNr.split(" ")
    if len(partsL) < 0 or len(partsL) > 5:
        # print(f"'{identNr}' Too few or too many parts")
        return True

    # has to have at least one number component
    any_number = False
    for part in partsL:
        if re.match(r"\d+", part):
            any_number = True
    if not any_number:
        # print(f"'{identNr}' not any number")
        return True

    # may not have >2 consecutive spaces
    if re.search(r"\s{2,}", identNr):
        # print(f"'{identNr}' 2+ white space")
        return True

    # may not have unbalanced brackets
    brackets = (("(", ")"), ("<", ">"), ("[", "]"))
    for btype in brackets:
        if identNr.count(btype[0]) != identNr.count(btype[1]):
            return True

    # may not have brackets with inside space ( ex )
    if re.search(r"\w+\(|\)\w+", identNr):
        return True

    # may not have suspicious characters
    for char in (";", "[", "]"):
        if char in identNr:
            return True

    # may not have >1 comma
    if identNr.count(",") > 1:
        return True

    # identNr is NOT suspicious
    return False


def not_suspicious(identNr: str) -> bool:
    if is_suspicious(identNr=identNr):
        return False
    else:
        return True


def whole_for_parts(identNr: str) -> str:
    """
    For a given identNr return the whole. If it is a whole already, return as is.
    """
    if has_parts(identNr):
        parts = identNr.split(" ")
        disamb = ""
        if "<" in parts[-1] and ">" in parts[-1]:
            disamb = parts.pop()
        parts.pop()  # rm parts info
        whole_ident = " ".join(parts)
        if disamb != "":
            whole_ident += " " + disamb
        return whole_ident
    else:
        return identNr
