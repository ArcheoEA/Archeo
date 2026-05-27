import sys
import os
sys.path.append(f"{os.getcwd()}\\src")

from archeo.model.archimatemodel.ElementArchimate import ElementArchimate
from archeo.model.archimatemodel.ModelArchimate import ModelArchimate

from pprint import pprint

def test_archimatebase():
    archimate1 : ElementArchimate = ElementArchimate(pName="Archimate1",
                                                pType="TypeA",
                                                pReferenceId=None,
                                                pSourcesId=[],
                                                pDescription="This is a test Archimate element")
    
    assert archimate1.name == "Archimate1"
    assert archimate1.type == "TypeA"
    assert archimate1.referenceId is not None
    assert archimate1.sourcesId == []
    assert archimate1.description == "This is a test Archimate element"

    pprint(archimate1)

# Run the test function if this script is executed directly
if __name__ == '__main__':
    test_archimatebase()
