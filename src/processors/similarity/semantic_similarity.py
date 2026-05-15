# src/processors/similarity/semantic_similarity.py
"""
Semantic Similarity Strategy module.
Executes strict branch-aware deduplication. Rejects superficial similarity.
"""

import re
import logging
import numpy as np
import pandas as pd

from .base_similarity import BaseSimilarityStrategy

logger = logging.getLogger(__name__)


class SemanticSimilarityStrategy(BaseSimilarityStrategy):
    """
    Branch-aware detection system.
    Isolates base supplier names from branch identifiers (e.g., '(up)', '(dl)').
    Enforces absolute base-name equivalence, overriding fuzzy semantic overlap.
    """

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2') -> None:
        self.model_name: str = model_name
        self._model = None

    def _get_model(self):
        """Lazy load the transformer model to protect main thread startup metrics."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Lazy loading Semantic Model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _extract_base_name(self, text: str) -> str:
        """
        Strips geographical or branch metadata enclosed in parentheses or brackets.
        'carrier (up)' -> 'carrier'
        """
        base = re.sub(r'\(.*?\)', '', text)
        base = re.sub(r'\[.*?\]', '', base)
        return base.strip()

    def flag_similar(self, df: pd.DataFrame, column: str, threshold: float) -> None:
        if not (0.5 <= threshold <= 1.0):
            raise ValueError(f"Threshold {threshold} invalid. Must be within [0.5, 1.0].")

        if column not in df.columns or df.empty:
            return

        unique_entities: np.ndarray = df[column].dropna().unique()
        if len(unique_entities) < 2:
            return

        model = self._get_model()
        from sentence_transformers import util

        embeddings = model.encode(list(unique_entities), batch_size=32, convert_to_tensor=True)
        cos_scores = util.cos_sim(embeddings, embeddings).cpu().numpy()

        np.fill_diagonal(cos_scores, 0)

        # High threshold enforced to filter initial noise before base-name validation
        indices = np.where(cos_scores >= threshold)

        flagged: set[tuple[str, str]] = set()
        for i, j in zip(indices[0], indices[1]):
            if i < j:
                # Force string casting to satisfy static type checkers and ensure scalar hashing
                e1 = str(unique_entities[i])
                e2 = str(unique_entities[j])

                pair = tuple(sorted([e1, e2]))

                if pair not in flagged:
                    base1 = self._extract_base_name(e1)
                    base2 = self._extract_base_name(e2)

                    # Strict Gate: Similar names (different base structure) are rejected.
                    # Only exact base matches with different branch identifiers are flagged.
                    if base1 != base2 or base1 == "":
                        continue

                    flagged.add(pair)
                    logger.warning(
                        "Branch duplicate %s detected: '%s' vs '%s' [semantic_score: %.3f]",
                        column, e1, e2, cos_scores[i, j]
                    )