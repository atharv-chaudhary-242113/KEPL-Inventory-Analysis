# src/processors/similarity/tfidf_similarity.py
"""
TF-IDF Similarity Strategy module.
"""

import logging
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import gc

from .base_similarity import BaseSimilarityStrategy

logger = logging.getLogger(__name__)


class TfidfSimilarityStrategy(BaseSimilarityStrategy):
    """
    Batched statistical similarity approach utilizing character n-grams and sparse cosine distance.
    """

    def compute_similarity_in_chunks(self, tfidf_matrix, unique_entities: np.ndarray, threshold: float,
                                     batch_size: int = 1000) -> set:
        num_rows = tfidf_matrix.shape[0]
        flagged: set[tuple[str, str]] = set()

        for start_idx in range(0, num_rows, batch_size):
            end_idx = min(start_idx + batch_size, num_rows)
            chunk = tfidf_matrix[start_idx:end_idx]

            similarity_chunk = cosine_similarity(chunk, tfidf_matrix, dense_output=False)

            # Extract upper triangle coordinates that exceed threshold
            coo = similarity_chunk.tocoo()
            for i_chunk, j, v in zip(coo.row, coo.col, coo.data):
                i = start_idx + i_chunk
                if i < j and v >= threshold:
                    e1, e2 = str(unique_entities[i]), str(unique_entities[j])
                    pair = tuple(sorted([e1, e2]))
                    if pair not in flagged:
                        flagged.add(pair)
                        logger.warning(
                            "Similar entity detected: '%s' vs '%s' [score: %.3f]",
                            e1, e2, v
                        )

            del chunk
            del similarity_chunk
            gc.collect()

        return flagged

    def flag_similar(self, df: pd.DataFrame, column: str, threshold: float, batch_size: int = 1000) -> None:
        if not (0.5 <= threshold <= 1.0):
            raise ValueError(f"Threshold {threshold} invalid. Must be within [0.5, 1.0].")

        if column not in df.columns or df.empty:
            return

        unique_entities: np.ndarray = df[column].dropna().unique()
        if len(unique_entities) < 2:
            return

        vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 4))
        tfidf_matrix = vectorizer.fit_transform(unique_entities)

        self.compute_similarity_in_chunks(tfidf_matrix, unique_entities, threshold, batch_size)