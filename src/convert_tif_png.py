"""
- loop recursively to directory
- for every *.tif you find make a png and saved it
- resize if over MAX_SIZE

folder1/TIFF/filename.tif -> forder1/PNG/filename.png
"""
import argparse
from PIL import Image
from pathlib import Path

MAX_SIZE = 2000  # size in px of longest edge


def convert_path(p: Path, mkdir: bool = True) -> Path:
    new_name = p.with_suffix(".png").name
    parent = p.parent
    if parent.name == "TIFF":
        p2 = parent.parent
        new_parent = p2 / "PNG"
        if mkdir:
            new_parent.mkdir(exist_ok=True)
    else:
        print("********** WARNING ********** ")
        return parent / new_name
    return new_parent / new_name


def resize(img):
    width, height = img.size
    if width > MAX_SIZE or height > MAX_SIZE:
        if width > height:
            factor = MAX_SIZE / width
        else:  # height > width or both equal
            factor = MAX_SIZE / height
        new_size = (int(width * factor), int(height * factor))
        print(f"   resize {factor:.0%} {new_size}")
    return img.resize(new_size, Image.LANCZOS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="convert tifs to pngs while preserving paths intelligently"
    )

    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        help="specify a limit to stop at",
    )

    args = parser.parse_args()
    if args.limit:
        print(f"Using limit {args.limit}")

    c = 1
    for p in Path(".").glob("**/*.tif"):
        new_p = convert_path(p)  # haven't created new dir yet
        print(f"{c}:{p} -> {new_p}")
        if new_p.exists():
            print(f"   exists already")
        else:
            img = Image.open(p)
            img = resize(img)
            img.save(new_p, optimize=True)
        if c == args.limit:
            print("Limit reached")
            break
        c += 1
