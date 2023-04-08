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
    # stem = str(path).split(".")[0]  # stem is everything before first .
    stem = path.stem

    m = re.search(r"([\w\d +.,-]+)", stem)
    if m:
        return m.group(1).strip()
    # else
    #     return None
