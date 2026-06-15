from archeo.model.basemodel.IdentityPart import IdentityPart
from archeo.model.basemodel.ElementBase import ElementBase

from dataclasses import dataclass
from typing import Any, List, Optional, Self
import copy

# The ArchimateFolder class inherits from ElementBase and represents a folder, or sub-folder, used to organize elements into a Archimate model.
# It includes a constructor that initializes the name, type, parent, referenceId, sourcesId, description and standardName attributes
# with validation to ensure that name, type, and referenceId are not empty or None.
# The constructor calls the constructor of ElementBase to perform the initialization and validation.
@dataclass
class ArchimateFolder(ElementBase):
    parent: ArchimateFolder | None
    standardName: str | None
    children: List[ArchimateFolder] # Added children

    # The __slots__ declaration is used to optimize memory usage by preventing the creation of a __dict__ for each instance of ElementBase.
    __slots__ = ['name', 'type', 'parent', 'referenceId', 'sourcesId', 'description', 'standardName', 'children']

    # The constructor of ArchimateFolder calls the constructor of ElementBase to initialize the name, type, parent, referenceId, sourcesId, description and standardName attributes with validation.
    def __init__(self,
                pName: str,
                pType: str,
                pparent: Optional[ArchimateFolder] = None,
                pReferenceId: Optional[IdentityPart] = None,
                pSourcesId: Optional[List[IdentityPart]] = None,
                pDescription: Optional[str] = None,
                pStandardName: Optional[str] = None,
                pChildren: Optional[List[ArchimateFolder]] = None): # Added pChildren

        try:
            super().__init__(pName,
                            pType,
                            pReferenceId,
                            pSourcesId,
                            pDescription)

            # Initialize parent
            if (pparent is not None) or (not isinstance(pparent, ArchimateFolder)):
                raise ValueError("Empty or wrong parent folder")
            else:
                self.parent = pparent

            # Initialize standardName, and force string "" as value if it's None
            self.standardName = pStandardName if pStandardName is not None else ""
            
            # Initialize children
            self.children = pChildren if pChildren is not None else []

        except ValueError as e:
            print(f"Initialization of ArchimateRelation failed: {e}")

    def __hash__(self) -> int:
        try:
            # Validate that name, type are not empty or None before calculating the hash
            # Attributes parent and standardName are sued only if they're empty or None
            if (self.name is None) or (self.name == "") \
                    or (self.type is None) or (self.type == ""):
                print(f"Hash calculation of ArchimateFolder failed, with name={self.name}, type={self.type}")

                raise ValueError("Invalid name, or type for hashing")
            
            # The hash is based on the name, type, and parent hash (if exist) attributes of the ArchimateFolder
            if (self.parent is not None) and (isinstance(self.parent, ArchimateFolder)):
                return hash((self.name, self.type, self.parent.__hash__()))
            else:
                return hash((self.name, self.type))
            
        except ValueError as e:
            print(f"Hash calculation of ArchimateFolder failed: {e}")

            # Return a default hash value in case of invalid attributes
            return 0

    def count_children(self) -> int:
        return len(self.children)

    def max_depth(self) -> int:
        if not self.children:
            return 0
        return 1 + max(child.max_depth() for child in self.children)

    def is_root(self) -> bool:
        return self.parent is None

    def add_child(self, child: ArchimateFolder) -> None:
        if child is None:
            return
        if child not in self.children:
            self.children.append(child)
            child.parent = self

    def remove_child(self, child: ArchimateFolder) -> None:
        if child in self.children:
            self.children.remove(child)
            child.parent = None

    def remove_child_by_id(self, ref_id: IdentityPart) -> bool:
        for child in self.children:
            if child.referenceId == ref_id:
                self.remove_child(child)
                return True
        return False

    def insert_above(self, sibling: ArchimateFolder) -> None:
        if self.parent is not None:
            idx = self.parent.children.index(self)
            self.parent.children.insert(idx, sibling)
            sibling.parent = self.parent

    def insert_below(self, sibling: ArchimateFolder) -> None:
        if self.parent is not None:
            idx = self.parent.children.index(self)
            self.parent.children.insert(idx + 1, sibling)
            sibling.parent = self.parent

    def search(self, name: Optional[str] = None, type: Optional[str] = None, hash_val: Optional[int] = None, referenceId: Optional[IdentityPart] = None, standardName: Optional[str] = None) -> List[ArchimateFolder]:
        results = []
        queue = [self]
        
        while queue:
            current = queue.pop(0)
            
            match = True
            if name is not None and current.name != name:
                match = False
            if type is not None and current.type != type:
                match = False
            if hash_val is not None and current.__hash__() != hash_val:
                match = False
            if referenceId is not None and current.referenceId != referenceId:
                match = False
            if standardName is not None and current.standardName != standardName:
                match = False
            
            if match:
                results.append(current)
            
            queue.extend(current.children)
        
        return results

    def copy_tree(self) -> 'ArchimateFolder':
        return copy.deepcopy(self)

    def clear_tree(self) -> None:
        for child in self.children:
            child.parent = None
            child.clear_tree()
        self.children.clear()
