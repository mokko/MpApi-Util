from pathlib import Path
import shutil

src_dir = r"\\pk.de\smb\Mediadaten\Projekte\EM\Fotobank\MDVOS_OZ_SB\TIFF_Hauser-Schäublin\VIII Oz K 215"

p = Path(src_dir)
print(p)
c = 1
for file in p.rglob("*.tif"):
    if not "___" in str(file):
        parent = file.parent
        c += 1
        new = parent.joinpath(file.stem + "___-A.tif")
        print(f"{file} -> {new}")
        shutil.move(file, new)
        # raise TypeError
print(f"{c}")
