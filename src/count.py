"""
count the *.jpg files in this directory recursively
"""

from pathlib import Path
from tqdm import tqdm

filemask = "**/*.jpg"
print(f"Looking for {filemask}")
src_dir = Path()
c = 1
with tqdm() as pbar:
    for f in src_dir.glob(filemask):
        pbar.update()
        # print (f)
        c += 1

print(f"files found: {c}")
