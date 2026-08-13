# retrieval/rerank_client.py
# Source: Book 2, Chapter 9 — Real Production; Book 3, the ingest/agent/rerank split.
# Sync HTTP client for the standalone inference service (../shopbot-rerank/main.py
# — a separate, standalone project, not a subfolder of this one). Cross-encoder
# reranking runs there — this process has no in-process fallback, so RERANK_URL
# is required (run ../shopbot-rerank/ via Docker locally, same as in production).
# (Dense embedding also runs on that same service, via infra/clients.py:embed()
# — that HTTP call lives there, not here, since infra/ owns client construction.)
#
# Synchronous by design: the whole retrieval call chain (retrieve_multi →
# _retrieve_one → retrieve_for_prompt_with_memory) and the /ask handler in
# src/api.py are plain sync functions — an async client here would need an
# event loop none of those callers have.

import os
import httpx
from infra.types import Chunk

RERANK_URL = os.environ["RERANK_URL"]


def _call_rerank_service(query: str, candidates: list[Chunk], top_k: int) -> tuple[list[str], list[float]]:
    payload = {
        "query":      query,
        "candidates": [{"id": c.id, "text": c.text} for c in candidates],
        "top_k":      top_k,
    }
    with httpx.Client(timeout=5.0) as client:
        resp = client.post(f"{RERANK_URL}/rerank", json=payload)
        resp.raise_for_status()
        body = resp.json()
    return body["ranked_ids"], body["scores"]


def rerank_remote(query: str, candidates: list[Chunk], top_k: int = 3) -> list[Chunk]:
    """Sorted top_k chunks, reranked by the remote cross-encoder service."""
    if not candidates:
        return []
    ranked_ids, _ = _call_rerank_service(query, candidates, top_k)
    by_id = {c.id: c for c in candidates}
    return [by_id[cid] for cid in ranked_ids if cid in by_id]


def rerank_scores_remote(query: str, candidates: list[Chunk]) -> list[float]:
    """
    A cross-encoder score for every candidate, aligned to input order.

    Unlike rerank_remote() (which only needs the top_k winners), memory_aware.py
    needs raw scores for the FULL candidate set to apply the active-SKU boost
    and confidence floor — a chunk the remote model ranked outside the naive
    top-k can still end up in the final top-3 after boosting. Requests all
    candidates back (top_k=len(candidates)) to get that.
    """
    if not candidates:
        return []
    ranked_ids, scores = _call_rerank_service(query, candidates, top_k=len(candidates))
    score_by_id = dict(zip(ranked_ids, scores))
    return [score_by_id[c.id] for c in candidates]
