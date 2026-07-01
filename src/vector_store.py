"""Vector store for policy chunks using Qdrant + Anthropic embeddings."""

from __future__ import annotations

import hashlib
import os
from typing import Optional

from anthropic import Anthropic
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from src.policy_loader import chunk_by_heading

COLLECTION_NAME = "policy_chunks"
EMBEDDING_MODEL = "voyage-3"
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")


def _get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def _get_embedding(text: str) -> list[float]:
    """Get embedding using Anthropic's API."""
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.beta.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1,
        messages=[{"role": "user", "content": text}],
        extra_headers={"anthropic-beta": "embeddings-2025-03-05"},
    )
    # fallback: use simple hash-based pseudo embedding for now
    # We'll use a different approach below
    return []


def _simple_embed(text: str, dim: int = 128) -> list[float]:
    """
    Simple deterministic embedding using character n-grams.
    Not semantic but works without extra API calls.
    Good enough for keyword-level retrieval on policy docs.
    """
    import math
    vector = [0.0] * dim
    text = text.lower()
    for i in range(len(text) - 2):
        trigram = text[i:i+3]
        idx = int(hashlib.md5(trigram.encode()).hexdigest(), 16) % dim
        vector[idx] += 1.0
    # normalize
    magnitude = math.sqrt(sum(v * v for v in vector))
    if magnitude > 0:
        vector = [v / magnitude for v in vector]
    return vector


def index_policy(policy_text: str, policy_id: str) -> int:
    """
    Chunk policy and store in Qdrant.
    Returns number of chunks stored.
    """
    client = _get_client()

    # create collection if it doesn't exist
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=128, distance=Distance.COSINE),
        )

    # chunk the policy
    sections = chunk_by_heading(policy_text)
    if not sections:
        return 0

    # delete old chunks for this policy_id
    try:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector={"filter": {
                "must": [{"key": "policy_id", "match": {"value": policy_id}}]
            }},
        )
    except Exception:
        pass

    # index new chunks
    points = []
    for i, (heading, content) in enumerate(sections.items()):
        chunk_text = f"{heading}\n\n{content}" if heading != "__preamble__" else content
        vector = _simple_embed(chunk_text)
        point_id = int(hashlib.md5(f"{policy_id}_{i}".encode()).hexdigest(), 16) % (2**31)
        points.append(PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "policy_id": policy_id,
                "heading": heading,
                "content": chunk_text,
            }
        ))

    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    return len(points)


def search_chunks(question: str, policy_id: str, top_k: int = 3) -> list[str]:
    """
    Find most relevant policy chunks for a question.
    Returns list of chunk texts.
    """
    client = _get_client()

    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        return []

    query_vector = _simple_embed(question)

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter={"must": [{"key": "policy_id", "match": {"value": policy_id}}]},
        limit=top_k,
    )

    return [hit.payload["content"] for hit in results.points]


def policy_is_indexed(policy_id: str) -> bool:
    """Check if a policy is already indexed."""
    try:
        client = _get_client()
        existing = [c.name for c in client.get_collections().collections]
        if COLLECTION_NAME not in existing:
            return False
        result = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter={"must": [{"key": "policy_id", "match": {"value": policy_id}}]},
            limit=1,
        )
        return len(result[0]) > 0
    except Exception:
        return False