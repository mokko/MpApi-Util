"""
Functions for dealing with identNrs originating from strings or paths.

"logic" stands for string logic for identNr.

e.g.
- extractIdentNr: extracts IdentNr from path/filename
- is_suspicious: check if filename is suspicious or not

Reoccuring logic that doesn't interface Excel and the RIA API. Reocurring Excel stuff goes
into BaseApp.py. Reoccuring API stuff goes into RIA.py. Perhaps I will find a better name
for this package.
"""

from pathlib import Path
import re
from MpApi.Utils.Xls import ConfigError


class identNrParserError:
    pass


def extractIdentNr(*, path: Path, parser: str) -> str:
    """
    extracts IdentNr (=identifier, Signatur) from filename (as Pathlib path). Developed
    specifically for cataogue cards and not widely tested beyond.

    New:
    - raises error ConfigError or identNrParserError
    """
    match parser:
        case "EM":
            return parse_EM(path)
        case _:
            raise ConfigError(f"Unknown identNr parser: {parser}!")


def fortlaufende_Nummer(identNr: str) -> str:
    """
    Return the actual fortlaufende Nummer as integer.
    
    N.B. fortlaufende Nummer is the number(actually: string) that defines the 
    main object:
    - VII c 1234 a-c: 1234
    - VII 78/0123: 0123
    """
    alist = identNr.split(" ")
    pos = fortlaufende_Nummer_pos(identNr)
    # we cant use int here because we want leading zeros 0123
    return alist[pos]


def fortlaufende_Nummer_pos(identNr: str) -> int:
    """
    Return the position of the first "fortlaufende Nummer".
    Expects a identNr-like object as string. Counts zero-based.


    New
    - identNrParserError if no fortlaufende_Nummer not found
    Todo:
        - Do we want 1-based counting?
        - Do we want to raise an error on failure?
    """
    if identNr.startswith("VII 78"):
        # also works for VII 78/
        #print("Schellack exception")
        return 2

    alist = identNr.split(" ")
    for c, elem in enumerate(alist):
        if re.fullmatch(r"\d+", alist[c]):
            return c
    raise identNrParserError("fortlaufende Nummer not found")


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


def is_suspicious(identNr: str | None) -> bool:
    """
    Checks whether identNr looks suspicious or like a valid identNr.
    Returns True if it looks suspicious, False if it looks good.
    """
    if identNr is None:
        return True

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

    # if no Roman numeral
    alist = identNr.split(" ")
    if len(alist) > 1:
        if not re.fullmatch(r"[IVXM/]+", alist[0]):
            print("no Roman numeral")  # exception for I/MV
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
    """
    Do we really need not_suspicious if we have is_suspicious?
    """
    if is_suspicious(identNr=identNr):
        return False
    else:
        return True


