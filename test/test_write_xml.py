"""
Tests for MpApi.Utils.becky.write_xml

Tests are offline (no RIA connection needed). They use synthetic Module
objects built from XML strings to test the private helpers (_new_or_replace,
_add) and the identNr callback. The stub functions that are just `pass` are
tested for callability and signature compatibility.

Requires the conftest.py stubs for mpapi.constants and MpApi.Utils.
"""

from copy import deepcopy
from lxml import etree
from mpapi.module import Module
from MpApi.Utils.becky import write_xml
from MpApi.Utils.becky.write_xml import (
    _add,
    _new_or_replace,
    create_xml,
    identNr,
    Aufschrift,
    BemerkungenSammlungen,
    Besitzart,
    Beteiligte,
    Datierung,
    ErwerbDatum,
    ErwerbNotiz,
    Erwerbungsart,
    MaterialTechnik,
    Objektreferenz,
    Sachbegriff,
    Status,
    SystematikArt,
    Titel,
    weitereNr,
    Zugang,
)
import pytest

NS = "xmlns='http://www.zetcom.com/ria/ws/module'"


# ── Fixtures ──────────────────────────────────────────────────────────────


TEMPLATE_XML = """\
<application xmlns="http://www.zetcom.com/ria/ws/module">
  <modules>
    <module name="Object" totalSize="1">
      <moduleItem id="100">
        <systemField dataType="Long" name="__id">
          <value>100</value>
        </systemField>
        <dataField dataType="Varchar" name="ObjObjectNumberTxt">
          <value>III C 192</value>
        </dataField>
        <dataField dataType="Varchar" name="ObjTechnicalTermClb">
          <value>Testbegriff</value>
        </dataField>
      </moduleItem>
    </module>
  </modules>
</application>"""


@pytest.fixture
def templateM():
    """A minimal Module object mimicking an RIA Object template."""
    return Module(xml=TEMPLATE_XML)


def _make_row(values: list) -> tuple:
    """Build a fake Excel row (list of simple cell-like objects)."""

    class FakeCell:
        def __init__(self, val):
            self.value = val

    return tuple(FakeCell(v) for v in values)


# ── _new_or_replace ───────────────────────────────────────────────────────


class TestNewOrReplace:
    def test_replace_existing(self, templateM):
        """When the xpath target exists, it should be replaced."""
        newN = etree.fromstring(
            f"<dataField {NS} name='ObjObjectNumberTxt'><value>III C 999</value></dataField>"
        )
        _new_or_replace(
            record=templateM,
            xpath="//m:dataField[@name='ObjObjectNumberTxt']",
            newN=newN,
        )
        result = templateM.xpath(
            "//m:dataField[@name='ObjObjectNumberTxt']/m:value/text()"
        )
        assert result == ["III C 999"]

    def test_append_when_missing(self, templateM):
        """When the xpath target doesn't exist, the new node is appended to moduleItem."""
        newN = etree.fromstring(
            f"<dataField {NS} name='ObjTechnicalTermClb'><value>Foo</value></dataField>"
        )
        # Remove the existing field so we test the append path
        existing = templateM.xpath("//m:dataField[@name='ObjTechnicalTermClb']")[0]
        existing.getparent().remove(existing)

        _new_or_replace(
            record=templateM,
            xpath="//m:dataField[@name='ObjTechnicalTermClb']",
            newN=newN,
        )
        result = templateM.xpath(
            "//m:dataField[@name='ObjTechnicalTermClb']/m:value/text()"
        )
        assert result == ["Foo"]

    def test_replace_preserves_other_elements(self, templateM):
        """Replacing one element should not remove unrelated siblings."""
        newN = etree.fromstring(
            f"<dataField {NS} name='ObjObjectNumberTxt'><value>NEW</value></dataField>"
        )
        _new_or_replace(
            record=templateM,
            xpath="//m:dataField[@name='ObjObjectNumberTxt']",
            newN=newN,
        )
        # The technical term should still be present
        assert templateM.xpath(
            "//m:dataField[@name='ObjTechnicalTermClb']/m:value/text()"
        ) == ["Testbegriff"]


