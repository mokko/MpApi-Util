# MpApi-Utils

MpApi-Utils is a package that extends MpApi with command line scripts. Many of these 
utils will assemble data in an Excel file in a first step, so that user can study the 
results and manually correct them in a second step. Only after these intermediary steps, 
real changes will be made in third step (e.g. to the RIA or files will be moved).

The Excel file also functions somewhat as a log file, documenting what has been done. 

## Main Scripts
- mover: move files that are already in RIA to save location
- prepare: create object records
- reportx: writes a report on files scanning a directory recursively 
- upload: upload files in one directory to RIA

## Small Tools
- attach: attach an asset to existing asset record (for debugging)
- count: count files types for example by extension
- mk_grp: make an Object Group from Excel file
- restart: restart a job x times
- sren: yet another simple file rename tool
- update_schemas: update the internal identNr schema db (used in upload)
