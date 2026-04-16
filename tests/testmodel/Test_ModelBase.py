import sys
import os
sys.path.append(f"{os.getcwd()}\\src")

from archeo.model.basemodel.IdentityPart import IdentityPart
from archeo.model.basemodel.ElementBase import ElementBase

from pprint import pprint
def test_elementbase():
    try:

        ###########################################################################
        # Create several IdentityPart instances with different attributes, and validate their properties and hash values

        # Create an IdentityPart instance with name "Element1", type "TypeA", and id generated automatically
        id1 : IdentityPart = IdentityPart(pName="Element1", pType="TypeA")

        try:
            # Validate the attributes of id1 and print its properties and hash value
            assert id1.name == "Element1"
            assert id1.type == "TypeA"
            assert id1.version == "0.0.1"

        except AssertionError as e:
            print(f"Assertion failed for IdentityPart id1: {e}")

        print(f"\nIdentityPart id1:")
        pprint(id1)
        pprint(id1.__hash__())
        
        # Create another IdentityPart instance with name "Element2", type "TypeB", and id generated automatically
        id2 : IdentityPart = IdentityPart(pName="Element2", pType="TypeB")

        try:
            # Validate the attributes of id2 and print its properties and hash value
            assert id2.name == "Element2"
            assert id2.type == "TypeB"
            assert id2.version == "0.0.1"

        except AssertionError as e:
            print(f"Assertion failed for IdentityPart id2: {e}")

        print(f"\nIdentityPart id2:")
        pprint(id2)
        pprint(id2.__hash__())
        
        # Create a third IdentityPart instance with name "Element3", type "TypeC", id generated automatically, and version "1.1.2"
        id3 : IdentityPart = IdentityPart(pName="Element3", pType="TypeC", pVersion="1.1.2")

        try:
            # Validate the attributes of id3 and print its properties and hash value
            assert id3.name == "Element3"
            assert id3.type == "TypeC"
            assert id3.version == "1.1.2"

        except AssertionError as e:
            print(f"Assertion failed for IdentityPart id3: {e}")

        print(f"\nIdentityPart id3:")
        pprint(id3)
        pprint(id3.__hash__())

        # Create a fourth IdentityPart instance with the same name, type and id as id1, but with a different version "0.0.2"
        id1_v2 : IdentityPart = IdentityPart(pName="Element1", pType="TypeA", pId=id1.id, pVersion="0.0.2")

        try:
            # Validate the attributes of id1_v2 and print its properties and hash value
            assert id1_v2.name == "Element1"
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
        # Create several ElementBase instances with different attributes, and validate their properties and hash values

        # Create a ElementBase instance with name "Element1", type "TypeA", referenceId set to id1, an empty list of sourcesId, and a description
        element1 : ElementBase = ElementBase(pName="Element1",
                                    pType="TypeA",
                                    pReferenceId=id1,
                                    pSourcesId=[],
                                    pDescription="This is a test element")
        
        # Validate the attributes of Element1 and print its properties and hash value
        try:
            assert element1.name == "Element1"
            assert element1.type == "TypeA"
            assert element1.referenceId == id1
            assert element1.referenceId.__hash__() == id1.__hash__()
            assert element1.sourcesId == []
            assert element1.description == "This is a test element"

        except AssertionError as e:
            print(f"Assertion failed for ElementBase element1: {e}")

        print(f"\nElementBase element1:")
        pprint(element1)
        pprint(element1.__hash__())

        # Create another ElementBase instance with name "Element2", type "TypeB", referenceId generated automatically, sourcesId set to [id2, id3], and a description
        element2 : ElementBase = ElementBase(pName="Element2",
                                    pType="TypeB",
                                    pReferenceId=None,
                                    pSourcesId=[id2, id3],
                                    pDescription="This is another test element")
        
        # Validate the attributes of element2 and print its properties and hash value
        try:
            assert element2.name == "Element2"
            assert element2.type == "TypeB"
            assert element2.referenceId is not None
            assert element2.__hash__() == element2.referenceId.__hash__()
            assert element2.sourcesId == [id2, id3]
            assert element2.description == "This is another test element"

        except AssertionError as e:
            print(f"Assertion failed for ElementBase element2: {e}")

        print(f"\nElementBase element2:")
        pprint(element2.referenceId)
        pprint(element2)
        pprint(element2.__hash__())

        # validate that element1 and element2 are not considered equal based on their name, type and referenceId,
        # and that their hash values are different
        try:
            assert element1 != element2
            assert element1.__hash__() != element2.__hash__()

        except AssertionError as e:
            print(f"Assertion failed for ElementBase element1 != element2: {e}")

        # Create a third ElementBase instance with the same name, type and referenceId as element1, but with a different version in the referenceId and a different description
        element1_v2 : ElementBase = ElementBase(pName="Element1", pType="TypeA", pReferenceId=id1_v2, pSourcesId=[], pDescription="This is a new version of element1")

        # Validate the attributes of element1_v2 and print its properties and hash value
        try:
            assert element1_v2.name == "Element1"
            assert element1_v2.type == "TypeA"
            assert element1_v2.referenceId == id1_v2
            assert element1_v2.sourcesId == []
            assert element1_v2.description == "This is a new version of element1"

        except AssertionError as e:
            print(f"Assertion failed for ElementBase element1_v2: {e}")

        print(f"\nElementBase element1_v2:")
        pprint(element1_v2)
        pprint(element1_v2.__hash__())

        # Validate that element1 and element1_v2 are considered equal based on their name, type and referenceId,
        # and that their hash values are the same, even though they have different versions
        try:
            assert element1_v2 == element1
            assert element1_v2.__hash__() == element1.__hash__()

        except AssertionError as e:
            print(f"Assertion failed for ElementBase element1_v2 == element1: {e}")

    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")

# Run the test function if this script is executed directly
if __name__ == '__main__':
    test_elementbase()
