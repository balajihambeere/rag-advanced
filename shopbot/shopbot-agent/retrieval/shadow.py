# retrieval/shadow.py
# Source: Book 2, Chapter 2 — Move Without Breaking Things
# Shadow read: all queries hit ChromaDB (primary), then the same query is sent
# to Qdrant asynchronously and both result sets are compared.
# Used during the migration period. After cut-over, this file is retired.
#
# The comparison log records per-query top-k agreement:
#   "agreement_at_k": 3  → identical top-3 from both stores (target: 94%+)

import time
import os
import uuid
import asyncio
import chromadb
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from dotenv import load_dotenv

from infra.comparison_log import append as comparison_log_append
from infra.types import Chunk

load_dotenv()

_NS = uuid.UUID("00000000-0000-0000-0000-000000000001")
CHROMA_COLLECTION = "zudyog_products"
QDRANT_COLLECTION = "zudyog_catalog"
SIMILARITY_THRESHOLD = 0.75  # Book 1 threshold — still enforced on the ChromaDB path
K = 3

_embeddings = OpenAIEmbeddings()
_chroma_client = chromadb.PersistentClient(path="./chroma_db")
_chroma_col = _chroma_client.get_or_create_collection(
    name=CHROMA_COLLECTION,
    metadata={"hnsw:space": "cosine"},
)
_qdrant = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
)


def _chroma_retrieve(query_vec: list[float], k: int) -> list[Chunk]:
    results = _chroma_col.query(
        query_embeddings=[query_vec],
        n_results=k,
        include=["documents", "distances", "metadatas"],
    )
    chunks = []
    for i, doc in enumerate(results["documents"][0]):
        similarity = 1 - results["distances"][0][i]
        if similarity >= SIMILARITY_THRESHOLD:
            meta = results["metadatas"][0][i]
            chunks.append(Chunk(
                id=meta.get("product_id", "") + "_" + meta.get("chunk_type", ""),
                text=doc,
                metadata=meta,
            ))
    return chunks


async def _shadow_compare(
    query: str,
    query_vec: list[float],
    chroma_results: list[Chunk],
    k: int,
) -> None:
    """Compare ChromaDB top-k with Qdrant dense top-k; log the agreement."""
    qdrant_results = _qdrant.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=("dense", query_vec),
        limit=k,
    )
    chroma_ids = {c.id for c in chroma_results}
    # Use the stored chunk_id in payload so comparison is apples-to-apples
    qdrant_ids = {p.payload.get("chunk_id", str(p.id)) for p in qdrant_results}

    comparison_log_append({
        "ts":             time.time(),
        "query":          query,
        "chroma_ids":     list(chroma_ids),
        "qdrant_ids":     list(qdrant_ids),
        "agreement_at_k": len(chroma_ids & qdrant_ids),
        "k":              k,
    })


def retrieve_with_shadow(query: str, k: int = K) -> list[Chunk]:
    """
    Primary read from ChromaDB. Shadow-fires the same query to Qdrant
    in the background for comparison logging. Returns ChromaDB results.
    """
    query_vec = _embeddings.embed_query(query)
    chroma_results = _chroma_retrieve(query_vec, k)

    # Fire-and-forget shadow comparison
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_shadow_compare(query, query_vec, chroma_results, k))
        else:
            loop.run_until_complete(_shadow_compare(query, query_vec, chroma_results, k))
    except RuntimeError:
        pass  # Sync context — skip shadow

    return chroma_results
