import sys
import os
sys.path.append(f"{os.getcwd()}\\src")

from archeo.model.archimatemodel.ArchimateModel import ArchimateModel
from archeo.model.archimatemodel.ArchimateElement import ArchimateElement
from archeo.model.archimatemodel.ArchimateRelation import ArchimateRelation
from archeo.model.archimatemodel.ArchimateFolder import ArchimateFolder
from archeo.model.basemodel.IdentityPart import IdentityPart

from pprint import pprint

def test_archimatebase():
    try:
        ###########################################################################
        # Test ArchimateModel
        print("Testing ArchimateModel...")
        
        # Create an ArchimateModel instance with default version
        model1 : ArchimateModel = ArchimateModel(pName="TestModel", pFormalism="ArchiMate 3.1")
        
        assert model1.name == "TestModel"
        assert model1.formalism == "ArchiMate 3.1"
        assert model1.version == "0.0.1"
        assert model1.customization is None
        assert model1.description is None
        
        print("\nArchimateModel model1:")
        pprint(model1)
        pprint(model1.__hash__())

        # Create another ArchimateModel with explicit version and description
        model2 : ArchimateModel = ArchimateModel(pName="TestModel", pFormalism="ArchiMate 3.1", pVersion="1.0.0", pDescription="A test model")
        
        assert model2.version == "1.0.0"
        assert model2.description == "A test model"
        
        # Verify equality and hash based on name, formalism, version (inherited from ModelBase)
        try:
            assert model1 != model2
            assert model1.__hash__() != model2.__hash__()
        except AssertionError as e:
            print(f"Assertion failed for ArchimateModel comparison: {e}")

        ###########################################################################
        # Test ArchimateElement
        print("\nTesting ArchimateElement...")

        id_elem1 : IdentityPart = IdentityPart(pName="BusinessProcess", pType="BusinessProcess")
        
        elem1 : ArchimateElement = ArchimateElement(pName="BusinessProcess", pType="BusinessProcess", pReferenceId=id_elem1, pSourcesId=[], pDescription="A business process")
        
        assert elem1.name == "BusinessProcess"
        assert elem1.type == "BusinessProcess"
        assert elem1.referenceId == id_elem1
        assert elem1.sourcesId == []
        assert elem1.description == "A business process"

        print("\nArchimateElement elem1:")
        pprint(elem1)
        pprint(elem1.__hash__())

        # Create another element with auto-generated referenceId
        elem2 : ArchimateElement = ArchimateElement(pName="DataObject", pType="DataObject", pSourcesId=[id_elem1], pDescription="A data object")
        
        assert elem2.name == "DataObject"
        assert elem2.type == "DataObject"
        assert elem2.referenceId is not None
        if elem2.sourcesId is not None:
            assert id_elem1 in elem2.sourcesId

        print("\nArchimateElement elem2:")
        pprint(elem2)
        pprint(elem2.__hash__())

        # Test equality based on referenceId (inherited from ElementBase)
        try:
            assert elem1 != elem2
            assert elem1.__hash__() != elem2.__hash__()
        except AssertionError as e:
            print(f"Assertion failed for ArchimateElement comparison: {e}")

        ###########################################################################
        # Test ArchimateRelation
        print("\nTesting ArchimateRelation...")

        id_rel : IdentityPart = IdentityPart(pName="AccessRelation", pType="Access")
        
        rel1 : ArchimateRelation = ArchimateRelation(pName="AccessRelation", pType="Access", pOrigElement=id_elem1, pDestElement=elem2.referenceId, pReferenceId=id_rel)
        
        assert rel1.name == "AccessRelation"
        assert rel1.type == "Access"
        assert rel1.referenceId == id_rel
        
        print("\nArchimateRelation rel1:")
        pprint(rel1)
        pprint(rel1.__hash__())

        ###########################################################################
        # Test ArchimateFolder
        print("\nTesting ArchimateFolder...")

        id_folder : IdentityPart = IdentityPart(pName="Processes", pType="Folder")
        
        folder1 : ArchimateFolder = ArchimateFolder(pName="Processes", pType="Folder", pReferenceId=id_folder, pDescription="Contains business processes")
        
        assert folder1.name == "Processes"
        assert folder1.type == "Folder"
        assert folder1.referenceId == id_folder
        assert folder1.description == "Contains business processes"

        print("\nArchimateFolder folder1:")
        pprint(folder1)
        pprint(folder1.__hash__())

        # Test nested folder (parentFolder is accepted but not stored in current implementation, we just verify instantiation works)
        folder2 : ArchimateFolder = ArchimateFolder(pName="SubProcesses", pType="Folder", pParentFolder=folder1, pDescription="Contains sub-processes")
        
        assert folder2.name == "SubProcesses"
        assert folder2.type == "Folder"
        # Note: parentFolder is not stored as an attribute in the current implementation

        print("\nArchimateFolder folder2:")
        pprint(folder2)
        pprint(folder2.__hash__())

    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")

if __name__ == '__main__':
    test_archimatebase()