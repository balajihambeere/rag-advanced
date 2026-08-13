# retrieval/memory_aware.py
# Source: Book 2, Chapter 6 — ShopBot Finally Remembers; Chapter 9 (moved to HTTP)
# Memory-aware retrieval: applies an active-SKU bonus on top of cross-encoder scores
# so the reranker slightly favours products already in the conversation context.
#
# Also applies the Chapter 8 cross-encoder confidence floor: if no candidate
# scores above 0.55, the retriever returns [] and the API routes to support.
# This replaces Book 1's 0.75 cosine-similarity threshold, which was calibrated
# against a 5-product catalog; the floor is calibrated against the labeled dataset.
#
# Cross-encoder scores come from the standalone ../shopbot-rerank/ service —
# this process has no in-process CrossEncoder (see retrieval/rerank_client.py).

from infra.types import Chunk
from retrieval.hybrid import retrieve_hybrid
from retrieval.rerank_client import rerank_scores_remote

ACTIVE_SKU_BOOST      = 0.05  # tie-breaker; not enough to override a clearly better chunk
RERANK_CONFIDENCE_FLOOR = 0.55  # Chapter 8: calibrated against labeled_dataset.jsonl


def retrieve_for_prompt_with_memory(query: str, session) -> list[Chunk]:
    """
    Hybrid retrieval (top-20) → cross-encoder rerank with active-SKU bonus → top 3.
    Chunks below the confidence floor are withheld (same gate-kept spirit as Book 1).
    """
    candidates = retrieve_hybrid(query, top_n=20)
    if not candidates:
        return []

    ce_scores = rerank_scores_remote(query, candidates)

    active_skus = getattr(session, "active_skus", []) if session is not None else []

    boosted: list[tuple[Chunk, float]] = []
    for c, s in zip(candidates, ce_scores):
        sku   = c.metadata.get("product_id") or c.metadata.get("sku", "")
        bonus = ACTIVE_SKU_BOOST if sku in active_skus else 0.0
        boosted.append((c, float(s) + bonus))

    boosted.sort(key=lambda item: item[1], reverse=True)

    # Apply Chapter 8 confidence floor
    above_floor = [(c, s) for c, s in boosted if s >= RERANK_CONFIDENCE_FLOOR]

    # When the session has active products, return only chunks from those products
    # if any pass the floor. This prevents sibling products from entering the
    # prompt on follow-up queries (e.g. other coord-sets when asking about size L
    # for a specific co-ord set the customer is already discussing).
    # Only fall back to unrestricted top-3 if no active-sku chunks cleared the floor.
    if active_skus:
        active_chunks = [
            c for c, _ in above_floor
            if (c.metadata.get("product_id") or c.metadata.get("sku", "")) in active_skus
        ]
        if active_chunks:
            return active_chunks[:3]
        # Active products had no chunks above the floor — fall through to normal top-3
    return [c for c, _ in above_floor[:3]]