# ── _add ──────────────────────────────────────────────────────────────────


class TestAdd:
    def test_add_sibling(self, templateM):
        """_add should insert a new sibling after the matched element."""
        newN = etree.fromstring(
            f"<dataField {NS} name='ObjObjectNumberTxt'><value>III C 999</value></dataField>"
        )
        _add(
            record=templateM,
            xpath="//m:dataField[@name='ObjObjectNumberTxt']",
            newN=newN,
        )
        results = templateM.xpath(
            "//m:dataField[@name='ObjObjectNumberTxt']/m:value/text()"
        )
        assert "III C 192" in results
        assert "III C 999" in results
        assert len(results) == 2

    def test_add_after_first_match(self, templateM):
        """When multiple matches exist, _add inserts after the first one."""
        # Add a second ObjObjectNumberTxt first
        second = etree.fromstring(
            f"<dataField {NS} name='ObjObjectNumberTxt'><value>III C 193</value></dataField>"
        )
        _add(
            record=templateM,
            xpath="//m:dataField[@name='ObjObjectNumberTxt']",
            newN=second,
        )
        # Now add a third
        third = etree.fromstring(
            f"<dataField {NS} name='ObjObjectNumberTxt'><value>III C 194</value></dataField>"
        )
        _add(
            record=templateM,
            xpath="//m:dataField[@name='ObjObjectNumberTxt']",
            newN=third,
        )
        results = templateM.xpath(
            "//m:dataField[@name='ObjObjectNumberTxt']/m:value/text()"
        )
        # Order should be: original, third (inserted after first), second
        assert results[0] == "III C 192"
        assert "III C 194" in results
        assert "III C 193" in results


# ── identNr callback ──────────────────────────────────────────────────────


class TestIdentNr:
    def test_identNr_set_type(self, templateM):
        """identNr with type='set' replaces ObjObjectNumberTxt with a
        repeatableGroup (ObjObjectNumberGrp) containing the parsed identNr."""
        cluster = {
            "type": "set",
            "fields": {
                "identNr": {"type": "column", "value": 0},
            },
        }
        row = _make_row(["VII a 113"])
        identNr(record=templateM, cluster=cluster, row=row)

        # The original ObjObjectNumberTxt dataField is replaced by the group
        old = templateM.xpath(
            "//m:dataField[@name='ObjObjectNumberTxt']/m:value/text()"
        )
        assert old == []

        # The new repeatableGroup should contain the identNr in InventarNrSTxt
        inventar = templateM.xpath(
            "//m:repeatableGroup[@name='ObjObjectNumberGrp']"
            "/m:repeatableGroupItem/m:dataField[@name='InventarNrSTxt']/m:value/text()"
        )
        assert inventar == ["VII a 113"]

    def test_identNr_add_type(self, templateM):
        """identNr with type='add' keeps the existing ObjObjectNumberTxt and
        adds a new repeatableGroup (ObjObjectNumberGrp) as a sibling."""
        cluster = {
            "type": "add",
            "fields": {
                "identNr": {"type": "column", "value": 0},
            },
        }
        row = _make_row(["VII a 113"])
        identNr(record=templateM, cluster=cluster, row=row)

        # The original ObjObjectNumberTxt should still exist
        old = templateM.xpath(
            "//m:dataField[@name='ObjObjectNumberTxt']/m:value/text()"
        )
        assert "III C 192" in old

        # A new repeatableGroup should be added with the identNr
        inventar = templateM.xpath(
            "//m:repeatableGroup[@name='ObjObjectNumberGrp']"
            "/m:repeatableGroupItem/m:dataField[@name='InventarNrSTxt']/m:value/text()"
        )
        assert "VII a 113" in inventar

    def test_identNr_creates_object_number_grp(self, templateM):
        """identNr should populate the ObjObjectNumberGrp repeatableGroup."""
        cluster = {
            "type": "set",
            "fields": {
                "identNr": {"type": "column", "value": 0},
            },
        }
        row = _make_row(["VII a 113"])
        identNr(record=templateM, cluster=cluster, row=row)

        # The InventarNrSTxt should contain the full identNr
        inventar = templateM.xpath(
            "//m:repeatableGroup[@name='ObjObjectNumberGrp']"
            "/m:repeatableGroupItem/m:dataField[@name='InventarNrSTxt']/m:value/text()"
        )
        assert inventar == ["VII a 113"]

    def test_identNr_unknown_cluster_type_raises(self, templateM):
        """identNr should raise TypeError for unknown cluster type."""
        cluster = {
            "type": "bogus",
            "fields": {
                "identNr": {"type": "column", "value": 0},
            },
        }
        row = _make_row(["VII a 113"])
        with pytest.raises(TypeError, match="Unknown cluster type"):
            identNr(record=templateM, cluster=cluster, row=row)


