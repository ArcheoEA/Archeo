from archeo.model.basemodel.IdentityPart import IdentityPart
from archeo.model.basemodel.ModelBase import ModelBase

from pprint import pprint

if __name__ == '__main__':
    id1 : IdentityPart = IdentityPart(pName="Model1", pType="TypeA")

    print(f"\nIdentityPart id1:")
    pprint(id1)

    model1 : ModelBase = ModelBase(pName="Model1", pType="TypeA", pReferenceId=id1, pSourcesId=[], pDescription="This is a test model")

    print(f"\nModelBase model1:")
    pprint(model1)
    