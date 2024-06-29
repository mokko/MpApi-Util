"""
execute this in a directory with asset files.
script will look for letter ending (e.g. -A) and increase the letter by one (e.g. -B).

Not tested for complicated cases e.g. with multiple letters!
"""

from pathlib import Path
import re
import shutil


def main(act: bool, filemask: str = "*.*", limit: int = -1) -> None:
    print(f"act is set to '{act}'")
    print(f"filemask is set to '{filemask}'")
    print(f"limit is set to '{limit}'")

    # we reverse order to that -C is processed before -B
    files = reversed(list(Path(".").glob(filemask)))

    for idx, child in enumerate(files, start=1):
        parts = re.split(r"\-", child.stem)
        if len(parts) == 2:
            # not tested for complicated cases, e.g. involving multiple letters!
            current_letter = parts[-1]
            new_letter = chr(ord(current_letter) + 1)
            # print(f"{current_letter} -> {new_letter}")
            name2 = Path(f"{parts[0]}-{new_letter}{child.suffix}")
            print(f"{child} -> {name2}")
            if act:
                if name2.exists():
                    print("WARNING:destination exists already; no move")
                else:
                    shutil.move(child, name2)
        else:
            print(f"UNUSUAL no_parts {len(parts)}")
        if idx == limit:
            print("Limit reached!")
            break  # out of for loop


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="attach an asset file to a multimedia record and download it"
    )
    parser.add_argument(
        "-a", "--act", help="actually do the renaming", action="store_true"
    )
    parser.add_argument(
        "-f",
        "--filemask",
        help="actually do the renaming",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=-1,
        help="stop after number of files",
    )
    args = parser.parse_args()
    main(act=args.act, filemask=args.filemask, limit=args.limit)
