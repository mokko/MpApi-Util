"""
    USAGE
    f = IdentNrFactory(schemas_fn="schemas.json")
    # default loc: src/data/schemas.json
    identNr = f.new_identNr(text="VII a 123")
    identNr = f.new_identNr(node=itemN)

    identNr.text
    identNr.schema
    identNr.part1
    identNr.part2
    identNr.part3
    identNr.schemaId
    itemN = identNr.get_node() # this is always newly assembled, not the original

    CLI USAGE
    update_schema_db -i "VII c 123 a-c" # looks identNr up online
    update_schema_db -f bla.xml         # looks thru a file
    update_schema_db -e excel.xlsx      # xlsx as written by prepare
    update_schema_db -v version

"""
from dataclasses import dataclass, field
import json
from lxml import etree  # type: ignore
from mpapi.module import Module
from pathlib import Path
import re
from typing import Any, Iterator

NSMAP = {
    "s": "http://www.zetcom.com/ria/ws/module/search",
    "m": "http://www.zetcom.com/ria/ws/module",
}


class UnknownSchemaException(Exception):
    """
    The schema is not known to schema_db.
    """

    pass


@dataclass
class IdentNr:
    text: str = field(init=False)
    part1: str = field(init=False)
    part2: str = field(init=False)
    part3: str = field(init=False)
    schema: str = field(init=False)
    schemaId: str = field(init=False)

    def get_node() -> Any:  # lxml
        """
        Assemble the internal identNr info into a node and return that.

        Note that this is a newly created generic node and not the one that was possibly
        used to create the identNr in the first place.

        Currently, it returns a whole repeatableGroup with a single rGrpItem in it. This
        might change in the future to preserve potentially existing other rGrpItems.
        """

        xml = f"""
            <repeatableGroup name="ObjObjectNumberGrp">
                <repeatableGroupItem>
                    <dataField name="InventarNrSTxt">
                        <value>{self.text}</value>
                    </dataField>
                    <dataField name="Part1Txt">
                        <value>{self.part1}</value>
                    </dataField>
                    <dataField name="Part2Txt">
                        <value>{self.part2}</value>
                    </dataField>
                    <dataField name="Part3Txt">
                        <value>{self.part3}</value>
                    </dataField>
                    <dataField name="SortLnu">
                        <value>1</value>
                    </dataField>
                    <vocabularyReference name="DenominationVoc">
                        <vocabularyReferenceItem id="2737051"/>
                    </vocabularyReference>
                    <moduleReference name="InvNumberSchemeRef" targetModule="InventoryNumber" multiplicity="N:1" size="1">
                        <moduleReferenceItem moduleItemId="{self.schemeId}"/>
                    </moduleReference>
                </repeatableGroupItem>
            </repeatableGroup>"""

        rGrpN = etree.fromstring(xml, parser)
        return rGrpN


class IdentNrFactory:
    def __init__(self, *, schemas_fn: str = None):
        if schemas_fn is None:
            parent = Path(__file__).parents[2]
            self.schemas_fn = parent / "data" / "schemas.json"

    def _extractSchema(self, *, text: str) -> str:
        """
        What should I do if text is empty?
        """
        if text is not None:
            m = re.search(r"^([\w ]+) \d+", text)
            if m:
                return m.group(1)

        # return None
        raise TypeError(f"_extractSchema failed: {text}")

    def _load_schemas(self) -> None:
        print(f"lazy loading schemas file '{self.schemas_fn}'")
        if Path(self.schemas_fn).exists():
            with open(self.schemas_fn, "r") as openfile:
                self.schema_db = json.load(openfile)
        else:
            self.schema_db = {}

    def _save_schemas(self):
        #        try:
        #            json.dump(self.schema_db, outfile, indent=True, sort_keys=True)
        #        except:
        #            print (self.schema_db)
        #            print ("* json file not written")
        #        else:
        with open(self.schemas_fn, "w") as outfile:
            json.dump(self.schema_db, outfile, indent=True, sort_keys=True)

    def _update_schemas(self, *, data):
        if not hasattr(self, "schema_db"):
            self._load_schemas()
        itemL = data.xpath(
            "/m:application/m:modules/m:module/m:moduleItem/m:repeatableGroup[@name = 'ObjObjectNumberGrp']/m:repeatableGroupItem"
        )

        for itemN in itemL:
            try:
                iNr = self.new_from_node(node=itemN)  # rGrpItemN
            except:
                print("Ignoring node!")
                break
            if iNr.schema is None:
                print(f"WARN: not storing identNr without schema! {iNr}")
                break
            print(f"{iNr.text}")
            self.schema_db[iNr.schema] = {
                "part1": iNr.part1,
                "part2": iNr.part2,
                "part3": iNr.part3,
                "schemaId": iNr.schemaId,
                "text": iNr.text,
            }
        self._save_schemas()

    #
    # PUBLIC
    #

    def get_schemas(self) -> dict:
        if not hasattr(self, "schema_db"):
            self._load_schemas()
        return self.schema_db

    def new_from_str(self, *, text: str) -> IdentNr:
        iNr = IdentNr()
        iNr.text = text
        parts = text.split()
        iNr.part1 = parts[0].strip()
        iNr.part2 = " " + parts[1].strip()
        iNr.part3 = " ".join(parts[2:]).strip()  # rest lumped together
        iNr.schema = self._extractSchema(text=text)

        # lazy load schema_db only once
        if not hasattr(self, "schema_db"):
            self._load_schema_db()
        try:
            schemaId = self.schema_db[iNr.schema]
        except:
            raise UnknownSchemaException(f"Unknown schema for '{iNr.text}'")
        iNr.schemaId = self.schema_db[iNr.schema]["schemaId"]
        return iNr

    def new_from_node(self, *, node) -> IdentNr:
        iNr = IdentNr()
        try:
            iNr.text = node.xpath(
                "m:dataField[@name = 'InventarNrSTxt']/m:value/text()", namespaces=NSMAP
            )[0]
        except:
            # without text, i cant make schema and without schema I cant save in json...
            raise ValueError(
                "No InventarNrSTxt found!"
                + etree.tostring(node, pretty_print=True, encoding="unicode")
            )
        try:
            iNr.part1 = node.xpath(
                "m:dataField[@name = 'Part1Txt']/m:value/text()", namespaces=NSMAP
            )[0]
        except:
            iNr.part1 = None
        try:
            iNr.part2 = node.xpath(
                "m:dataField[@name = 'Part2Txt']/m:value/text()", namespaces=NSMAP
            )[0]
        except:
            iNr.part2 = None
        try:
            iNr.part3 = node.xpath(
                "m:dataField[@name = 'Part3Txt']/m:value/text()", namespaces=NSMAP
            )[0]
        except:
            iNr.part3 = None

        iNr.schemaId = int(
            node.xpath(
                "m:moduleReference[@name = 'InvNumberSchemeRef']/m:moduleReferenceItem/@moduleItemId",
                namespaces=NSMAP,
            )[0]
        )
        iNr.schema = self._extractSchema(text=iNr.text)
        return iNr

    def update_schemas(self, *, data=None, file=None):
        """
        Update the schemas info using existing data either from file or in a Module object.
        """
        if file is not None:
            data = Module(file=file)
        self._update_schemas(data=data)


if __name__ == "__main__":
    pass
