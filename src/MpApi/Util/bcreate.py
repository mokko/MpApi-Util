"""
NAME bcreate.py 
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

CLI INTERFACE
	bcreate 	: just show what you would does
	bcreate -a	: actually create new records
		
"""
import configparser
import copy
from lxml import etree
import logging
from mpapi.module import Module
from mpapi.client import MpApi

# from mpapi.sar import Sar
from mpapi.search import Search
from pathlib import Path

ETparser = etree.XMLParser(remove_blank_text=True)
NSMAP = {
    "s": "http://www.zetcom.com/ria/ws/module/search",
    "m": "http://www.zetcom.com/ria/ws/module",
}

# Let's put the conf in a py file and simply exec it?


class Bcreate:
    def __init__(
        self, *, baseURL: str, confFN: str, job: str, pw: str, user: str
    ) -> None:

        self.api = MpApi(baseURL=baseURL, user=user, pw=pw)
        conf = self._initConf(confFN=confFN, job=job)
        self._initLog()

        print(conf)
        m = self.setTemplate(mtype="Object", ID=conf["templateID"])  # Object-only atm

        srcP = Path(conf["src_dir"])
        count_files = 0
        count_alreadyTaken = 0
        logging.info(f"mask {conf['mask']}")
        logging.info(f"dir {conf['src_dir']}")
        print(f"***About to scan dir '{conf['src_dir']}' with mask '{conf['mask']}'")
        for p in Path(srcP).rglob(conf["mask"]):
            print(f"{p}")
            identNr = self._xtractIdentNr(name=p.stem)
            r = self.identExists(nr=identNr)
            print(f"   checking if '{identNr}' exists in RIA")
            if r:
                count_alreadyTaken += 1
                print(f"\texists already, we won't touch it; exists {r} times")
                logging.warning(f"identNr '{identNr}' exists already {r} times in RIA")
            else:
                # print(f"{p} {identNr} DOES NOT exist")
                self.createObject(identNr=identNr)
            count_files += 1
        logging.info(
            f"bcreate found {count_files} files fitting mask (looking recursively)"
        )
        logging.info(
            f"of those {count_alreadyTaken} have an identNr that already exists in RIA"
        )

    def createObject(self, *, identNr: str):
        """
        We want to create a new reord and fill in some data that remains
        consistent. In order to do that, we'll use the same template-based
        mechanism as RIA, i.e. effectively copying the template record to
        the new record.

        Steps
        1. get (download) the template record,
        2. sanitize the xml, so it has the upload form required by RIA
        3. fill in identNr
        4. createRecord

        <application xmlns="http://www.zetcom.com/ria/ws/module">
            <modules>
                <module name="Address">
                    <moduleItem>
                        <dataField name="AdrPostcodeTxt">
                            <value>12345</value>
                        </dataField>
                        <dataField name="AdrSurNameTxt">
                            <value>Muster</value>
                        </dataField>
                        <dataField name="AdrStreetTxt">
                          <value>Köpenickerstr. 154</value>
                        </dataField>
                        <dataField name="AdrCityTxt">
                          <value>Berlin</value>
                        </dataField>
                        <dataField name="AdrForeNameTxt">
                          <value>Max</value>
                        </dataField>
                        <dataField name="AdrCountryTxt">
                          <value>Germany</value>
                        </dataField>
                        <dataField dataType="Varchar" name="AdrCountyTxt">
                          <value>Berlin</value>
                        </dataField>
                        <vocabularyReference name="AdrSendEmailVoc">
                          <vocabularyReferenceItem id="30891" />
                        </vocabularyReference>
                        <vocabularyReference name="AdrSendPostVoc">
                          <vocabularyReferenceItem id="30891" />
                        </vocabularyReference>
                        <repeatableGroup name="AdrContactGrp">
                          <repeatableGroupItem>
                            <dataField name="ValueTxt">
                              <value>max.muster@gmail.com</value>
                            </dataField>
                            <vocabularyReference name="TypeVoc">
                              <vocabularyReferenceItem id="30152" />
                            </vocabularyReference>
                          </repeatableGroupItem>
                          <repeatableGroupItem>
                            <dataField name="ValueTxt">
                              <value>(555)555-5555</value>
                            </dataField>
                            <vocabularyReference name="TypeVoc">
                              <vocabularyReferenceItem id="30150" />
                            </vocabularyReference>
                          </repeatableGroupItem>
                        </repeatableGroup>
                        <moduleReference name="AdrAddressGroupRef">
                            <moduleReferenceItem moduleItemId="12011" />
                        </moduleReference>
                    </moduleItem>
                </module>
            </modules>
        </application>
        """

        print(f"\tabout to create object")
        newM = copy.deepcopy(self.template)
        # todo: changeIdentNr
        # fake is a minimal record for testing purposes
        fake = Module()
        objModule = fake.module(name="Object")
        item = m.moduleItem(parent=objModule)
        # r = self.api.createItem2(mtype="Object", data=newM)
        r = self.api.createItem2(mtype="Object", data=fake)
        print(r)
        raise SyntaxError("STOP HERE PURPOSEFULLY")

    def identExists(self, *, nr) -> int:
        s = Search(module="Object", limit=-1, offset=0)
        # s.AND()
        s.addCriterion(
            field="ObjObjectNumberVrt",
            operator="equalsField",
            value=nr,
        )
        m = self.api.search2(query=s)
        return len(m)

    def setTemplate(self, *, mtype: str, ID: int) -> None:
        """
        Get (download) record with ID from the module mtype.
        Sanitize the xml (upload form) and save to self.templateXml

        Perhaps we should save it as ET? Not sure yet
        """

        m = self.api.getItem2(mtype=mtype, ID=ID)

        if not m:
            raise SyntaxError(f"ERROR: Template record not found: {mtype} {ID}")

        m.clean()
        m.uploadForm()
        m.toFile(path="template.debug.xml")
        if len(m) > 1:
            raise SyntaxError("ERROR: Upload xml has >1 items")
        # print (m)
        logging.info(f"template Object {ID}")
        self.template = m

    #
    # privates
    #

    def _initConf(self, *, confFN, job):
        if not Path(confFN).exists():
            raise SyntaxError("ERROR: Config file not found!")
        config = configparser.ConfigParser()
        config.read(
            confFN, "UTF-8"
        )  # at the moment expecting: templateID, mask, src_dir
        return config[job]  # dies gracefully on error

    def _initLog(self):
        logging.basicConfig(
            datefmt="%Y%m%d %I:%M:%S %p",
            filename="bcreate.log",
            filemode="w",  # a =append?
            level=logging.INFO,
            format="%(asctime)s: %(message)s",
        )

    def _xtractIdentNr(self, *, name: str) -> str:
        return name
