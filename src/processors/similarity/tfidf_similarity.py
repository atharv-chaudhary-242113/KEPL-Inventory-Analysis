# src/processors/similarity/tfidf_similarity.py
"""
TF-IDF Similarity Strategy module.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .base_similarity import BaseSimilarityStrategy

logger = logging.getLogger(__name__)


class TfidfSimilarityStrategy(BaseSimilarityStrategy):
    """
    Legacy statistical similarity approach utilizing character n-grams and cosine distance.
    """

    def flag_similar(self, df: pd.DataFrame, column: str, threshold: float) -> None:
        if not (0.5 <= threshold <= 1.0):
            raise ValueError(f"Threshold {threshold} invalid. Must be within [0.5, 1.0].")

        if column not in df.columns or df.empty:
            return

        unique_entities: np.ndarray = df[column].dropna().unique()
        if len(unique_entities) < 2:
            return

        vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 4))
        tfidf_matrix = vectorizer.fit_transform(unique_entities)
        sim_matrix: np.ndarray = cosine_similarity(tfidf_matrix)

        np.fill_diagonal(sim_matrix, 0)
        indices = np.where(sim_matrix >= threshold)

        flagged: set[tuple[str, str]] = set()
        for i, j in zip(indices[0], indices[1]):
            if i < j:
                e1, e2 = unique_entities[i], unique_entities[j]
                pair = tuple(sorted([e1, e2]))
                if pair not in flagged:
                    flagged.add(pair)
                    logger.warning(
                        "Similar %s detected: '%s' vs '%s' [score: %.3f]",
                        column, e1, e2, sim_matrix[i, j]
                    )