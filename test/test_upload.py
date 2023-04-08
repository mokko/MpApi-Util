"""

In April 2023 we begin our 2nd app using this framework. First of all, we trying to 
improve the credenials system. We want to provide a single credentials file and we
also might restrict from all too curious eyes.

"""

from MpApi.Utils.AssetUploader import AssetUploader
import os
from pathlib import Path


def test_construction():
    u = AssetUploader()
    assert u


def test_init():
    p = Path("upload.xlsx")
    if p.exists():
        os.remove(p)
    u = AssetUploader()
    u.init()


def test_scandir():
    u = AssetUploader()
    u.scandir(Dir="adir")
