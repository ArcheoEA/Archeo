# comparison/differ.py

"""
Engine for comparing two ArchiMate models.
Provides fine-grained element-wise and structural comparison.
"""

from __future__ import annotations
import logging
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
import difflib

from ..core.model_store import ArchiModel
from ..core.element import ArchiElement

logger = logging.getLogger(__name__)


@dataclass
class ElementDifference:
    """Difference between two elements."""
    type: str  # "added", "removed", "modified"
    element_a_id: Optional[str]
    element_b_id: Optional[str]
    changes: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if self.changes is None:
            self.changes = []


@dataclass
class ComparisonResult:
    """Full result of comparing two ArchiModels."""
    model_a_name: str
    model_b_name: str
    element_diffs: List[ElementDifference]
    relationship_diffs: List[str]  # Simple representation for now
    structural_diffs: Dict[str, Any]
    match_score: float = 0.0


class ModelDiffer:
    """
    Compare two ArchiModels with fine-grained difference reporting.
    
    Features:
      - Structural diffs (folder trees)
      - Element comparison by ID or name+type
      - Relationship mapping
    """
    
    def __init__(self, match_threshold: float = 0.7):
        self._threshold = match_threshold

    def compare(self, model_a: ArchiModel, model_b: ArchiModel) -> ComparisonResult:
        """Compare two models and return detailed differences."""
        
        # Match elements by ID first (identity), then fallback to name+type
        matched_pairs, unmatched_a, unmatched_b = self._match_elements(model_a, model_b)
        
        diffs = []
        for el_a in matched_pairs.keys():
            diff = self._compare_element_pair(el_a, matched_pairs[el_a])
            if diff.changes:
                diffs.append(diff)
        
        # Add unmatched as added/removed
        for eid in unmatched_a:
            diffs.append(ElementDifference(
                type="removed", element_a_id=eid, element_b_id=None
            ))
        
        for eid in unmatched_b:
            diffs.append(ElementDifference(
                type="added", element_a_id=None, element_b_id=eid
            ))
        
        # Compute match score (heuristic)
        total_elements = len(model_a.elements) + len(model_b.elements)
        matched_count = len(matched_pairs) * 2
        unmatched_count = len(unmatched_a) + len(unmatched_b)
        
        if total_elements == 0:
            score = 1.0
        else:
            score = (matched_count / total_elements) * 0.7 + \
                    ((unmatched_count == 0) and 1.0 or 0.0)
        
        return ComparisonResult(
            model_a_name=model_a.name,
            model_b_name=model_b.name,
            element_diffs=diffs,
            relationship_diffs=[],
            structural_diffs={
                "folder_count_a": len(model_a.folders),
                "folder_count_b": len(model_b.folders)
            },
            match_score=round(score, 3)
        )

    def _match_elements(
        self, 
        model_a: ArchiModel, 
        model_b: ArchiModel
    ) -> Tuple[
        Dict[str, ArchiElement], List[str], List[str]
    ]:
        """Match elements between models. Returns (matches, unmatched_a, unmatched_b)."""
        
        matches = {}
        unmatched_a = []
        matched_ids_in_b = set()
        
        # Fast path: ID-based matching
        for eid_a in model_a.elements:
            if eid_a in model_b.elements:
                matches[eid_a] = model_b.elements[eid_a]
                matched_ids_in_b.add(eid_a)
            else:
                unmatched_a.append(eid_a)
        
        # Fallback: name+type heuristic matching
        for eid_a in unmatched_a[:]:
            el_a = model_a.elements[eid_a]
            best_match_score = 0
            best_b_id = None
            
            for eid_b, el_b in model_b.elements.items():
                if eid_b in matched_ids_in_b:
                    continue
                
                score = self._element_similarity(el_a, el_b)
                if score > best_match_score and score >= self._threshold:
                    best_match_score = score
                    best_b_id = eid_b
            
            if best_b_id is not None:
                matches[eid_a] = model_b.elements[best_b_id]
                matched_ids_in_b.add(best_b_id)
                unmatched_a.remove(eid_a)
        
        unmatched_b = [
            eid for eid in model_b.elements 
            if eid not in matched_ids_in_b
        ]
        
        return matches, unmatched_a, unmatched_b

    def _element_similarity(self, el_a: ArchiElement, el_b: ArchiElement) -> float:
        """Compute similarity score between two elements (0–1)."""
        
        # Same type contributes 0.4
        type_score = 0.4 if type(el_a) == type(el_b) else 0
        
        # Name similarity (Levenshtein-style)
        name_similarity = difflib.SequenceMatcher(
            None, el_a.name.lower(), el_b.name.lower()
        ).ratio() * 0.5
        
        # Folder path match
        folder_score = 0.1 if (getattr(el_a, 'folder_id', None) == getattr(el_b, 'folder_id', None)) else 0
        
        return type_score + name_similarity + folder_score

    def _compare_element_pair(self, el_a: ArchiElement, el_b: ArchiElement) -> ElementDifference:
        """Compare two matched elements."""
        
        changes = []
        fields_to_check = ["name", "description", "folder_id"]
        
        for field in fields_to_check:
            val_a = getattr(el_a, field)
            val_b = getattr(el_b, field)
            
            if str(val_a) != str(val_b):
                changes.append({
                    "field": field,
                    "old": val_a,
                    "new": val_b
                })
        
        # Special handling for v4.0-only fields when comparing across versions
        if hasattr(el_a, "is_abstract") and hasattr(el_b, "is_abstract"):
            if el_a.is_abstract != el_b.is_abstract:
                changes.append({
                    "field": "isAbstract",
                    "old": el_a.is_abstract,
                    "new": el_b.is_abstract
                })
        
        return ElementDifference(
            type="modified" if changes else "identical",
            element_a_id=el_a.id,
            element_b_id=el_b.id,
            changes=changes
        )
