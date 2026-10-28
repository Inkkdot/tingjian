"""Real embedding provider (fastembed ONNX, bge-small-zh-v1.5)."""
from __future__ import annotations

import threading
from typing import Iterable

import numpy as np

MODEL_NAME = "BAAI/bge-small-zh-v1.5"
MODEL_LABEL = "bge-small-zh-v1.5"
DIMENSION = 512
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


class Embedder:
    def __init__(self, dimension: int = DIMENSION):
        self.dimension = dimension
        self._model = None
        self._lock = threading.Lock()
        self._error: str | None = None
        self._tried = False

    @property
    def error(self) -> str | None:
        return self._error

    def available(self) -> bool:
        self._load()
        return self._model is not None

    def _load(self) -> None:
        with self._lock:
            if self._tried:
                return
            self._tried = True
            try:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=MODEL_NAME)
            except Exception as exc:  # download/runtime failure stays honest
                self._error = f"{type(exc).__name__}: {exc}"[:400]
                self._model = None

    def _embed(self, texts: list[str]) -> list[list[float]]:
        self._load()
        if self._model is None:
            raise RuntimeError(self._error or "embedding model unavailable")
        vectors = list(self._model.embed(texts, batch_size=16))
        out = []
        for vec in vectors:
            arr = np.asarray(vec, dtype=np.float32)
            norm = float(np.linalg.norm(arr))
            if norm > 0:
                arr = arr / norm
            out.append(arr.tolist())
        return out

    def embed_passages(self, texts: Iterable[str]) -> list[list[float]]:
        items = list(texts)
        return self._embed(items) if items else []

    def embed_query(self, text: str) -> list[float]:
        return self._embed([QUERY_PREFIX + text])[0]
