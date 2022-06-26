"""
A little script that tests if a certain set of files have unique filenames
"""

from pathlib import Path

src_dir = "M:/MuseumPlus/Produktiv/Multimedia/EM/Südsee-Australien/Archiv TIFF und Raw/1 Hauser"
mask = "VIII B*.jpg"

srcP = Path(src_dir)
cache = {}  # pname to count
path_cache = {}  # path to pname
for p in Path(srcP).rglob(mask):
    path_cache[p] = p.name
    print(f"*{p.name}")
    if p.name in cache:
        cache[p.name] += 1
    else:
        cache[p.name] = 1
for pname1 in cache:
    if cache[pname1] > 1:
        print(f"{pname1} {cache[pname1]}")
        for p2 in path_cache:
            if path_cache[p2] == pname1:
                print(f"!{p2}")
