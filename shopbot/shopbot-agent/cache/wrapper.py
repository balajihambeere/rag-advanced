# cache/wrapper.py
# Source: Book 2, Chapter 7 — Paying Twice for the Same Answer
# Top-level answer function. Checks exact cache, then semantic cache,
# then falls through to the full retrieval + generation pipeline.
# Writes every cache-miss result back to both cache layers.

import time

from infra.clients import embed, llm
from infra.types import Chunk
from cache.layered import CachedAnswer, get_exact, get_semantic, put_exact, put_semantic
from retrieval.multi_query import retrieve_multi
from retrieval.prompt_multi import build_prompt_multi
from retrieval.system_prompt import SHOPBOT_SYSTEM_B2

FALLBACK_ANSWER = (
    "I don't have a product that matches that specifically. "
    "Could you describe what you're looking for differently, "
    "or contact our team at support@zudyog.com?"
)


def answer_with_cache(query: str, session=None) -> tuple[str, list[Chunk], list[str]]:
    """
    Answer a customer query using the three-layer cache.

    Returns (answer, retrieved_chunks, sub_queries).
    Callers use retrieved_chunks to update session active_skus.
    sub_queries is used for prompt construction (already consumed here, exposed
    for callers that want to log which path fired).
    """
    # Context-sensitive queries (follow-ups with session history) must bypass
    # both cache layers — the same string means different things in different
    # sessions ("What about size L?" depends entirely on what was just discussed).
    has_context = bool(session and getattr(session, "recent_turns", None))

    if not has_context:
        # Layer 1 — exact-match (string hash)
        hit = get_exact(query)
        if hit is not None:
            return hit.answer, [], []

        # Layer 2 — semantic (cosine ≥ 0.97)
        query_vec = embed(query)
        hit = get_semantic(query_vec)
        if hit is not None:
            return hit.answer, [], []
    else:
        query_vec = embed(query)

    # Layer 3 — full pipeline
    retrieved, sub_queries = retrieve_multi(query, session)

    if not retrieved:
        answer = FALLBACK_ANSWER
    else:
        user_msg = build_prompt_multi(query, sub_queries, retrieved, session)
        answer = llm.complete(system=SHOPBOT_SYSTEM_B2, user=user_msg)

    # Only cache context-free queries — session-specific answers must not
    # be served to other sessions asking the same string.
    if not has_context:
        retrieved_skus = list({
            c.metadata.get("product_id") or c.metadata.get("sku", "")
            for c in retrieved
        } - {""})
        cached = CachedAnswer(
            answer=answer,
            retrieved_skus=retrieved_skus,
            created_at=time.time(),
        )
        put_exact(query, cached)
        put_semantic(query, query_vec, cached)

    return answer, retrieved, sub_queries
