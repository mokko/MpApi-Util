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
from lxml import etree
import lxml
from mpapi.constants import NSMAP, parser
from mpapi.module import Module
from pathlib import Path
import re
from typing import Self  # Self since 3.11


class UnknownSchemaException(Exception):
    """
    The schema is not known to schemas data silo in self.schemas.
    """

    pass


@dataclass
class IdentNr:
    text: str = field(
        init=False
    )  # example as str for a given IdentNr, e.g. "VII f 123"
    part1: str = field(init=False)  # part 1, e.g. "VII"
    part2: str = field(init=False)  # part 2, e.g. " f"
    part3: str = field(init=False)  # part 3, e.g. "123"
    part4: str = field(init=False, default="")  # False = not required?
    schema: str = field(init=False)  # label for specific schema e.g. "VII f"
    schemaId: str = field(init=False)  # id from RIA for this schema

    def get_node(self) -> lxml.etree:
        """
        Assemble the internal identNr info into a node and return that.

        Note that this is a newly created generic node and not the one that was possibly
        used to create the identNr in the first place.

        Currently, it returns a whole repeatableGroup with a single rGrpItem in it. This
        might change in the future to preserve potentially existing other rGrpItems.
        """

        noSpecialChars = self.text.replace(" ", "").replace("_", "").replace("/", "")

        xml = f"""
            <repeatableGroup xmlns='http://www.zetcom.com/ria/ws/module' name="ObjObjectNumberGrp">
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
                    <dataField name="Part4Txt">
                        <value>{self.part4}</value>
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
                    <virtualField name="NumberWithoutSpecialCharactersVrt">
                        <value>{noSpecialChars}</value>
                    </virtualField>
                    <virtualField name="NumberVrt">
                        <value>{self.text}</value>
                    </virtualField>
                </repeatableGroupItem>
            </repeatableGroup>"""

        rGrpN = etree.fromstring(xml, parser)
        return rGrpN


#
#
#


