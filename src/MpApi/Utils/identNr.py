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
    update_schemas -i "VII c 123 a-c" # looks identNr up online
    update_schemas -f bla.xml         # looks thru a file
    update_schemas -e excel.xlsx      # xlsx as written by prepare
    update_schemas -v version

"""
from dataclasses import dataclass, field
import json
from lxml import etree  # type: ignore
from mpapi.module import Module
from pathlib import Path
import re
from typing import Any, Iterator

parser = etree.XMLParser(remove_blank_text=True)


NSMAP = {
    "s": "http://www.zetcom.com/ria/ws/module/search",
    "m": "http://www.zetcom.com/ria/ws/module",
}


class UnknownSchemaException(Exception):
    """
    The schema is not known to schemas data silo.
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

    def get_node(self) -> Any:  # lxml
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
                        <moduleReferenceItem moduleItemId="{self.schemaId}"/>
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

    def _extract_schema(self, *, text: str) -> str:
        """
        What should I do if text is empty?
        """
        if text is not None:
            m = re.search(r"^([\w ]+) \d+", text)
            if m:
                return m.group(1)
        # let's be strict
        # don't return None
        raise TypeError(f"_extract_schema failed: {text}")

    def _load_schemas(self) -> None:
        """
        initialies (loads lazily) schemas.json info and saves it in self.schemas.
        """
        if not hasattr(self, "schemas"):
            print(f"lazy loading schemas file '{self.schemas_fn}'")
            if Path(self.schemas_fn).exists():
                with open(self.schemas_fn, "r") as openfile:
                    self.schemas = json.load(openfile)
            else:
                self.schemas = {}

    def _save_schemas(self):
        with open(self.schemas_fn, "w") as outfile:
            json.dump(self.schemas, outfile, indent=True, sort_keys=True)

    def _update_schemas(self, *, data):
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
            self.schemas[iNr.schema] = {
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
        self._load_schemas()
        return self.schemas

    def new_from_str(self, *, text: str) -> IdentNr:
        iNr = IdentNr()
        iNr.text = text
        parts = text.split()
        iNr.part1 = parts[0].strip()
        iNr.part2 = " " + parts[1].strip()
        iNr.part3 = " ".join(parts[2:]).strip()  # rest lumped together
        iNr.schema = self._extract_schema(text=text)

        # lazy load schemas only once
        self._load_schemas()
        try:
            schemaId = self.schemas[iNr.schema]
        except:
            raise UnknownSchemaException(f"Unknown schema for '{iNr.text}'")
        iNr.schemaId = self.schemas[iNr.schema]["schemaId"]
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
        iNr.schema = self._extract_schema(text=iNr.text)
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
