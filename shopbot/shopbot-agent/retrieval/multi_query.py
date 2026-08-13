# retrieval/multi_query.py
# Source: Book 2, Chapter 5 — Two Halves of One Question
# Multi-query retrieval: splits two-intent queries BEFORE retrieval runs.
# Single-intent queries pass straight through. Two-intent queries retrieve
# each half separately via the full hybrid+rerank+memory pipeline, then merge
# with RRF. The merged top-3 go to the model.
#
# This closes the "festive and warm" cliffhanger from Book 1 Chapter 10.

from infra.types import Chunk
from retrieval.decompose import decompose
from retrieval.hybrid import retrieve_hybrid, reciprocal_rank_fusion
from retrieval.rerank import rerank


def retrieve_multi(
    query: str,
    session=None,
) -> tuple[list[Chunk], list[str]]:
    """
    Decompose → per-sub-query hybrid+rerank → RRF merge → top 3.

    Returns (chunks, sub_queries).
    sub_queries has len==1 for single-intent, len==2 for two-intent.
    The prompt builder uses sub_queries to decide whether to add the
    multi-intent instruction note to the model.
    """
    sub_queries = decompose(query, session=session)

    if len(sub_queries) == 1:
        # Single-intent — standard hybrid + rerank path
        chunks = _retrieve_one(sub_queries[0], session)
        return chunks, sub_queries

    # Two-intent — retrieve each sub-query separately, merge
    ranked_lists = [_retrieve_one(sq, session) for sq in sub_queries]
    fused = reciprocal_rank_fusion(*ranked_lists, k=60)
    return [chunk for chunk, _ in fused[:3]], sub_queries


def _retrieve_one(sub_query: str, session) -> list[Chunk]:
    """Run one sub-query through the memory-aware retrieval path."""
    if session is not None:
        from retrieval.memory_aware import retrieve_for_prompt_with_memory
        return retrieve_for_prompt_with_memory(sub_query, session)
    candidates = retrieve_hybrid(sub_query, top_n=20)
    return rerank(sub_query, candidates, top_k=3)
