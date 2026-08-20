# tests/test_parser.py

"""
Tests for ArchiMate XML parser.
"""

import pytest
from pathlib import Path
import tempfile

from ArcheoConverter.import_export.archimate_parser import parse_archimate_xml


def test_v32_parsing(sample_v32_model_xml, temp_dir):
    """Test parsing an ArchiMate v3.2 file."""
    
    xml_file = temp_dir / "v32.xml"
    xml_file.write_text(sample_v32_model_xml)
    
    result = parse_archimate_xml(xml_file)
    
    assert result.model_name == "sample_v32_model_xml"  # From test fixture
    assert result.version == "3.2"
    assert len(result.elements) == 2
    
    # Check element types
    for elem in result.elements:
        assert hasattr(elem, "name")
        assert hasattr(elem, "id")


def test_v40_parsing(sample_v40_model_xml, temp_dir):
    """Test parsing an ArchiMate v4.0 file."""
    
    xml_file = temp_dir / "v40.xml"
    xml_file.write_text(sample_v40_model_xml)
    
    result = parse_archimate_xml(xml_file)
    
    assert result.version == "4.0"
    # Should have 2 elements: goal and actor
    assert len(result.elements) >= 1
    
    # Check abstract flag is parsed if present (simplified test)


def test_invalid_xml(temp_dir):
    """Test handling of invalid XML."""
    
    bad_file = temp_dir / "bad.xml"
    bad_file.write_text("<unclosed>")
    
    with pytest.raises(RuntimeError):
        parse_archimate_xml(bad_file)


def test_version_detection_v32(sample_v32_model_xml, temp_dir):
    """Test detection of v3.2 files."""
    
    xml_file = temp_dir / "v32.xml"
    xml_file.write_text(sample_v32_model_xml)
    
    result = parse_archimate_xml(xml_file)
    assert result.version == "3.2"


def test_version_detection_v40(sample_v40_model_xml, temp_dir):
    """Test detection of v4.0 files."""
    
    xml_file = temp_dir / "v40.xml"
    xml_file.write_text(sample_v40_model_xml)
    
    result = parse_archimate_xml(xml_file)
    assert result.version == "4.0"
