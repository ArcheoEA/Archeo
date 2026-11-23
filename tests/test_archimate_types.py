"""Tests for the ArchiMate type catalogs (3.2 / 4.0)."""

from __future__ import annotations

from ArcheoConverter.formalisms.archimate import types as at


def test_catalog_sizes():
    """The 3.2 catalog is complete; 4.0 adds the Resource concept."""
    assert len(at.ELEMENT_TYPES_32) >= 50
    assert len(at.ELEMENT_TYPES_40) == len(at.ELEMENT_TYPES_32) + 1
    assert "resource" in at.ELEMENT_TYPES_40
    assert "resource" not in at.ELEMENT_TYPES_32
    assert at.ELEMENT_TYPES_40["resource"].abstract is True
    assert len(at.RELATIONSHIP_TYPES_32) == 13
    assert at.RELATIONSHIP_TYPES_40 == at.RELATIONSHIP_TYPES_32


def test_perspectives_cover_all_layers():
    """Every 3.2 concept is assigned to a perspective."""
    expected = {"motivation", "business", "application", "technology",
                "physical", "implementation", "extension"}
    assert {info.perspective for info in at.ELEMENT_TYPES_32.values()} == expected


def test_xml_roundtrip_32():
    """xml <-> canonical names round-trip for every 3.2 element."""
    for canonical, info in at.ELEMENT_TYPES_32.items():
        assert at.canonical_from_xml(info.xml_name, "3.2") == canonical
        assert at.xml_name_from_canonical(canonical, "3.2") == info.xml_name


def test_xml_roundtrip_40():
    """xml <-> canonical names round-trip for every 4.0 element."""
    for canonical, info in at.ELEMENT_TYPES_40.items():
        assert at.canonical_from_xml(info.xml_name, "4.0") == canonical
        assert at.xml_name_from_canonical(canonical, "4.0") == info.xml_name


def test_version_specific_lookups():
    """Lookups respect the requested version."""
    assert at.element_info("resource", "3.2") is None
    assert at.element_info("resource", "4.0") is not None
    assert at.element_info("business-actor", "3.2") is not None
    assert at.xml_name_from_canonical("business-actor", "3.2") == "businessActor"
    assert at.xml_name_from_canonical("means-of-realization", "3.2") == "meansOfRealization"
    assert at.xml_name_from_canonical("nope", "3.2") is None


def test_relationship_lookups():
    """Relationship xml names map to canonical names and back."""
    assert at.relationship_canonical_from_xml("serving") == "serving"
    assert at.relationship_canonical_from_xml("storing") == "storing"
    assert at.relationship_canonical_from_xml("unknownRel") is None
    assert at.relationship_display("serving") == "Serving"
    assert at.relationship_display("weird-type") == "Weird Type"


def test_display_names():
    """Display names are human readable."""
    assert at.element_display("business-actor") == "Business Actor"
    assert at.element_display("means-of-realization") == "Means of Realization"
    assert at.element_display("mystery-type") == "Mystery Type"


def test_folder_kinds():
    """The known folder kinds include the standard ArchiMate ones."""
    assert "business" in at.FOLDER_KINDS
    assert "technology" in at.FOLDER_KINDS
    assert "other" in at.FOLDER_KINDS
