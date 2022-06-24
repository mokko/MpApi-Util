MpApi-Utils
is a package with advanced utilities and scripts for MpApi. It's also experimental and 
work in progress.

du (i.e. download/upload)
		I am working on a script that can download data from RIA via the API to Excel 
		where it be manually edited and the uploaded again via the API.

bkp (from Bokop)
bkp-ren Rename some files on the disk according to a pattern using an Excel doc as 
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

bkp-create 
		for every file matching a specific pattern, 
		- extract a identNr from file name
		- check if record with this identNr exists already
		- if does not exist: 
			- create a new record in RIA 
			- copy a template record to the new record
			- fill in this identNr
			
		Let's also write initial configuration to program quick-and-dirty style.
		What is the cli?
		create -d path/to/dir
		
		Eventually we'll want a logger, but that can wait.