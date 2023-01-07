"""
Rename the von Bruchhausen photos
"""
start_dir = (
    r"//pk.de/smb/Mediadaten/Projekte/EM/Fotobank/vBurchhausenBenin/2022-06-08-tif16-2"
)

from pathlib import Path
import shutil

pp = Path(start_dir)
# if pp.exists():
#    print("exists")

print(f"start_dir: {start_dir}")

for p in Path(start_dir).rglob("*.tif"):
    stem = p.stem
    parent = p.parent
    if stem.startswith("IIIC"):
        print(p)
        new = stem.replace("IIIC", "III C ")
        # print(f"{stem} -> {new}{p.suffix}" )
        new_p = parent.joinpath(new + p.suffix)
        # print(f"{p} -> {new_p}")
        shutil.move(p, new_p)
