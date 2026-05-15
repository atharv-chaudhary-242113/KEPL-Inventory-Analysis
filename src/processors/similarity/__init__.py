# src/processors/similarity/__init__.py
"""
Similarity Detection Strategies module.

Exposes concrete algorithms for identifying duplicate nomenclatures.
Adheres to the Strategy Pattern to satisfy the Open/Closed Principle.
"""

from .base_similarity import BaseSimilarityStrategy
from .tfidf_similarity import TfidfSimilarityStrategy
from .semantic_similarity import SemanticSimilarityStrategy

__all__ = [
    "BaseSimilarityStrategy",
    "TfidfSimilarityStrategy",
    "SemanticSimilarityStrategy"
]