# ── Stub callbacks (no-op functions) ─────────────────────────────────────


class TestStubCallbacks:
    """These callbacks are currently stubs (pass). Verify they are callable
    and don't raise when invoked with the expected signature."""

    STUB_CALLBACKS = [
        BemerkungenSammlungen,
        Besitzart,
        Beteiligte,
        Datierung,
        ErwerbDatum,
        ErwerbNotiz,
        Erwerbungsart,
        Objektreferenz,
        Sachbegriff,
        Status,
        SystematikArt,
        Titel,
        weitereNr,
        Zugang,
    ]

    @pytest.mark.parametrize("cb", STUB_CALLBACKS)
    def test_callable_without_error(self, templateM, cb):
        """Each stub callback should be callable with (record, cluster=, row=)."""
        cluster = {"type": "set", "fields": {}}
        row = _make_row([])
        # Should not raise
        cb(templateM, cluster=cluster, row=row)

    def test_aufschrift_sets_missing(self):
        """Aufschrift is the one stub that sets global missing=True."""
        # Reset the module-level missing
        write_xml.missing = False
        template = Module(xml=TEMPLATE_XML)
        cluster = {"type": "set", "fields": {}}
        row = _make_row([])
        Aufschrift(template, cluster=cluster, row=row)
        assert write_xml.missing is True

    def test_anzahl_teile_callable(self, templateM):
        """AnzahlTeile is a stub that prints a message."""
        cluster = {"type": "set", "fields": {}}
        row = _make_row([])
        # Should not raise
        write_xml.AnzahlTeile(templateM, cluster=cluster, row=row)


# ── create_xml ────────────────────────────────────────────────────────────


class TestCreateXml:
    def test_template_not_single_record_raises(self):
        """create_xml should raise TypeError if template doesn't have exactly one record."""
        multi_xml = """\
<application xmlns="http://www.zetcom.com/ria/ws/module">
  <modules>
    <module name="Object" totalSize="2">
      <moduleItem id="1"/>
      <moduleItem id="2"/>
    </module>
  </modules>
</application>"""
        conf = {
            "templateM": Module(xml=multi_xml),
            "fields2": {},
            "project_dir": None,
        }
        row = _make_row([])
        with pytest.raises(TypeError, match="Template does not have a single record"):
            create_xml(conf=conf, row=row)

    def test_unknown_callback_raises(self, templateM):
        """create_xml should raise ValueError for unknown callback name."""
        conf = {
            "templateM": templateM,
            "fields2": {
                "testCluster": {
                    "cb": "nonexistent_callback",
                    "type": "set",
                    "fields": {},
                }
            },
            "project_dir": None,
        }
        row = _make_row([])
        with pytest.raises(ValueError, match="Unknown callback 'nonexistent_callback'"):
            create_xml(conf=conf, row=row)

    def test_missing_config_key_raises(self, templateM):
        """create_xml should raise KeyError if 'templateM' is missing from conf."""
        conf = {"fields2": {}}
        row = _make_row([])
        with pytest.raises(KeyError):
            create_xml(conf=conf, row=row)
