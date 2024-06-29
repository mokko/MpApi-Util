"""
Currently sorts files with the extension jpg, tif and zip into corresponding folders,
but keeping the rest of the path.
"""

import argparse
import os  # os.sep
from pathlib import Path
import shutil
import signal
import sys
import zipfile

src = Path(r"M:\MuseumPlus\Produktiv\Multimedia\EM\PLM-Dubletten")
done = ["audio", "jpg", "pdf", "tif", "video", "zip"]
SHUTDOWN = False

for each in done:
    d = src / each
    d.mkdir(exist_ok=True)


def main(act: bool, limit: int, filemask: str = "**/*") -> None:
    signal.signal(signal.SIGINT, signal_int)
    print(f"Start globbing in {src}")
    print(f"{act=}")
    print(f"{limit=}")
    print(f"{filemask=}")
    for idx, file in enumerate(src.glob(filemask)):
        if SHUTDOWN:
            print("Graceful shutdown after CTRL+C")
            sys.exit(0)
        suf = file.suffix.lower()
        rel = file.relative_to(src)
        dirs = str(rel).split(os.sep)  # windows specific

        # if dirs[0] in done:
        # print(f"already done {rel=} not in done? dirs0: '{dirs[0]}'")
        if dirs[0] not in done:
            match suf:
                case ".jpg" | ".jpeg":
                    mover("jpg", rel, idx, act)
                case ".mp3" | ".wav":
                    mover("audio", rel, idx, act)
                case ".mp4" | ".mov":
                    mover("video", rel, idx, act)
                case ".pdf":
                    mover("pdf", rel, idx, act)
                case ".tif" | ".tiff":
                    mover("tif", rel, idx, act)
                case ".zip":
                    mover("zip", rel, idx, act)
        if idx == limit:
            print("   Limit reached!")
            break


def mover(kind: str, rel: Path, idx, act) -> None:
    p = src / rel
    p2 = src / kind / rel
    print(f" {idx} {kind} '{rel}'")
    if kind in ["jpg", "pdf", "zip", "audio", "video"]:
        p2.parent.mkdir(parents=True, exist_ok=True)
        # print(f" -> {p2}")
        if act and not p2.exists():
            try:
                shutil.move(p, p2)
            except PermissionError as e:
                print(f"PermissionError {e}")

    elif kind == "tif":
        zip_fn = p2.with_suffix(".zip")
        zip_fn.parent.mkdir(parents=True, exist_ok=True)
        # print(f" -> {zip_fn}")
        if not act:
            print("not act")
            return
        if not zip_fn.exists():
            with zipfile.ZipFile(
                zip_fn, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as myzip:
                myzip.write(p, p.name)
            p.unlink()
    else:
        raise Exception(f"Unknown kind '{kind}'")


def signal_int(sig, frame):
    print("Shutdown requested...")
    global SHUTDOWN
    SHUTDOWN = True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="cleanup", description="Cleanup tool", epilog="Text at the bottom of help"
    )
    parser.add_argument("-a", "--act", action="store_true")
    parser.add_argument("-l", "--limit", type=int, default=1)
    parser.add_argument("-f", "--filemask", default="**/*")
    args = parser.parse_args()
    main(act=args.act, limit=args.limit, filemask=args.filemask)
