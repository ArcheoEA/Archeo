# tests/test_version_migrator.py

"""
Tests for ArchiMate version migration.
"""

import pytest

from ArcheoConverter.converter.version_migrator import VersionMigrator, MigrationResult
from ArcheoConverter.core.model_store import ArchiModel
from ArcheoConverter.core.element import (
    ArchiElement_v32,
    ElementTypes_v32,
    ArchiElement_v40,
)


def test_version_migration_path_validation():
    """Test that invalid migration paths are rejected."""
    migrator = VersionMigrator()
    
    with pytest.raises(ValueError):
        migrator.migrate({}, "3.2", "5.0")
    
    with pytest.raises(ValueError):
        migrator.migrate({}, "5.0", "4.0")


def test_v32_to_v40_migration(sample_v32_model_xml, temp_dir):
    """Test v3.2 to v4.0 migration."""
    import xml.etree.ElementTree as ET
    
    # Create a model manually
    elem = ArchiElement_v32(
        name="Business Actor",
        type=ElementTypes_v32.BusinessActor,
        folder_id="f1"
    )
    
    model = ArchiModel(
        id="test-id",
        name="Test Model v3.2",
        version="3.2",
        elements={elem.id: elem}
    )
    
    migrator = VersionMigrator()
    result = migrator.migrate(model, "3.2", "4.0")
    
    assert isinstance(result, MigrationResult)
    assert result.original_model_id == "test-id"
    assert result.migrated_model["version"] == "4.0"
    assert len(result.migrated_model["elements"]) == 1
    
    # Check element migration
    new_elem = list(result.migrated_model["elements"].values())[0]
    assert isinstance(new_elem, ArchiElement_v40)
    assert new_elem.is_abstract is False


def test_v40_to_v32_migration():
    """Test v4.0 to v3.2 migration (lossy)."""
    
    # Create a v4.0 element with abstract flag
    elem = ArchiElement_v40(
        name="Abstract Goal",
        type=ElementTypes_v40.Goal,
        is_abstract=True
    )
    
    model = ArchiModel(
        id="test-id-40",
        name="Test Model v4.0",
        version="4.0",
        elements={elem.id: elem}
    )
    
    migrator = VersionMigrator()
    result = migrator.migrate(model, "4.0", "3.2")
    
    assert result.warnings
    # Warning should mention abstract element loss
    assert any("abstract" in w.lower() for w in result.warnings)