class IdentNrFactory:
    def __init__(self, *, schemas_fn: str = None) -> None:
        if schemas_fn is None:
            parent = Path(__file__).parents[2]
            self.schemas_fn = parent / "data" / "schemas.json"
        self.schemas = self._load_schemas(
            schemas_fn=self.schemas_fn
        )  # explicit is better than implicit
        # print (self.schemas)

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
        print(f"WARN: _extract_schema failed: {text}")
        # raise TypeError(f"_extract_schema failed: {text}")

    def _load_schemas(self, *, schemas_fn: str) -> None:
        """
        initialies (loads lazily) schemas.json info and saves it in self.schemas.
        """
        if not hasattr(self, "schemas"):  # todo: might not work
            print(f"lazy loading schemas file '{self.schemas_fn}'")
            if Path(schemas_fn).exists():
                with open(schemas_fn, "r") as openfile:
                    return json.load(openfile)
            else:
                return {}

    def _parser_AKu(self, text: str) -> IdentNr:
        iNr = IdentNr()
        iNr.text = text

        partsL = text.split("/")  # IV/AKu/000059 -> IV, AKu, 00059
        if len(partsL) != 3:
            raise SyntaxError(f"identNr str not recognized! {text}")
        iNr.part1 = partsL[0]
        iNr.part2 = partsL[1]
        iNr.part3 = partsL[2]
        iNr.schema = f"{partsL[0]}/{partsL[1]}"
        return iNr

    def _parser_EM(self, text: str) -> IdentNr:
        """
        Parse identNr as string into four parts.
        Parse typical EM identNr using roman numeral in the beginning and number towards
        the end.

        """
        iNr = IdentNr()
        iNr.text = text

        m = re.match(
            r"([XVI]+)( [a-zA-Z]{1,2} *[a-zA-Z]*) (\d+)( *[a-z0-9\.\,\-<>()\? ]*)", text
        )

        if m is None:
            raise SyntaxError("ERROR: Not recognized!")

        iNr.part1 = m.group(1)
        iNr.part2 = m.group(2)
        iNr.part3 = m.group(3)
        iNr.part4 = m.group(4).lstrip().lstrip(".")

        iNr.schema = f"{m.group(1)}{m.group(2)}"
        return iNr

    def _parser_space(self, iNr: Self) -> None:
        """
        Use space as a separator to parse the text into parts.
        Still in use?
        """
        parts = identNr.text.split()
        iNr.part1 = parts[0].strip()
        iNr.part2 = " " + parts[1].strip()
        iNr.part3 = parts[2].strip()  # rest lumped together
        iNr.part4 = join(parts[3:]).strip()  # rest lumped together

    def _save_schemas(self) -> None:
        print(f"saving schema at {self.schemas_fn}")
        with open(self.schemas_fn, "w") as outfile:
            json.dump(self.schemas, outfile, indent=True, sort_keys=True)

    def _update_schemas(self, *, data: Module) -> None:
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
                # label = "IV/AKu"
            print(f"{iNr.text}")
            self.schemas[label] = {
                "part1": iNr.part1,
                "part2": iNr.part2,
                "part3": iNr.part3,
                # what about part4?
                "schemaId": iNr.schemaId,
                "text": iNr.text,
            }
        self._save_schemas()

    #
    # PUBLIC
    #

    def get_schemas(self) -> dict:
        return self.schemas

    def new_from_str(self, *, text: str, institution: str = "EM") -> IdentNr:
        match institution:
            case "EM" | "iitm":
                iNr = self._parser_EM(text)  #  eg. V A Dlg 1234 a,b
            case "AKu":
                iNr = self._parser_AKu(text)
            case other:
                raise TypeError(f"Unknown institution: {institution}")

        try:
            schemaId = self.schemas[iNr.schema]
        except KeyError:
            raise UnknownSchemaException(
                f"Unknown schema for '{iNr.text}' {iNr.schema}"
            )
        iNr.schemaId = self.schemas[iNr.schema]["schemaId"]
        return iNr

    def new_from_node(self, *, node: lxml.etree._Element) -> IdentNr:
        """
        node is repeatableGroup[@name='ObjObjectNumberGrp']/repeatableGroupItem. There
        may only be one such item. Not sure
        """
        iNr = IdentNr()
        try:
            iNr.text = node.xpath(
                "m:virtualField[@name = 'NumberVrt']/m:value/text()", namespaces=NSMAP
            )[0]
        except:
            # without text, i cant make schema and without schema I cant save in json...
            # print ("GH1")
            raise ValueError(
                "No InventarNrSTxt found!"
                + etree.tostring(node, pretty_print=True, encoding="unicode")
            )
        try:
            iNr.part1 = node.xpath(
                "m:dataField[@name = 'Part1Txt']/m:value/text()", namespaces=NSMAP
            )[0]
        except:
            # print ("GH2")
            iNr.part1 = None
        try:
            iNr.part2 = node.xpath(
                "m:dataField[@name = 'Part2Txt']/m:value/text()", namespaces=NSMAP
            )[0]
        except:
            # print ("GH3")
            iNr.part2 = None
        try:
            iNr.part3 = node.xpath(
                "m:dataField[@name = 'Part3Txt']/m:value/text()", namespaces=NSMAP
            )[0]
        except:
            # print ("GH4")
            iNr.part3 = None

        iNr.schemaId = int(
            node.xpath(
                "m:moduleReference[@name = 'InvNumberSchemeRef']/m:moduleReferenceItem/@moduleItemId",
                namespaces=NSMAP,
            )[0]
        )
        iNr.schema = self._extract_schema(text=iNr.text)
        return iNr

    def update_schemas(self, *, data=None, file=None) -> None:
        """
        Update the schemas info using existing data either from file or in a Module object.
        """
        if file is not None:
            data = Module(file=file)
        self._update_schemas(data=data)


if __name__ == "__main__":
    pass
