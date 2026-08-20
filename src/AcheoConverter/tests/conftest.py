# tests/conftest.py

"""
Pytest configuration and fixtures.
"""

import pytest
from pathlib import Path
import tempfile
import os


@pytest.fixture(scope="session")
def sample_xml_path():
    """Create a minimal valid ArchiMate XML file for testing."""
    
    # Create temp directory if needed
    with tempfile.TemporaryDirectory() as tmpdir:
        xml_file = Path(tmpdir) / "sample_v32.xml"
        
        # Write sample XML (v3.2)
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<archimate:ArchimateDiagramModel xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:archimate="http://www.archimatetool.com/archimate">
    <archimate:businessActor name="Business Actor 1" id="id1"/>
    <archimate:applicationComponent name="App Component 1" id="id2"/>
</archimate:ArchimateDiagramModel>'''
        
        xml_file.write_text(xml_content)
        yield xml_file


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_v32_model_xml():
    """Sample ArchiMate 3.2 model XML content."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<archimate:ArchimateDiagramModel xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:archimate="http://www.archimatetool.com/archimate">
    <archimate:businessActor name="CEO" id="actor1"/>
    <archimate:businessRole name="CFO" id="role1"/>
</archimate:ArchimateDiagramModel>
'''


@pytest.fixture
def sample_v40_model_xml():
    """Sample ArchiMate 4.0 model XML content."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<archimate:ArchimateDiagramModel xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:archimate="http://www.opengroup.org/xsd/archimate/4.0/"
    isAbstract="false">
    <archimate:goal name="Digital Transformation" id="goal1"/>
    <archimate:businessActor name="CEO" id="actor1"/>
</archimate:ArchimateDiagramModel>
'''
