"""
In-memory vector store for HR policy chunks.

Rebuilds from the `hr_policies` table. For a larger deployment this
same interface could be backed by Chroma/FAISS/Qdrant instead — the
rest of the RAG pipeline only depends on `PolicyVectorStore.search()`.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.hrms import HRPolicy
from app.services.ai.embeddings import TfidfEmbedder

CHUNK_MAX_CHARS = 700
CHUNK_OVERLAP_CHARS = 100


@dataclass
class PolicyChunk:
    policy_id: int
    title: str
    category: str
    filename: str | None
    chunk_index: int
    text: str


def chunk_policy_content(content: str) -> list[str]:
    """Splits on paragraph/section boundaries first, then hard-wraps
    any paragraph still longer than CHUNK_MAX_CHARS, with overlap so
    retrieval doesn't lose context at chunk edges."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= CHUNK_MAX_CHARS:
            chunks.append(para)
            continue
        start = 0
        while start < len(para):
            end = start + CHUNK_MAX_CHARS
            chunks.append(para[start:end])
            start = end - CHUNK_OVERLAP_CHARS
    return chunks


class PolicyVectorStore:
    """Process-wide singleton, rebuilt whenever policies change."""

    _instance: "PolicyVectorStore | None" = None
    _lock = threading.Lock()

    def __init__(self):
        self.chunks: list[PolicyChunk] = []
        self.embedder = TfidfEmbedder()
        self._built = False

    @classmethod
    def instance(cls) -> "PolicyVectorStore":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def build(self, db: Session) -> None:
        policies = db.query(HRPolicy).all()
        chunks: list[PolicyChunk] = []
        for policy in policies:
            for idx, chunk_text in enumerate(chunk_policy_content(policy.content)):
                chunks.append(
                    PolicyChunk(
                        policy_id=policy.id,
                        title=policy.title,
                        category=policy.category,
                        filename=policy.filename,
                        chunk_index=idx,
                        text=chunk_text,
                    )
                )
        self.chunks = chunks
        if chunks:
            self.embedder.fit([c.text for c in chunks])
        self._built = True

    def ensure_built(self, db: Session) -> None:
        if not self._built:
            self.build(db)

    def search(self, query: str, k: int) -> list[tuple[PolicyChunk, float]]:
        if not self.chunks:
            return []
        results = self.embedder.top_k(query, k)
        return [(self.chunks[i], score) for i, score in results]
