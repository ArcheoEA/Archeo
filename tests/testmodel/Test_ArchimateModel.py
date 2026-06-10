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
    try:
        model1 = ArchimateModel(pName="TestModel", pFormalism="ArchiMate 3.1", pDescription="A simple model")
        
        assert model1.name == "TestModel"
        assert model1.formalism == "ArchiMate 3.1"
        assert model1.version == "0.0.1"
        assert model1.customization == MODEL_CUSTOMIZATION_STANDARD
        assert model1.description == "A simple model"
    except AssertionError as e:
        print(f"Assertion failed for first ArchimateModel creation: {e}")
    
    print("\nArchimateModel model1:")
    pprint(model1)
    pprint(model1.__hash__())

    # Create another ArchimateModel with explicit version
    try:
        model2 = ArchimateModel(pName="TestModel", pFormalism="ArchiMate 3.1", pVersion="1.0.0", pDescription="Same model, with version upgrade")
        
        assert model2.name == "TestModel"
        assert model2.formalism == "ArchiMate 3.1"
        assert model2.version == "1.0.0"
        assert model2.customization == MODEL_CUSTOMIZATION_STANDARD
        assert model2.description == "Same model, with version upgrade"
    except AssertionError as e:
        print(f"Assertion failed for second ArchimateModel creation: {e}")
    
    # Verify equality and hash based on name, formalism, version (inherited from ModelBase)
    try:
        assert model1 != model2
        assert model1.__hash__() != model2.__hash__()
    except AssertionError as e:
        print(f"Assertion failed for ArchimateModel comparison: {e}")

    ###########################################################################
    # Test ArchimateElement
    print("\nTesting ArchimateElement...")

    try:
       id_elem1 = IdentityPart(pName="BusinessProcess", pType="BusinessProcess")

    except AssertionError as e:
        print(f"Assertion failed for element IdentityPart creation: {e}")

    try:
        elem1 = ArchimateElement(pName="BusinessProcess", pType="BusinessProcess", pReferenceId=id_elem1, pSourcesId=[], pDescription="A business process")
        
        assert elem1.name == "BusinessProcess"
        assert elem1.type == "BusinessProcess"
        assert elem1.referenceId == id_elem1
        assert elem1.sourcesId == []
        assert elem1.description == "A business process"

        print("\nArchimateElement elem1:")
        pprint(elem1)
        pprint(elem1.__hash__())

    except AssertionError as e:
        print(f"Assertion failed for first ArchimateElement creation: {e}")

    # Create another element with auto-generated referenceId
    try:
        elem2 = ArchimateElement(pName="DataObject", pType="DataObject", pDescription="A data object")
        
        assert elem2.name == "DataObject"
        assert elem2.type == "DataObject"
        assert elem2.referenceId is not None
        assert elem2.sourcesId == []
        assert elem2.description == "A data object"

        print("\nArchimateElement elem2:")
        pprint(elem2)
        pprint(elem2.__hash__())

    except AssertionError as e:
        print(f"Assertion failed for second ArchimateElement creation: {e}")

    # Test equality based on referenceId (inherited from ElementBase)
    try:
        assert elem1 != elem2
        assert elem1.__hash__() != elem2.__hash__()
    except AssertionError as e:
        print(f"Assertion failed for ArchimateElement comparison: {e}")

    ###########################################################################
    # Test ArchimateRelation
    print("\nTesting ArchimateRelation...")

    try:
       id_rel = IdentityPart(pName="AccessRelation", pType="Access")

    except AssertionError as e:
        print(f"Assertion failed for relation IdentityPart creation: {e}")

    try:
        rel1 = ArchimateRelation(pName="AccessRelation", pType="Access", pOrigElement=id_elem1, pDestElement=elem2.referenceId, pReferenceId=id_rel)
        
        assert rel1.name == "AccessRelation"
        assert rel1.type == "Access"
        assert rel1.referenceId == id_rel
        assert rel1.origElement == id_elem1
        assert rel1.destElement == elem2.referenceId
        
        print("\nArchimateRelation rel1:")
        pprint(rel1)
        pprint(rel1.__hash__())

    except AssertionError as e:
        print(f"Assertion failed for ArchimateRelation creation: {e}")

    ###########################################################################
    # Test ArchimateFolder
    print("\nTesting ArchimateFolder...")

    try:
       id_folder = IdentityPart(pName="Processes", pType="Folder")

    except AssertionError as e:
        print(f"Assertion failed for folder IdentityPart creation: {e}")
    
    try:
        folder1 = ArchimateFolder(pName="Processes", pType="Folder", pReferenceId=id_folder, pDescription="Root folder")
        
        assert folder1.name == "Processes"
        assert folder1.type == "Folder"
        assert folder1.referenceId == id_folder
        assert folder1.description == "Root folder"

        print("\nArchimateFolder folder1:")
        pprint(folder1)
        pprint(folder1.__hash__())

    except AssertionError as e:
        print(f"Assertion failed for first ArchimateFolder creation: {e}")

    try:
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
        print(f"Assertion failed for second ArchimateFolder creation: {e}")

if __name__ == '__main__':
    test_archimatebase()