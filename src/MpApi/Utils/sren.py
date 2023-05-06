"""
Simple renaming tool - rename files in current directory

    add a string before suffix  
        ren2 add ___-KK  
        before: ./file.jpg
        after:  ./file___-KK.jpg

    replace string A with another string B
        ren relpace "-" "___-KK"
        before: ./file -KK.jpg
        after:  ./file ___-KK.jpg

    Directories are untouched. 
    
    If you want recursive use add **/ at the beginning of your filemask.
    
    Files are always reamed in place, i.e. they stay in the dir they are in.    
"""

from pathlib import Path
import shutil
from typing import Iterator

DEBUG = True


class Sren:
    def __init__(self, *, act=False, filemask=None) -> None:
        self.act = act
        if filemask is None:
            self.filemask = "*"  # default
        else:
            self.filemask = filemask

        self._debug(f"Using filemask {self.filemask}")

    def add(self, string) -> None:
        for p in self._loop():
            suffix = p.suffix
            stem = p.stem
            parent = p.parent
            dst = parent / f"{stem}{string}{suffix}"
            self._move(p, dst)

    def replace(self, first, second) -> None:
        for p in self._loop():
            suffix = p.suffix
            stem = p.stem
            parent = p.parent
            new_stem = stem.replace(first, second)
            dst = parent / f"{new_stem}{suffix}"
            self._move(p, dst)

    #
    # private
    #

    def _debug(self, msg) -> None:
        if DEBUG:
            print(msg)

    def _loop(self) -> Iterator:
        for f in sorted(Path().glob(self.filemask)):
            if not f.is_dir():
                yield f

    def _move(self, src, dst) -> None:
        if src == dst:
            print(f"{src} - name is not new, not moving")
            return
        print(f"{src} -> {dst}")
        if self.act:
            shutil.move(src, dst)
