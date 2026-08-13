# retrieval/hybrid.py
# Source: Book 2, Chapter 3 — Two Signals Are Better Than One
# Hybrid search: dense (semantic) + BM25 (lexical), fused by Reciprocal Rank Fusion.
# Replaces the Book 1 single-signal dense retriever for all customer-facing queries.
#
# Why RRF: dense and BM25 produce scores on incompatible scales. RRF normalises
# both to rank positions, then sums the reciprocal ranks. A chunk that ranks first
# in both lists scores higher than one that ranks first in only one. The 60
# smoothing constant comes from Cormack & Clarke (2009) — empirically stable.

from collections import defaultdict
from infra.clients import embed, bm25, qdrant_client
from infra.types import Chunk
from qdrant_client import models

QDRANT_COLLECTION = "zudyog_catalog"
RRF_K = 60  # smoothing constant — see Chapter 3 prose for calibration guidance


def point_to_chunk(p) -> Chunk:
    """Convert a Qdrant ScoredPoint to a Chunk. Payload contains text + metadata."""
    return Chunk(
        id=p.payload.get("chunk_id", str(p.id)),
        text=p.payload["text"],
        metadata=p.payload,
    )


def reciprocal_rank_fusion(
    *ranked_lists: list[Chunk],
    k: int = RRF_K,
) -> list[tuple[Chunk, float]]:
    """
    Fuse N ranked lists into one ordered list using Reciprocal Rank Fusion.
    Returns (chunk, rrf_score) pairs sorted by score descending.
    """
    scores: dict[str, float] = defaultdict(float)
    chunk_by_id: dict[str, Chunk] = {}
    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            scores[chunk.id] += 1.0 / (k + rank)
            chunk_by_id[chunk.id] = chunk
    fused = sorted(
        ((chunk_by_id[cid], s) for cid, s in scores.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    return fused


def retrieve_hybrid(query: str, top_n: int = 10) -> list[Chunk]:
    """
    Dense + BM25 hybrid retrieval from Qdrant, fused with RRF.
    Returns top_n chunks. top_n=20 feeds the reranker in Chapter 4.
    top_n=10 (default) for direct use without reranking.
    """
    dense_vec = embed(query)
    sparse_vec = next(iter(bm25.embed([query])))

    dense_hits = qdrant_client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=("dense", dense_vec),
        limit=20,
    )
    sparse_hits = qdrant_client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=models.NamedSparseVector(
            name="bm25",
            vector=models.SparseVector(
                indices=sparse_vec.indices.tolist(),
                values=sparse_vec.values.tolist(),
            ),
        ),
        limit=20,
    )

    dense_chunks  = [point_to_chunk(p) for p in dense_hits]
    sparse_chunks = [point_to_chunk(p) for p in sparse_hits]

    fused = reciprocal_rank_fusion(dense_chunks, sparse_chunks)
    return [chunk for chunk, _ in fused[:top_n]]
