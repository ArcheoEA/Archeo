import sys
import os
sys.path.append(f"{os.getcwd()}\\src")

from archeo.model.basemodel.IdentityPart import IdentityPart
from archeo.model.basemodel.ModelBase import ModelBase

from pprint import pprint
def test_modelbase():
    try:

        ###########################################################################
        # Create several IdentityPart instances with different attributes, and validate their properties and hash values

        # Create an IdentityPart instance with name "Model1", type "TypeA", and id generated automatically
        id1 : IdentityPart = IdentityPart(pName="Model1", pType="TypeA")

        try:
            # Validate the attributes of id1 and print its properties and hash value
            assert id1.name == "Model1"
            assert id1.type == "TypeA"
            assert id1.version == "0.0.1"

        except AssertionError as e:
            print(f"Assertion failed for IdentityPart id1: {e}")

        print(f"\nIdentityPart id1:")
        pprint(id1)
        pprint(id1.__hash__())
        
        # Create another IdentityPart instance with name "Model2", type "TypeB", and id generated automatically
        id2 : IdentityPart = IdentityPart(pName="Model2", pType="TypeB")

        try:
            # Validate the attributes of id2 and print its properties and hash value
            assert id2.name == "Model2"
            assert id2.type == "TypeB"
            assert id2.version == "0.0.1"

        except AssertionError as e:
            print(f"Assertion failed for IdentityPart id2: {e}")

        print(f"\nIdentityPart id2:")
        pprint(id2)
        pprint(id2.__hash__())
        
        # Create a third IdentityPart instance with name "Model3", type "TypeC", id generated automatically, and version "1.1.2"
        id3 : IdentityPart = IdentityPart(pName="Model3", pType="TypeC", pVersion="1.1.2")

        try:
            # Validate the attributes of id3 and print its properties and hash value
            assert id3.name == "Model3"
            assert id3.type == "TypeC"
            assert id3.version == "1.1.2"

        except AssertionError as e:
            print(f"Assertion failed for IdentityPart id3: {e}")

        print(f"\nIdentityPart id3:")
        pprint(id3)
        pprint(id3.__hash__())

        # Create a fourth IdentityPart instance with the same name, type and id as id1, but with a different version "0.0.2"
        id1_v2 : IdentityPart = IdentityPart(pName="Model1", pType="TypeA", pId=id1.id, pVersion="0.0.2")

        try:
            # Validate the attributes of id1_v2 and print its properties and hash value
            assert id1_v2.name == "Model1"
            assert id1_v2.type == "TypeA"
            assert id1_v2.id == id1.id
            assert id1_v2.version == "0.0.2"

        except AssertionError as e:
            print(f"Assertion failed for IdentityPart id1_v2: {e}")

        print(f"\nIdentityPart id1_v2:")
        pprint(id1_v2)
        pprint(id1_v2.__hash__())

        # Validate that id1 and id2 are not considered equal based on their name, type and id,
        # and that their hash values are different
        try:
            assert id1 != id2
            assert id1.__hash__() != id2.__hash__()

        except AssertionError as e:
            print(f"Assertion failed for IdentityPart comparison: {e}")

        # Validate that id1 and id1_v2 are considered equal based on their name, type and id,
        # and that their hash values are the same, even though they have different versions
        try:
            assert id1_v2 == id1
            assert id1_v2.__hash__() == id1.__hash__()

        except AssertionError as e:
            print(f"Assertion failed for IdentityPart comparison: {e}")

        ###########################################################################
        # Create several ModelBase instances with different attributes, and validate their properties and hash values

        # Create a ModelBase instance with name "Model1", type "TypeA", referenceId set to id1, an empty list of sourcesId, and a description
        model1 : ModelBase = ModelBase(pName="Model1",
                                    pType="TypeA",
                                    pReferenceId=id1,
                                    pSourcesId=[],
                                    pDescription="This is a test model")
        
        # Validate the attributes of model1 and print its properties and hash value
        try:
            assert model1.name == "Model1"
            assert model1.type == "TypeA"
            assert model1.referenceId == id1
            assert model1.referenceId.__hash__() == id1.__hash__()
            assert model1.sourcesId == []
            assert model1.description == "This is a test model"

        except AssertionError as e:
            print(f"Assertion failed for ModelBase model1: {e}")

        print(f"\nModelBase model1:")
        pprint(model1)
        pprint(model1.__hash__())

        # Create another ModelBase instance with name "Model2", type "TypeB", referenceId generated automatically, sourcesId set to [id2, id3], and a description
        model2 : ModelBase = ModelBase(pName="Model2",
                                    pType="TypeB",
                                    pReferenceId=None,
                                    pSourcesId=[id2, id3],
                                    pDescription="This is another test model")
        
        # Validate the attributes of model2 and print its properties and hash value
        try:
            assert model2.name == "Model2"
            assert model2.type == "TypeB"
            assert model2.referenceId is not None
            assert model2.__hash__() == model2.referenceId.__hash__()
            assert model2.sourcesId == [id2, id3]
            assert model2.description == "This is another test model"

        except AssertionError as e:
            print(f"Assertion failed for ModelBase model2: {e}")
        
        print(f"\nModelBase model2:")
        pprint(model2.referenceId)
        pprint(model2)
        pprint(model2.__hash__())

        # validate that model1 and model2 are not considered equal based on their name, type and referenceId,
        # and that their hash values are different
        try:
            assert model1 != model2
            assert model1.__hash__() != model2.__hash__()

        except AssertionError as e:
            print(f"Assertion failed for ModelBase model1 != model2: {e}")

        # Create a third ModelBase instance with the same name, type and referenceId as model1, but with a different version in the referenceId and a different description
        model1_v2 : ModelBase = ModelBase(pName="Model1", pType="TypeA", pReferenceId=id1_v2, pSourcesId=[], pDescription="This is a new version of model1")

        # Validate the attributes of model1_v2 and print its properties and hash value
        try:
            assert model1_v2.name == "Model1"
            assert model1_v2.type == "TypeA"
            assert model1_v2.referenceId == id1_v2
            assert model1_v2.sourcesId == []
            assert model1_v2.description == "This is a new version of model1"

        except AssertionError as e:
            print(f"Assertion failed for ModelBase model1_v2: {e}")

        print(f"\nModelBase model1_v2:")
        pprint(model1_v2)
        pprint(model1_v2.__hash__())

        # Validate that model1 and model1_v2 are considered equal based on their name, type and referenceId,
        # and that their hash values are the same, even though they have different versions
        try:
            assert model1_v2 == model1
            assert model1_v2.__hash__() == model1.__hash__()

        except AssertionError as e:
            print(f"Assertion failed for ModelBase model1_v2 == model1: {e}")

    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")

# Run the test function if this script is executed directly
if __name__ == '__main__':
    test_modelbase()
