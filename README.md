# MpApi-Utils

MpApi-Utils is a package that extends MpApi with command line scripts. Many of these 
utils will assemble data in an Excel file in a first step, so that user can study the 
results and manually correct them in a second step. Only after these intermediary steps, 
real changes will be made in third step (e.g. to the RIA or files will be moved).

The Excel file also functions somewhat as a log file, documenting what has been done. 

## Scripts
- reportx: writes a report on files scanning a directory recursively 
- mover: move files that are already in RIA to save location
- prepare: create object records
- upload: upload files in one directory to RIA

## Little Scripts
- count: count files types for example by extension
- rens: simple rename tool

## Work in Progress

du (i.e. download/upload)
		I am working on a script that can download data from RIA via the API to Excel 
		where it be manually edited and the uploaded again via the API.


rename.py  
		Rename some files on the disk according to a pattern using an Excel doc as 
		intermediary step for manual proof reading.
		Where to we place the configuration information? In a plugin? Perhaps we 
		start with a quick and dirty version where we write the configuration in the 
		program file and fix that later if we ever need this script again.
		
		Maybe then we'll put it in $HOME/.bkp
		
		What is the cli interface?
		ren -s -d . -x o.xslx	: scan the specified directory and write the proposed 
								  changes to o.xsl
		ren -e -x o.xslx		: read o.xslx and execute the changes specified in the Excel
		
		column A: Orig FN relative to starting directory
		column B: project directory
		column C: new name
		column D: target directory

