import re


# functions, not methods
def extractIdentNr(*, path: Path) -> Optional[str]:
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
