import sys
import os

sys.path.append(os.path.join(os.getcwd(), "src"))

from archeo.model.basemodel.IdentityPart import IdentityPart
from archeo.model.basemodel.ModelBase import MODEL_CUSTOMIZATION_STANDARD

from archeo.model.archimatemodel.ArchimateModel import ArchimateModel
from archeo.model.archimatemodel.ArchimateElement import ArchimateElement
from archeo.model.archimatemodel.ArchimateRelation import ArchimateRelation
from archeo.model.archimatemodel.ArchimateFolder import ArchimateFolder

from pprint import pprint

def test_archimatebase():
    try:
        # Pre-declaration of objects used in tests
        model1 : ArchimateModel
        model2 : ArchimateModel
        id_elem1 : IdentityPart
        elem1 : ArchimateElement
        elem2 : ArchimateElement
        id_rel : IdentityPart
        rel1 : ArchimateRelation
        id_folder : IdentityPart
        folder1 : ArchimateFolder
        folder2 : ArchimateFolder 

        ###########################################################################
        # Test ArchimateModel
        print("Testing ArchimateModel...")
        
        # Create an ArchimateModel instance with default version
        model1 = ArchimateModel(pName="TestModel", pFormalism="ArchiMate 3.1", pDescription="A simple model")
        
        assert model1.name == "TestModel"
        assert model1.formalism == "ArchiMate 3.1"
        assert model1.version == "0.0.1"
        assert model1.customization == MODEL_CUSTOMIZATION_STANDARD
        assert model1.description == "A simple model"
    
        print("\nArchimateModel model1:")
        pprint(model1)
        pprint(model1.__hash__())

        # Create another ArchimateModel with explicit version
        model2 = ArchimateModel(pName="TestModel", pFormalism="ArchiMate 3.1", pVersion="1.0.0", pDescription="Same model, with version upgrade")
        
        assert model2.name == "TestModel"
        assert model2.formalism == "ArchiMate 3.1"
        assert model2.version == "1.0.0"
        assert model2.customization == MODEL_CUSTOMIZATION_STANDARD
        assert model2.description == "Same model, with version upgrade"
    
        # Verify equality and hash based on name, formalism, version (inherited from ModelBase)
        assert model1 != model2
        assert model1.__hash__() != model2.__hash__()

        ###########################################################################
        # Test ArchimateElement
        print("\nTesting ArchimateElement...")

        id_elem1 = IdentityPart(pName="BusinessProcess", pType="BusinessProcess")

        elem1 = ArchimateElement(pName="BusinessProcess", pType="BusinessProcess", pReferenceId=id_elem1, pSourcesId=[], pDescription="A business process")

        assert elem1.name == "BusinessProcess"
        assert elem1.type == "BusinessProcess"
        assert elem1.referenceId == id_elem1
        assert elem1.sourcesId == []
        assert elem1.description == "A business process"

        print("\nArchimateElement elem1:")
        pprint(elem1)
        pprint(elem1.__hash__())

        # Create another element with auto-generated referenceId
        elem2 = ArchimateElement(pName="DataObject", pType="DataObject", pDescription="A data object")
        
        assert elem2.name == "DataObject"
        assert elem2.type == "DataObject"
        assert elem2.referenceId is not None
        assert elem2.sourcesId == []
        assert elem2.description == "A data object"

        print("\nArchimateElement elem2:")
        pprint(elem2)
        pprint(elem2.__hash__())

        # Test equality based on referenceId (inherited from ElementBase)
        assert elem1 != elem2
        assert elem1.__hash__() != elem2.__hash__()

        ###########################################################################
        # Test ArchimateRelation
        print("\nTesting ArchimateRelation...")

        id_rel = IdentityPart(pName="AccessRelation", pType="Access")

        rel1 = ArchimateRelation(pName="AccessRelation", pType="Access", pOrigElement=id_elem1, pDestElement=elem2.referenceId, pReferenceId=id_rel)
        
        assert rel1.name == "AccessRelation"
        assert rel1.type == "Access"
        assert rel1.referenceId == id_rel
        assert rel1.origElement == id_elem1
        assert rel1.destElement == elem2.referenceId
        
        print("\nArchimateRelation rel1:")
        pprint(rel1)
        pprint(rel1.__hash__())

        ###########################################################################
        # Test ArchimateFolder
        print("\nTesting ArchimateFolder...")

        id_folder = IdentityPart(pName="Processes", pType="Folder")

        folder1 = ArchimateFolder(pName="Processes", pType="Folder", pReferenceId=id_folder, pDescription="Root folder")
        
        assert folder1.name == "Processes"
        assert folder1.type == "Folder"
        assert folder1.referenceId == id_folder
        assert folder1.description == "Root folder"

        print("\nArchimateFolder folder1:")
        pprint(folder1)
        pprint(folder1.__hash__())

        # Test nested folder (parentFolder is accepted but not stored in current implementation, we just verify instantiation works)
        folder2 = ArchimateFolder(pName="SubProcesses", pType="Folder", pParentFolder=folder1, pDescription="Sub-folder")
        
        assert folder2.name == "SubProcesses"
        assert folder2.type == "Folder"
        assert folder2.referenceId is not None
        assert folder2.description == "Sub-folder"

        print("\nArchimateFolder folder2:")
        pprint(folder2)
        pprint(folder2.__hash__())

    except AssertionError as e:
        print(f"Assertion failed during tests of ArchimateModel: {e}")

    except TypeError as e:
        print(f"Type error during tests of ArchimateModel: {e}")

    except Exception as e:
        print(f"Exception error during tests of ArchimateModel: {e}")

if __name__ == '__main__':
    test_archimatebase()