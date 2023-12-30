"""
Simple renaming tool - rename files in current directory

    add a string before suffix  
        ren2 add ___-KK  
            ./file.jpg --> ./file___-KK.jpg

    replace string A with another string B
        ren replace "-" "___-KK"
            ./file -KK.jpg  --> ./file ___-KK.jpg

    Directories will not be renamed. 
    
    If you want recursive use add **/ at the beginning of your filemask.
    
    Files are always renamed in place, i.e. they stay in the dir they are in.    
"""

from pathlib import Path
import shutil
from typing import Iterator

DEBUG = True


class Sren:
    def __init__(self, *, act=False, filemask=None, rblock=True) -> None:
        """
        rblock blocks recursively adding a string that already exists in stem. By
        default, we switch that on.
        """
        self.act = act
        self.rblock = rblock
        if filemask is None:
            self.filemask = "*"  # default
        else:
            self.filemask = filemask

        self._debug(f"Using filemask {self.filemask}")

    def add(self, string) -> None:
        """
        add a string before the suffix

        {path}{stem}{suffix}

        Should we optionally prevent adding a string that is already present at the end
        of the filename? This is the recursiveblock.
        """
        for p, c in self._loop():
            suffix = p.suffix
            stem = p.stem
            parent = p.parent
            # todo: test
            if self.rblock and stem.endswith(string):
                print(
                    f"rblock: String '{string}' exists already in stem, blocking duplication"
                )
                dst = p
            else:
                dst = parent / f"{stem}{string}{suffix}"
            self._move(p, dst, c)

    def replace(self, first, second) -> None:
        """
        replace a string in the filename (before suffix) - not path.
        """
        for p, c in self._loop():
            suffix = p.suffix
            stem = p.stem
            parent = p.parent
            # should we introduce the rblock?
            # If second string is already part of the stem
            new_stem = stem.replace(first, second)
            if self.rblock and second in stem:
                print(
                    f"rblock: Target string '{second}' exists already in stem, blocking replacment"
                )
                dst = p
            else:
                dst = parent / f"{new_stem}{suffix}"
            self._move(p, dst, c)

    #
    # private
    #

    def _debug(self, msg) -> None:
        if DEBUG:
            print(msg)

    def _loop(self) -> Iterator:
        """
        Returns every file and counts the files returned. Dirs are not returned and not
        counted. Filemask can trigger recursive search (**/). See Python's pathlib for
        details.
        """
        c = 1
        for f in sorted(Path().glob(self.filemask)):
            if not f.is_dir():
                yield f, c
                c += 1

    def _move(self, src, dst, count) -> None:
        if src == dst:
            print(f"{src} - name is not new, not moving")
            return
        print(f"{count}: {src} -> {dst}")
        if self.act:
            shutil.move(src, dst)
