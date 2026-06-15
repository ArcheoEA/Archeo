import pytest
import sys
import os

sys.path.append(os.path.join(os.getcwd(), "src"))

from app.core.store import store, ArchimateModel, ArchiMateVersion
from app.models.layers import Stakeholder
from app.core.engine import ArchimateEngine

def test_model_migration():
    # Setup
    m_id = "test-1"
    model = ArchimateModel(model_id=m_id, name="Company Architecture", version=ArchiMateVersion.V3_2)
    store.add_model(model)
    
    # Execute
    migrated = ArchimateEngine.migrate_version(m_id, ArchiMateVersion.V4_0)
    
    # Verify
    assert migrated.version == ArchiMateVersion.V4_0

def test_compare_models():
    # Setup Model A
    ma = ArchimateModel(model_id="a", name="Model A", version=ArchiMateVersion.V3_2)
    ma.elements["1"] = Stakeholder(name="CEO")
    store.add_model(ma)
    
    # Setup Model B
    mb = ArchimateModel(model_id="b", name="Model B", version=ArchiMateVersion.V3_2)
    mb.elements["2"] = Stakeholder(name="CFO")
    store.add_model(mb)
    
    # Execute
    diff = ArchimateEngine.compare_models("a", "b")
    
    # Verify
    assert "CEO" in diff["only_in_a"]
    assert "CFO" in diff["only_in_b"]
