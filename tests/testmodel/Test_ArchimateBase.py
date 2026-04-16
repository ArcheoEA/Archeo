import sys
import os
sys.path.append(f"{os.getcwd()}\\src")

from archeo.model.archimatemodel.ArchimateBase import ArchimateBase

from pprint import pprint

def test_archimatebase():
    archimate1 : ArchimateBase = ArchimateBase(pName="ArchimateModel1",
                                                pType="TypeA",
                                                pReferenceId=None,
                                                pSourcesId=[],
                                                pDescription="This is a test Archimate model")
    
    assert archimate1.name == "ArchimateModel1"
    assert archimate1.type == "TypeA"
    assert archimate1.referenceId is not None
    assert archimate1.sourcesId == []
    assert archimate1.description == "This is a test Archimate model"

    pprint(archimate1)

# Run the test function if this script is executed directly
if __name__ == '__main__':
    test_archimatebase()
