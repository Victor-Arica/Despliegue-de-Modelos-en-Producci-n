"""Minimal RAG engine backed by Gemini and numpy."""

from __future__ import annotations

import glob
import os
import threading

import numpy as np
from google import genai
from google.genai import types

DOCS_DIR = os.getenv("DOCS_DIR", "docs")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
TOP_K = int(os.getenv("TOP_K", "4"))
CHUNK_WORDS = int(os.getenv("CHUNK_WORDS", "150"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "30"))


def _get_api_key() -> str | None:
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


class RagEngine:
    def __init__(self) -> None:
        self._client: genai.Client | None = None
        self._chunks: list[str] = []
        self._matrix: np.ndarray | None = None
        self._lock = threading.Lock()
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def num_chunks(self) -> int:
        return len(self._chunks)

    def _client_or_raise(self) -> genai.Client:
        if self._client is None:
            key = _get_api_key()
            if not key:
                raise RuntimeError(
                    "No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY at runtime."
                )
            self._client = genai.Client(api_key=key)
        return self._client

    @staticmethod
    def _chunk(text: str) -> list[str]:
        words = text.split()
        if not words:
            return []
        step = max(1, CHUNK_WORDS - CHUNK_OVERLAP)
        chunks: list[str] = []
        for start in range(0, len(words), step):
            piece = " ".join(words[start : start + CHUNK_WORDS]).strip()
            if piece:
                chunks.append(piece)
            if start + CHUNK_WORDS >= len(words):
                break
        return chunks

    def _load_chunks(self) -> list[str]:
        chunks: list[str] = []
        for path in sorted(glob.glob(os.path.join(DOCS_DIR, "*.txt"))):
            with open(path, encoding="utf-8") as file_handle:
                chunks.extend(self._chunk(file_handle.read()))
        return chunks

    def _embed(self, texts: list[str], task_type: str) -> np.ndarray:
        client = self._client_or_raise()
        response = client.models.embed_content(
            model=EMBED_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBED_DIM,
            ),
        )
        vectors = np.array(
            [embedding.values for embedding in response.embeddings], dtype=np.float32
        )
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms

    def build(self) -> None:
        with self._lock:
            if self._ready:
                return
            chunks = self._load_chunks()
            if not chunks:
                raise RuntimeError(f"No .txt documents found in '{DOCS_DIR}/'.")
            self._matrix = self._embed(chunks, task_type="RETRIEVAL_DOCUMENT")
            self._chunks = chunks
            self._ready = True

    def _retrieve(self, question: str) -> list[str]:
        if self._matrix is None:
            raise RuntimeError("Index is not ready.")
        query_vector = self._embed([question], task_type="RETRIEVAL_QUERY")[0]
        scores = self._matrix @ query_vector
        top_indexes = np.argsort(scores)[::-1][:TOP_K]
        return [self._chunks[index] for index in top_indexes]

    def ask(self, question: str) -> str:
        if not self._ready:
            self.build()
        context = "\n\n---\n\n".join(self._retrieve(question))
        system_instruction = (
            "You are a precise assistant. Answer using only the provided context. "
            "If the answer is not in the context, say you do not have enough information. "
            "Reply in the same language as the question and keep it concise."
        )
        prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        client = self._client_or_raise()
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            ),
        )
        return (response.text or "").strip()


engine = RagEngine()
