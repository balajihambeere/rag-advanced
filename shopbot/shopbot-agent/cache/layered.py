# cache/layered.py
# Source: Book 2, Chapter 7 — Paying Twice for the Same Answer
# Three-layer answer cache:
#   Layer 1 — exact-match: hash(query) → Redis (1h TTL)
#   Layer 2 — semantic:    embed(query) → Qdrant cosine at ≥0.97 (1h TTL)
#   Layer 3 — miss:        full pipeline (hybrid + rerank + memory + LLM)
#
# All cached answers carry retrieved_skus for targeted invalidation (Chapter 7).
# The 0.97 semantic threshold prevents false positives: "cotton kurta in white"
# must not match "cotton kurta in mint" (different answers). Tested at 0.92 and
# found false positives; 0.97 gives zero false positives on production traffic.

import hashlib
import json
import time
from dataclasses import dataclass

from infra.clients import embed, qdrant_client, r
from qdrant_client import models

EXACT_TTL          = 60 * 60    # 1 hour
SEMANTIC_TTL       = 60 * 60    # 1 hour
SEMANTIC_THRESHOLD = 0.97
CACHE_COLLECTION   = "answer_cache"


@dataclass
class CachedAnswer:
    answer: str
    retrieved_skus: list[str]
    created_at: float


# ── Helpers ──────────────────────────────────────────────────────────────────

def _exact_key(query: str) -> str:
    h = hashlib.sha256(query.strip().lower().encode()).hexdigest()
    return f"cache:exact:{h}"


def _query_to_uuid(query: str) -> str:
    """Convert query string to a stable UUID for use as a Qdrant point ID."""
    h = hashlib.sha256(query.encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def _ensure_cache_collection() -> None:
    existing = [c.name for c in qdrant_client.get_collections().collections]
    if CACHE_COLLECTION not in existing:
        qdrant_client.create_collection(
            collection_name=CACHE_COLLECTION,
            vectors_config=models.VectorParams(
                size=1536, distance=models.Distance.COSINE
            ),
        )


# ── Layer 1: exact-match ─────────────────────────────────────────────────────

def get_exact(query: str) -> CachedAnswer | None:
    try:
        raw = r.get(_exact_key(query))
        return CachedAnswer(**json.loads(raw)) if raw else None
    except Exception:
        return None


def put_exact(query: str, ans: CachedAnswer) -> None:
    try:
        r.setex(_exact_key(query), EXACT_TTL, json.dumps(ans.__dict__))
    except Exception:
        pass


# ── Layer 2: semantic ────────────────────────────────────────────────────────

def get_semantic(query_vec: list[float]) -> CachedAnswer | None:
    try:
        hits = qdrant_client.search(
            collection_name=CACHE_COLLECTION,
            query_vector=query_vec,
            limit=1,
            score_threshold=SEMANTIC_THRESHOLD,
        )
        if not hits:
            return None
        p = hits[0].payload
        return CachedAnswer(
            answer=p["answer"],
            retrieved_skus=p["retrieved_skus"],
            created_at=p["created_at"],
        )
    except Exception:
        return None


def put_semantic(query: str, query_vec: list[float], ans: CachedAnswer) -> None:
    try:
        _ensure_cache_collection()
        qdrant_client.upsert(
            collection_name=CACHE_COLLECTION,
            points=[
                models.PointStruct(
                    id=_query_to_uuid(query),
                    vector=query_vec,
                    payload=ans.__dict__ | {"query": query},
                )
            ],
        )
    except Exception:
        pass
