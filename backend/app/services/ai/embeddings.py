"""
Embedding generation for the Policy RAG pipeline.

Uses scikit-learn's TF-IDF vectorizer rather than a downloaded neural
embedding model. This keeps the whole system runnable fully offline/
air-gapped (no HF Hub / model registry access required) while still
giving semantically useful similarity for short HR policy chunks.

Swap-out point: replace `TfidfEmbedder` with a call to any embeddings
API (OpenAI, Voyage, Anthropic partners, etc.) by implementing the
same `fit`, `embed`, `similarity` interface.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@dataclass
class EmbeddingIndex:
    vectorizer: TfidfVectorizer
    matrix: np.ndarray  # sparse matrix, shape (n_chunks, n_features)


class TfidfEmbedder:
    """Fits once over the full chunk corpus; query vectors are
    transformed against the fitted vocabulary."""

    def __init__(self):
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None

    def fit(self, chunk_texts: list[str]) -> None:
        normalized = [normalize(t) for t in chunk_texts]
        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            stop_words="english",
        )
        self._matrix = self._vectorizer.fit_transform(normalized)

    @property
    def is_fitted(self) -> bool:
        return self._vectorizer is not None

    def embed_query(self, text: str):
        if not self.is_fitted:
            raise RuntimeError("Embedder not fitted yet — call fit() with the policy corpus first.")
        return self._vectorizer.transform([normalize(text)])

    def top_k(self, query: str, k: int) -> list[tuple[int, float]]:
        """Returns [(chunk_index, similarity_score), ...] sorted desc."""
        if not self.is_fitted:
            return []
        q_vec = self.embed_query(query)
        sims = cosine_similarity(q_vec, self._matrix)[0]
        ranked = np.argsort(-sims)[:k]
        return [(int(i), float(sims[i])) for i in ranked]
