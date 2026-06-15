from __future__ import annotations

from archeo.model.basemodel.ModelBase import ModelBase
from archeo.model.archimatemodel.ArchimateElement import ArchimateElement
from archeo.model.archimatemodel.ArchimateRelation import ArchimateRelation
from archeo.model.archimatemodel.ArchimateFolder import ArchimateFolder

from dataclasses import dataclass, field
from typing import Any, List, Optional, Self

# The ArchimateModel class inherits from ModelBase and represents a base class for Archimate models.
# It includes a constructor that initializes the name, formalism, version, customization, and description attributes
# with validation to ensure that name, formalism, and version are not empty or None.
# The constructor calls the constructor of ModelBase to perform the initialization and validation.
@dataclass
class ArchimateModel(ModelBase):
    name: str
    formalism: str
    version: str | None
    customization: str | None
    description: Optional[str] | None
    
    # Dictionary-like structures for storing Archimate model elements and relationships
    elements: dict[str, ArchimateElement] = field(default_factory=dict)
    relations: dict[str, ArchimateRelation] = field(default_factory=dict)
    
    # Folder trees for model element repository (organization tree) and view repository (view tree)
    organization_tree: ArchimateFolder | None = None
    view_tree: ArchimateFolder | None = None
    
    # The constructor of ArchimateElement calls the constructor of ModelBase to initialize the name, formalism, version, customization, and description attributes with validation.
    def __init__(self,
                pName: str,
                pFormalism: str,
                pVersion: Optional[str] = None,
                pCustomization: Optional[str] = None,
                pDescription: Optional[str] = None):

        super().__init__(pName,
                         pFormalism,
                         pVersion,
                         pCustomization,
                         pDescription)

        # Initialize storage structures
        self.elements: dict[str, ArchimateElement] = {}
        self.relations: dict[str, ArchimateRelation] = {}
        self.organization_tree: ArchimateFolder | None = None
        self.view_tree: ArchimateFolder | None = None

    def __hash__(self) -> int:
        try:
            # Validate that name, formalism, customization are not empty or None before calculating the hash
            if (self.name is None) or (self.name == "") \
                    or (self.formalism is None) or (self.formalism == "") \
                    or (self.customization is None) or (self.customization == ""):
                print(f"Hash calculation of ArchimateModel failed, with name={self.name}, formalism={self.formalism}, customization={self.customization}")

                raise ValueError("Invalid name, type, formalism, or customization for hashing")
            
            # The hash is based on the name, formalism, and customization attributes of the ArchimateModel
            return hash((self.name, self.formalism, self.customization))
            
        except ValueError as e:
            print(f"Hash calculation of ArchimateModel failed: {e}")

            # Return a default hash value in case of invalid attributes
            return 0

    # =========================================================================
    # Element Management Methods
    # =========================================================================

    def count_elements(self) -> int:
        """Return the total number of elements in the model."""
        return len(self.elements)

    def add_element(self, element: ArchimateElement) -> None:
        """Add an element to the model's elements dictionary using its name as key."""
        if element is not None and element.name:
            self.elements[element.name] = element

    def get_element(self, name: str) -> Optional[ArchimateElement]:
        """Retrieve an element by its name."""
        return self.elements.get(name, None)

    def remove_element(self, name: str) -> Optional[ArchimateElement]:
        """Remove and return an element by its name. Returns None if not found."""
        return self.elements.pop(name, None)

    def search_elements_by_name(self, name: str) -> List[ArchimateElement]:
        """Search for elements matching the given name (exact match)."""
        return [elem for elem in self.elements.values() if elem.name == name]

    def search_elements_by_name_contains(self, substring: str) -> List[ArchimateElement]:
        """Search for elements whose name contains the given substring."""
        return [elem for elem in self.elements.values() if substring in elem.name]

    def search_elements_by_type(self, type_name: str) -> List[ArchimateElement]:
        """Search for elements matching the given type name."""
        return [elem for elem in self.elements.values() if hasattr(elem, 'type') and elem.type == type_name]

    def search_elements_by_hash(self, hash_value: int) -> List[ArchimateElement]:
        """Search for elements matching the given hash value."""
        return [elem for elem in self.elements.values() if hash(elem) == hash_value]

    def copy_elements(self) -> dict[str, ArchimateElement]:
        """Return a shallow copy of the elements dictionary."""
        return dict(self.elements)

    def clear_elements(self) -> None:
        """Remove all elements from the elements dictionary."""
        self.elements.clear()

    # =========================================================================
    # Relation Management Methods
    # =========================================================================

    def count_relations(self) -> int:
        """Return the total number of relations in the model."""
        return len(self.relations)

    def add_relation(self, relation: ArchimateRelation) -> None:
        """Add a relation to the model's relations dictionary using its name as key."""
        if relation is not None and relation.name:
            self.relations[relation.name] = relation

    def get_relation(self, name: str) -> Optional[ArchimateRelation]:
        """Retrieve a relation by its name."""
        return self.relations.get(name, None)

    def remove_relation(self, name: str) -> Optional[ArchimateRelation]:
        """Remove and return a relation by its name. Returns None if not found."""
        return self.relations.pop(name, None)

    def search_relations_by_name(self, name: str) -> List[ArchimateRelation]:
        """Search for relations matching the given name (exact match)."""
        return [rel for rel in self.relations.values() if rel.name == name]

    def search_relations_by_name_contains(self, substring: str) -> List[ArchimateRelation]:
        """Search for relations whose name contains the given substring."""
        return [rel for rel in self.relations.values() if substring in rel.name]

    def search_relations_by_type(self, type_name: str) -> List[ArchimateRelation]:
        """Search for relations matching the given type name."""
        return [rel for rel in self.relations.values() if hasattr(rel, 'type') and rel.type == type_name]

    def search_relations_by_hash(self, hash_value: int) -> List[ArchimateRelation]:
        """Search for relations matching the given hash value."""
        return [rel for rel in self.relations.values() if hash(rel) == hash_value]

    def copy_relations(self) -> dict[str, ArchimateRelation]:
        """Return a shallow copy of the relations dictionary."""
        return dict(self.relations)

    def clear_relations(self) -> None:
        """Remove all relations from the relations dictionary."""
        self.relations.clear()

    # =========================================================================
    # Model-Wide Utility Methods
    # =========================================================================

    def clear_all(self) -> None:
        """Clear both elements and relations dictionaries."""
        self.clear_elements()
        self.clear_relations()

    def copy_all(self) -> tuple[dict[str, ArchimateElement], dict[str, ArchimateRelation]]:
        """Return shallow copies of both elements and relations dictionaries."""
        return self.copy_elements(), self.copy_relations()

    # =========================================================================
    # Organization Tree Management Methods
    # =========================================================================

    def get_organization_tree(self) -> Optional[ArchimateFolder]:
        return self.organization_tree

    def set_organization_tree(self, tree: Optional[ArchimateFolder]) -> None:
        self.organization_tree = tree

    def count_organization_nodes(self) -> int:
        if not self.organization_tree:
            return 0
        return self._count_folder_nodes(self.organization_tree)

    def add_to_organization_tree(self, folder: ArchimateFolder) -> None:
        if not self.organization_tree:
            self.organization_tree = folder
        elif hasattr(self.organization_tree, 'children'):
            self.organization_tree.children.append(folder)

    def remove_organization_tree(self) -> None:
        self.organization_tree = None

    def search_organization_by_name(self, name: str) -> List[ArchimateFolder]:
        if not self.organization_tree:
            return []
        return self._search_folder_by_name(self.organization_tree, name)

    def search_organization_by_type(self, type_name: str) -> List[ArchimateFolder]:
        if not self.organization_tree:
            return []
        return self._search_folder_by_type(self.organization_tree, type_name)

    def search_organization_by_hash(self, hash_value: int) -> List[ArchimateFolder]:
        if not self.organization_tree:
            return []
        return self._search_folder_by_hash(self.organization_tree, hash_value)

    def copy_organization_tree(self) -> Optional[ArchimateFolder]:
        import copy
        return copy.copy(self.organization_tree) if self.organization_tree else None

    def clear_organization_tree(self) -> None:
        self.organization_tree = None

    # =========================================================================
    # View Tree Management Methods
    # =========================================================================

    def get_view_tree(self) -> Optional[ArchimateFolder]:
        return self.view_tree

    def set_view_tree(self, tree: Optional[ArchimateFolder]) -> None:
        self.view_tree = tree

    def count_view_nodes(self) -> int:
        if not self.view_tree:
            return 0
        return self._count_folder_nodes(self.view_tree)

    def add_to_view_tree(self, folder: ArchimateFolder) -> None:
        if not self.view_tree:
            self.view_tree = folder
        elif hasattr(self.view_tree, 'children'):
            self.view_tree.children.append(folder)

    def remove_view_tree(self) -> None:
        self.view_tree = None

    def search_view_by_name(self, name: str) -> List[ArchimateFolder]:
        if not self.view_tree:
            return []
        return self._search_folder_by_name(self.view_tree, name)

    def search_view_by_type(self, type_name: str) -> List[ArchimateFolder]:
        if not self.view_tree:
            return []
        return self._search_folder_by_type(self.view_tree, type_name)

    def search_view_by_hash(self, hash_value: int) -> List[ArchimateFolder]:
        if not self.view_tree:
            return []
        return self._search_folder_by_hash(self.view_tree, hash_value)

    def copy_view_tree(self) -> Optional[ArchimateFolder]:
        import copy
        return copy.copy(self.view_tree) if self.view_tree else None

    def clear_view_tree(self) -> None:
        self.view_tree = None

    # =========================================================================
    # Private Tree Traversal Helpers
    # =========================================================================

    def _count_folder_nodes(self, folder: ArchimateFolder) -> int:
        count = 1
        if hasattr(folder, 'children') and folder.children:
            for child in folder.children:
                count += self._count_folder_nodes(child)
        return count

    def _search_folder_by_name(self, folder: ArchimateFolder, name: str) -> List[ArchimateFolder]:
        results = []
        if getattr(folder, 'name', None) == name:
            results.append(folder)
        if hasattr(folder, 'children') and folder.children:
            for child in folder.children:
                results.extend(self._search_folder_by_name(child, name))
        return results

    def _search_folder_by_type(self, folder: ArchimateFolder, type_name: str) -> List[ArchimateFolder]:
        results = []
        if getattr(folder, 'type', None) == type_name:
            results.append(folder)
        if hasattr(folder, 'children') and folder.children:
            for child in folder.children:
                results.extend(self._search_folder_by_type(child, type_name))
        return results

    def _search_folder_by_hash(self, folder: ArchimateFolder, hash_value: int) -> List[ArchimateFolder]:
        results = []
        if hash(folder) == hash_value:
            results.append(folder)
        if hasattr(folder, 'children') and folder.children:
            for child in folder.children:
                results.extend(self._search_folder_by_hash(child, hash_value))
        return results
