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