def parse_EM(path: Path) -> str:
    """
    receive a path and extract the identNr.

    Note: certain valid identNr characters cannot be included in paths such as /.

    (1) We have a preprocessor where we basically replace underline with space
    (2) Middle: split all elements, investigate them and join them back together
    (3) We may have a postprocessor where we cut off unwanted tails that still remain
    (4) There will be always special cases to include chars that are included in identNr,
        but not allowed in filesystem.

    New:
    - Used to return None on failure; now: raises error

    TODO:
    - should we raise error on failure instead of returning None?

    """

    std_form = standardform(path=path)

    # has to have a number
    if not re.search(r"\d+", std_form):
        # number can be sole item e.g. if objId is used as identNr
        return None

    # try to restrict to max length of elements 5 or 4 elements

    # STEP 3: cut off obvious tails
    astr = re.split(r"-[A-Z]+", std_form)[0].strip()  # -KK -A ... -ZZ

    # print(f"***hyphen {astr}")
    m = re.search(r"([()\w\d +.,<>-]+) *_+", astr)  # ___-A
    if m:
        astr = m.group(1).strip()

    # double space: why is this necessary? " *" should catch it already.
    m = re.search(r"([()\w\d +.,<>-]+)  ", astr)
    if m:
        astr = m.group(1).strip()
    # there are 5k+ records with brackets in IdentNr
    # although I dont know what that means
    # e.g. IV Ca 3159 (17)
    # m = re.search(r"([\w\d +.,<>-]+)\(\w+\)", astr) # brackets
    # if m:
    #    astr = m.group(1).strip()

    # print(f"***with tail cut '{astr}'")
    alist = astr.split(" ")
    pos = fortlaufende_Nummer_pos(astr)
    # print(f"***{pos=} {alist}")
    if len(alist) >= pos + 2:
        # 2+ items after fortlaufende Nr.
        plus_one = alist[pos + 1]
        # print("***LONG FORM")
        # print(f"{plus_one=} {len(plus_one)}")
        if re.search(r"[()a-z1-9,-,+]", plus_one):  # ()
            if plus_one == "(P":  # falsche P-Nr
                new = " ".join(alist[0 : pos + 1])
            elif len(plus_one) <= 5:
                # print(f"***part recognized '{plus_one}'")
                new = " ".join(alist[0 : pos + 2])
            else:
                # print(f"***part NOT recognized '{plus_one}'")
                new = " ".join(alist[0 : pos + 1])
        else:
            print(f"***part NOT recognized '{plus_one}'")
            new = " ".join(alist[0 : pos + 1])
    else:
        print("SHORT FORM")
        new = " ".join(alist)

    # STEP 4: special cases
    if astr.startswith("I MV"):
        print(f"**Special case Akten '{astr}'")
        # adding a magic slash.
        # It's magic because we're adding a char that doesn't exist in origin
        # some have different length I/MV 0950 a
        alist[0] = "I/MV"
        alist.pop(1)
        print(f"***{alist} len:{len(alist)}")
        if len(alist) == 2:
            print("astr has only two parts")
            return " ".join(alist)
        elif len(alist) > 2:
            if re.search(r"[a-zA-Z]+", alist[2]):
                print("***valid part")
                new = " ".join(alist[0:3])
            elif re.search(r"\d+", alist[2]):
                print("***digit for disamb")
                # we allow diaamb only when no part
                alist[2] = f"<{alist[2]}>"
                new = " ".join(alist[0:3])
            else:
                new = " ".join(alist[0:2])
        else:  # if alist has 0 items
            raise identNrParserError(f"Unusual number of items {len(alist)}")
    elif astr.startswith("Verz BGAEU"):
        # add a magic dot
        new = re.sub("Verz BGAEU", "Verz. BGAEU", new)
    elif astr.startswith("EJ ") or astr.startswith("Inv "):
        # not catching __0001 correctly...
        new = " ".join(alist[0:2])
    elif astr.startswith("Adr (EJ)"):
        new = " ".join(alist[0:3])
    # elif astr.startswith("VIII "):
    #    new = _parse_EM_photo(astr)
    elif astr.startswith("I C "):
        new = astr.split(" mit ")[0]
    # print (f"{new=}")

    return new


def parse_old(*, path: Path) -> str | None:
    """
    Attempts to extract the full identifier (identNr) from a filename.
    Multiple file extensions are ignored, only the real_stem is processed.
    "-KK" is a required part of the stem.

    TODO: We will need multiple identNr parsers so we have to find a way to
    configure that. Probably a plugin architecure
    """
    stem = str(path).split(".")[0]
    # stem = path.stem # assuming there is only one suffix
    # print (stem)
    m = re.search(r"([\w ,.-]+)\w*-KK", stem)
    # print (m)
    if m:
        return m.group(1)
    return None  # make mypy happy


def standardform(path: Path) -> str:
    """
    - We expect a path as input, but we use only stem (name before last suffix)
    - We replace _ with single space
    - We expect only certain characters (\w\d +.,<>-)
    returns identNrParserError in case of failure
    """

    stem = path.stem  # everything before the _last_ .suffix.

    # STEP 1: collapse underlines into space
    stem2 = re.sub("_", " ", stem)

    # STEP 2: allowed characters
    m = re.search(r"([()\w\d +.,<>-]+)", stem2)

    # What is maximum number of elements in EM?
    # VII ME 01234 a-c <1>: category, unit, number, part, disamb:
    # 4 elements counting 0-based

    if not m:
        raise identNrParserError("Standardform failed")

    return m.group(1).strip()


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


#
# more private
#


def _parse_EM_photo(astr: str) -> str | None:
    """
    receives a version of a filename as str and returns identNr or None. The filename
    has already been transformed.

    NOT USED ATM!
    """
    alist = astr.split(" ")
    print(f"VIII Parser! {astr} {len(alist)}")

    if len(alist) < 2:
        raise SyntaxError("ERROR: VIII Signaturen need to have at least 2 elements")
        return None  # ?
    if re.fullmatch(r"\d+", alist[1]):
        # at this point we dont allow VIII 123 a
        print(f"***Old short VIII form without letter {astr}")
        new = " ".join(alist[0:2])
    else:
        # long form: VIII NA 123 (2nd element is not a number)
        if len(alist) == 2:
            new = " ".join(alist[0:2])
        # VIII NA 123 a
        # at this point we dont allow: VIII NA 123 a <1>
        if re.fullmatch(r"[a-zA-Z]{1,2}", alist[3]):
            print(f"***Long VIII form with part info '{astr}'")
            new = " ".join(alist[0:4])
        else:
            print("***default -- allow 3 elements")
            # default VIII NA 1234
            new = " ".join(alist[0:3])
    return new
