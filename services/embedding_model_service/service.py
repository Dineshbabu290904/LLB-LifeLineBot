"""
Embedding Model Service - Business logic for generating text embeddings.
Uses sentence-transformers all-MiniLM-L6-v2 (384-dimensional) locally.
"""
import numpy as np
from typing import List
from functools import lru_cache
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load and cache the sentence-transformer model (lazy singleton)."""
    return SentenceTransformer(MODEL_NAME)


def normalize_vector(vector: np.ndarray) -> np.ndarray:
    """L2-normalize a vector so cosine similarity equals dot product."""
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm


def embed_single(text: str) -> List[float]:
    """Generate a normalized embedding for a single text string."""
    model = get_model()
    embedding = model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
    return embedding.tolist()


def embed_batch(texts: List[str]) -> List[List[float]]:
    """Generate normalized embeddings for a list of texts (batched for efficiency)."""
    model = get_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        batch_size=32,
        show_progress_bar=False,
    )
    return [emb.tolist() for emb in embeddings]


def get_model_info() -> dict:
    """Return metadata about the loaded embedding model."""
    return {
        "model_name": MODEL_NAME,
        "dimensions": EMBEDDING_DIM,
        "normalize": True,
        "similarity_metric": "cosine (dot product on normalized vectors)",
    }
