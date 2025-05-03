"""
Little tool that applies a template to a set of records after they have already been 
created.
WORK IN PROGRESS

A template is copied over the existing record (for the most part), so beware of 
potenial data loss!

As input we expect an Excel sheet with the title "Sheet1" with the IDs in the first 
column. First row are supposed to be headings. Second row is the template. Rest are all
the records that will be overwritten.

BTW: Currently this works for Asste records only and we don't overwrite Dateiname and 
Dateigröße.
"""

import argparse
from copy import deepcopy
from lxml import etree
from pathlib import Path
from mpapi.client import MpApi
from mpapi.constants import get_credentials, NSMAP
from mpapi.module import Module
from MpApi.Utils.Xls import Xls

def apply_template(*, client: MpApi, targetID:int, templateM: Module) -> None:
    print(f"* getting Multimedia {targetID}")
    targetM = client.getItem2(mtype="Multimedia", ID=targetID)
    #todo: currently we're assuming there is always a dateiname
    dateiname_xpath = """/m:application/m:modules/m:module[
        @name = 'Multimedia'
    ]/m:moduleItem/m:dataField[
        @name = 'MulOriginalFileTxt']"""
    dateigröße_xpath = """/m:application/m:modules/m:module[
        @name = 'Multimedia'
    ]/m:moduleItem/m:dataField[
        @name = 'MulSizeTxt']"""     
    dateigröße2_xpath = """/m:application/m:modules/m:module[
        @name = 'Multimedia'
    ]/m:moduleItem/m:dataField[
        @name = 'MulSizeLnu']"""     
    uuid_xpath = """/m:application/m:modules/m:module[
        @name = 'Multimedia'
    ]/m:moduleItem/m:systemField[
        @name = '__uuid']/m:value/text()"""     
    uuid2_xpath = """/m:application/m:modules/m:module[
        @name = 'Multimedia'
    ]/m:moduleItem/m:systemField[
        @name = '__uuid']"""     
    
    #fields to keep from original, no overwrite
    target_dnameN = targetM.xpath(dateiname_xpath)[0]
    target_dgrößeN = targetM.xpath(dateigröße_xpath)[0]
    target_dgröße2N = targetM.xpath(dateigröße2_xpath)[0]
    target_uuid = targetM.xpath(uuid_xpath)[0]
    target_uuidN = targetM.xpath(uuid2_xpath)[0]
    print(f"UUID: {target_uuid}")    
    #newM = deepcopy(templateM)
    newM = deepcopy(targetM)
    mItem = newM.xpath("""/m:application/m:modules/m:module[
        @name = 'Multimedia'
    ]/m:moduleItem""")[0]
    new_dnameN = newM.xpath(dateiname_xpath)[0]
    new_dgrößeN = newM.xpath(dateigröße_xpath)[0]
    new_dgröße2N = newM.xpath(dateigröße2_xpath)[0]
    new_uuidN = newM.xpath(uuid2_xpath)[0]
    
    new_dnameN.getparent().replace(new_dnameN, target_dnameN)
    new_dgrößeN.getparent().replace(new_dgrößeN, target_dgrößeN)
    new_dgröße2N.getparent().replace(new_dgröße2N, target_dgröße2N)
    new_uuidN.getparent().replace(new_uuidN, target_uuidN)
    #fields to add to target (other approach)
    erstellt_amN = """/m:application/m:modules/m:module[
        @name = 'Multimedia'
    ]/m:moduleItem/m:systemField[
        @name = '__uuid']"""     
    
    
    MulShootingDateDat
        
    newM.uploadForm()
    newM._dropAttribs(xpath="//m:repeatableGroupItem", attrib="uuid")
    newM._dropAttribs(xpath="//m:moduleReference", attrib="size")
    newM._dropAttribs(xpath="//m:moduleReference", attrib="multiplicity")
    newM._dropAttribs(xpath="//m:moduleReferenceItem", attrib="seqNo")
    newM._dropAttribs(xpath="//m:compositeItem", attrib="seqNo")
    mItem.set("hasAttachments", "true")
    mItem.set("id", targetID)
    mItem.set("uuid", target_uuid)

    newM.toFile(path="debug.xml")
    print("* updating Multimedia")
    r = client.updateItem2(mtype="Multimedia", ID=targetID, data=newM)
    print(r)


def main(limit:int, filepath:str) -> None:
    user, pw, baseURL = get_credentials()
    client = MpApi(baseURL=baseURL, user=user, pw=pw)
    xls = Xls(path=filepath, description=description())
    ws = xls.get_sheet(title="Sheet1")
    template_id = None
    for row,rno in xls.loop2(sheet=ws, limit=limit, offset=2):
        if rno==2:
            template_id = row[0].value
            print(f"* getting template {template_id}")
            templateM = client.getItem2(mtype="Multimedia", ID=template_id)
            continue
        print(f"{rno}: {row[0].value}")
        apply_template(client=client, templateM=templateM, targetID=row[0].value)
        
def description(): 
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="apply template after creation")
    parser.add_argument(
        "-l", "--limit", type=int, help="stop after x lines of Excel input (integer)"
    )
    parser.add_argument("filepath", help="Excel input file (xlsx)")
    args = parser.parse_args()

    main(limit=args.limit, filepath=args.filepath)
