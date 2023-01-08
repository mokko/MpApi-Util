"""
NAME bcreate.py 
	for every file matching a specific pattern, 
	- extract a identNr from file name
	- check if record with this identNr exists already in RIA
	- if does not exist: 
		- create a new record in RIA 
		- copy a template record to the new record
		- fill in this identNr and possibly other fields
		
CONFIGURATION
	bcreate-conf.ini
    
CLI INTERFACE
	bcreate -c conf.ini -j section	

    TODO: make an explicit switch to do any changes
	bcreate -a	: actually create new records
"""
import configparser
import copy
from lxml import etree
import logging
from mpapi.module import Module
from mpapi.client import MpApi
from MpApi.Utils.BaseApp import BaseApp
#from MpApi.Utils.Ria import RiaUtil # not yet used

# from mpapi.sar import Sar
from mpapi.search import Search
from pathlib import Path

ETparser = etree.XMLParser(remove_blank_text=True)
NSMAP = {
    "s": "http://www.zetcom.com/ria/ws/module/search",
    "m": "http://www.zetcom.com/ria/ws/module",
}

# Let's put the conf in a py file and simply exec it?


class Bcreate(BaseApp):
    def __init__(
        self, *, baseURL: str, conf_fn: str, job: str, pw: str, user: str
    ) -> None:

        self.api = MpApi(baseURL=baseURL, user=user, pw=pw)
        #not yet used
        #self.client = RiaUtil(baseURL=baseURL, user=user, pw=pw)
        self.conf = self._init_conf(path=confFN, job=job)
        self._init_log()

        # print(conf)
        self.templateM = self.setTemplate(
            mtype="Object", ID=conf["templateID"]
        )  # Object-only atm

        srcP = Path(conf["src_dir"])
        count_files = 0
        count_alreadyTaken = 0
        logging.info(f"mask {conf['mask']}")
        logging.info(f"dir {conf['src_dir']}")
        print(f"***About to scan dir '{conf['src_dir']}' with mask '{conf['mask']}'")
        for p in Path(srcP).rglob(conf["mask"]):
            print(f"\n{p}")
            identNr = self._xtractIdentNr(name=p.stem)
            r = self.identExists(nr=identNr)
            print(f"   checking if '{identNr}' exists in RIA")
            if r:
                print("\texists")
                count_alreadyTaken += 1
                print(f"\texists already, we won't touch it; exists {r} times")
                logging.warning(f"identNr '{identNr}' exists already {r} times in RIA")
            else:
                print(f"{p} {identNr} DOES NOT exist")
                self.createObject(identNr=identNr)
            count_files += 1
        logging.info(
            f"bcreate found {count_files} files fitting mask (looking recursively)"
        )
        logging.info(
            f"of those {count_alreadyTaken} have an identNr that already exists in RIA"
        )

    def addIdentNr(self, *, data, identNr):
        """

        Assume that
        - I dont need or may not have InventarNrSTxt, ModifiedByTxt, ModifiedDateDat,
        - have to have Part1Txt, Part2Txt, Part3Txt and
        - want to have SortLnu
        <repeatableGroup name="ObjObjectNumberGrp">
          <repeatableGroupItem>
            <dataField name="InventarNrSTxt">
              <value>VIII B 74</value>
            </dataField>
            <dataField name="ModifiedByTxt">
              <value>EM_EM</value>
            </dataField>
            <dataField name="ModifiedDateDat">
              <value>2010-05-07</value>
            </dataField>
            <dataField name="Part1Txt">
              <value>VIII</value>
            </dataField>
            <dataField name="Part2Txt">
              <value> B</value>
            </dataField>
            <dataField name="Part3Txt">
              <value>74</value>
            </dataField>
            <dataField name="SortLnu">
              <value>1</value>
            </dataField>
            ...

            Note the leading spave in Part2!

        <repeatableGroup name="ObjObjectNumberGrp">
          <repeatableGroupItem>
            <dataField name="InventarNrSTxt">
              <value>{identNr}</value>
            </dataField>
            <dataField name="Part1Txt">
              <value>{part1}</value>
            </dataField>
            <dataField name="Part2Txt">
              <value> {part2}</value>
            </dataField>
            <dataField name="Part3Txt">
              <value>{part3}</value>
            </dataField>
            <dataField name="SortLnu">
              <value>1</value>
            </dataField>
          </repeatableGroupItem>
        </repeatableGroup>
        """

        part1 = identNr.split()[0]
        part2 = " " + identNr.split()[1]
        part3 = " ".join(identNr.split()[2:])
        print(f"DEBUG:{part1}|{part2}|{part3}|")

        itemN = data.xpath("/m:application/m:modules/m:module/m:moduleItem[1]")[0]
        # assume that ObjObjektNumberGrp exists already, which is a reasonable expectation
        # only api-created records may have no identNr
        rGrpN = data.repeatableGroup(parent=itemN, name="ObjObjectNumberGrp")
        grpItemN = data.repeatableGroupItem(parent=rGrpN)
        data.dataField(parent=grpItemN, name="InventarNrSTxt", value=identNr)
        data.dataField(parent=grpItemN, name="Part1Txt", value=part1)
        data.dataField(parent=grpItemN, name="Part2Txt", value=part2)
        data.dataField(parent=grpItemN, name="Part3Txt", value=part3)
        data.dataField(parent=grpItemN, name="SortLnu", value="1")
        vr = data.vocabularyReference(parent=grpItemN, name="DenominationVoc")
        data.vocabularyReferenceItem(parent=vr, ID=2737051)  # Ident. Nr.
        mrN = data.moduleReference(parent=grpItemN, name="InvNumberSchemeRef")
        data.moduleReferenceItem(
            parent=mrN, moduleItemId="68"
        )  # EM-Südsee/Australien VIII B
        # return m we change the object in-place

    def createObject(self, *, identNr: str):
        """
        We want to create a new reord and fill in some data that remains
        consistent. In order to do that, we'll use the same template-based
        mechanism as RIA, i.e. effectively copying the template record to
        the new record.

        Steps
        1. get (download) the template record,
        2. sanitize the xml, so it has the upload form required by RIA
        3. fill in identNr -> TODO
        4. createRecord

        The first step happens in setTemplate, the rest here.

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

        newM = copy.deepcopy(self.templateM)
        # todo: check changeIdentNr
        self.addIdentNr(data=newM, identNr=identNr)
        newM.toFile(path="template.debug.xml")

        print(f"\tabout to create object")
        r = self.api.createItem2(mtype="Object", data=newM)
        # responseM = Module(xml=r.text)
        # ID = responseM.xpath("/m:application/m:modules/m:module/m:moduleItem/@id")[0]
        # print ("RESPONSE: id {ID} created")
        print("RESPONSE")
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
        Sanitize (=clean) the xml (upload form)

        Croaks if nothing found
        Saves Module object to self.template

        Questions
        - perhaps we should save it as ET? Not sure yet
        - requirements of upload form are unclear
        """

        m = self.api.getItem2(mtype=mtype, ID=ID)

        if not m:
            raise SyntaxError(f"ERROR: Template record not found: {mtype} {ID}")

        m.clean()
        m.uploadForm()

        if len(m) > 1:
            raise SyntaxError("ERROR: Upload xml has >1 items")
        # print (m)
        logging.info(f"template Object {ID}")
        return m

    #
    # privates
    #



    def _xtractIdentNr(self, *, name: str) -> str:
        parts = name.split(" ")
        if len(parts) < 2:
            raise SyntaxError(f"ERROR: IdentNr has suspicious format... {name}")
        return name
