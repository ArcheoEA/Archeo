import sys
import os
sys.path.append(f"{os.getcwd()}\\src")

from archeo.model.archimatemodel.ArchimateModel import ArchimateModel
from archeo.model.archimatemodel.ArchimateElement import ArchimateElement
from archeo.model.archimatemodel.ArchimateRelation import ArchimateRelation
from archeo.model.archimatemodel.ArchimateFolder import ArchimateFolder

from pprint import pprint

def test_archimatebase():
    element1 : ArchimateElement = ArchimateElement(pName="ElementArchimate1",
                                                pType="TypeA",
                                                pReferenceId=None,
                                                pSourcesId=[],
                                                pDescription="This is a test Archimate element")
    
    assert element1.name == "ElementArchimate1"
    assert element1.type == "TypeA"
    assert element1.referenceId is not None
    assert element1.sourcesId == []
    assert element1.description == "This is a test Archimate element"

    pprint(element1)

# Run the test function if this script is executed directly
if __name__ == '__main__':
    test_archimatebase()
