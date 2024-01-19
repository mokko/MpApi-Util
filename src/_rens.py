from pathlib import Path
import shutil

# src_dir = r"\\pk.de\smb\Mediadaten\Projekte\EM\Fotobank\MDVOS_OZ_SB\TIFF_Hauser-Schäublin\VIII Oz K 215"

p = Path(".")
# print(p)
c = 1
for file in p.glob("**/*.tif"):
    if "IC" in str(file):
        parent = file.parent
        c += 1
        new_stem = file.stem.replace("IC", "I_C")
        new = parent.joinpath(new_stem + file.suffix)
        print(f"{file} -> {new}")
        # shutil.move(file, new)
        # raise TypeError
print(f"{c}")
