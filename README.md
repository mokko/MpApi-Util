# MpApi-Utils

MpApi-Utils is a package that extends MpApi with command line scripts. Many of these 
utilities will assemble data in an Excel file in a first step, so that user can study 
the results and manually correct them in a second step. Only after these intermediary 
steps, real changes will be made in third step (e.g. changes made to the database). The 
Excel file also functions as a log file, documenting what has been done. This method is 
relatively slow, so dont expect anything here to win a speed competition. 

## Main Scripts
- mover: move files that are already in RIA to safe location
- prepare: create object records for assets that dont have one yet
- reportx: writes a report on files scanning a directory recursively 
- upload: based on properly named files on disk, create asset records, link to object 
  records, and attach assets in RIA.

## Small Tools
- attach: attach an asset to existing asset record (for debugging)
- count: count files types for example by extension
- mk_grp: make an Object Group from Excel file
- restart: restart a job x times
- sren: yet another simple file renaming tool
- update_schemas: update the internal identNr schema db (used in upload)
