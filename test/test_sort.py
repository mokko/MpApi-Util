from mpapi.module import Module
from pathlib import Path


def test_one() -> None:
    fn = Path("../sdata/debug.object.xml")
    m = Module(file=fn)
    # m.validate()
    m.sort_elements()
    m.validate()
    m.toFile(path="new.debug.xml")
    print(m)
