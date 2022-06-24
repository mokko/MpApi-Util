"""
bkp-ren 
        Rename some files on the disk according to a pattern using an Excel 
        doc as intermediary step for manual proof reading.

        The first instance of this script is supposed to work on pairs of
        tiff and jpg files. Do we even need those jpgs in RIA? Or do we work 
        solely on tifs and eliminate the jpgs?

        CONFIGURATION
		Where to we place the configuration information? In a plugin? Perhaps we 
		start with a quick and dirty version where we write the configuration in the 
		program file and fix that later if we ever need this script again.
		
		Maybe then we'll put it in $HOME/.bkp

        CLI INTERFACE
        ren -l cache.json       : load a saved cache
		ren -s -d . -x o.xslx	: scan the specified directory and write the proposed 
								  changes to o.xsl
		ren -e -x o.xslx		: read o.xslx and execute the changes specified in the Excel
		
        EXCEL Format
		column A: Orig FN relative to starting directory
		column B: project directory
		column C: new name
		column D: target directory

        FILE CACHE
        Do we use a file cache to speed up the process?
        
        absolute path is unique, so has to be key
        
        abspath: basename
        
        save to dir
        
"""
from pathlib import Path

src_dir = "M:\MuseumPlus\Produktiv\Multimedia\EM\Südsee-Australien\Archiv TIFF und Raw\1 Hauser"
class ren:

    def __init__ () -> None: pass
    
    def cache_dir (self, *, folder):
        for each in  Path(folder).rglob("*.jpg"):
            print (f"{each}")

        self.cache

if __name__ == "__main__":
    r = ren
    r.cache_dir(folder=src_dir)
    