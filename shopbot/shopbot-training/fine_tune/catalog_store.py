# fine_tune/catalog_store.py
# Source: Book 3, Chapter 5 — A Smaller Model That Knows the Catalog
# Utility functions for fetching chunks from Qdrant during triplet construction.
# Used only by fine_tune/build_dataset.py — not part of the production pipeline.
#
# Standalone: qdrant_client comes from ../clients.py (this project's own, not
# ../shopbot-agent/infra/clients.py). point_to_chunk()/QDRANT_COLLECTION are
# duplicated from ../shopbot-agent/retrieval/hybrid.py rather than imported
# across projects — both are a handful of lines, not worth a cross-project dep.

import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clients import qdrant_client
from chunk_types import Chunk

QDRANT_COLLECTION = "zudyog_catalog"


def point_to_chunk(p) -> Chunk:
    """Convert a Qdrant ScoredPoint to a Chunk. Payload contains text + metadata."""
    return Chunk(
        id=p.payload.get("chunk_id", str(p.id)),
        text=p.payload["text"],
        metadata=p.payload,
    )


def get_chunk(chunk_id: str) -> Chunk:
    """
    Retrieve a single chunk from Qdrant by its string chunk_id.
    Raises ValueError if the chunk is not found.
    """
    results, _ = qdrant_client.scroll(
        collection_name=QDRANT_COLLECTION,
        scroll_filter={
            "must": [
                {"key": "chunk_id", "match": {"value": chunk_id}}
            ]
        },
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    if not results:
        raise ValueError(f"Chunk not found in Qdrant: {chunk_id}")
    return point_to_chunk(results[0])


def sample_hard_negative(product_id: str, exclude_chunk_type: str) -> Chunk | None:
    """
    Return a chunk from the same product as a different chunk_type.
    Hard negatives force the model to distinguish dimensions (identity vs. care vs. FAQ),
    not just products.
    Returns None if no such chunk exists (e.g. single-chunk products).
    """
    results, _ = qdrant_client.scroll(
        collection_name=QDRANT_COLLECTION,
        scroll_filter={
            "must": [
                {"key": "product_id", "match": {"value": product_id}}
            ],
            "must_not": [
                {"key": "chunk_type", "match": {"value": exclude_chunk_type}}
            ],
        },
        limit=20,
        with_payload=True,
        with_vectors=False,
    )
    if not results:
        return None
    return point_to_chunk(random.choice(results))
