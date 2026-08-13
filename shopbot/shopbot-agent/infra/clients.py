# infra/clients.py
# Source: Book 2, Appendix A (baseline) + Book 3, Chapters 6, 8, and 9 (updates)
# Shared client module. Build once; import everywhere.
# Every module that needs embed(), llm, qdrant_client, bm25, or r imports from
# here — never constructs its own client.
#
# Book 3 changes:
#   Ch. 6 — embed() uses the fine-tuned bge-small ONNX INT8 model (384-dim).
#   Ch. 8 — _LLM uses two OpenAI keys round-robin to avoid throttling at 600 qpm.
#            Set OPENAI_API_KEY_PRIMARY and OPENAI_API_KEY_SECONDARY in .env.
#            If OPENAI_API_KEY_SECONDARY is absent, falls back to primary only.
#   Ch. 9 / ingest-agent-rerank split — cross-encoder reranking AND embedding
#            both run exclusively in the standalone ../shopbot-rerank/ service
#            (services/inference/main.py in the pre-split checkout). This process
#            has no in-process CrossEncoder or ONNXEmbedder — see
#            retrieval/rerank_client.py for the HTTP calls. RERANK_URL is
#            required; there is no fallback (mirrors Book 2's shopbot-agent).

import itertools
import os
import httpx
from openai import OpenAI
from qdrant_client import QdrantClient
import redis
from fastembed import SparseTextEmbedding
from dotenv import load_dotenv

load_dotenv()

# ── Embedding — Ch. 6, moved to HTTP by the ingest/agent/rerank split ───────
# The fine-tuned bge-small ONNX INT8 model (384-dim, ~2ms) is served by
# ../shopbot-rerank/'s /embed endpoint — this process never loads it in-process
# (onnxruntime/transformers stay out of this project's requirements.txt). No
# fallback: a forgotten `docker run` on shopbot-rerank fails loudly here rather
# than silently degrading to a different embedding space.
RERANK_URL = os.environ["RERANK_URL"]


def embed(text: str) -> list[float]:
    """Remote embedding — bge-small fine-tuned, ONNX INT8, served by ../shopbot-rerank/."""
    with httpx.Client(timeout=5.0) as client:
        resp = client.post(f"{RERANK_URL}/embed", json={"text": text})
        resp.raise_for_status()
        return resp.json()["embedding"]

# ── Multi-key LLM — Book 3, Ch. 8 ───────────────────────────────────────────
# At 600 qpm the pipeline issues ~1,300 LLM calls/min (HyDE + CRAG + generate).
# A single API key throttles at that volume. Two keys, round-robin.
_primary_key   = os.environ.get("OPENAI_API_KEY_PRIMARY") or os.environ["OPENAI_API_KEY"]
_secondary_key = os.environ.get("OPENAI_API_KEY_SECONDARY")

if _secondary_key:
    _key_cycle = itertools.cycle([_primary_key, _secondary_key])
else:
    _key_cycle = itertools.cycle([_primary_key])


def _next_openai_client() -> OpenAI:
    return OpenAI(api_key=next(_key_cycle))


class _LLM:
    """Thin wrapper over chat.completions for the prose-style usage in chapters."""

    def __init__(self, model: str, temperature: float = 0):
        self.model = model
        self.temperature = temperature

    def complete(
        self,
        *,
        system: str | None = None,
        user: str | None = None,
        prompt: str | None = None,
        max_tokens: int = 800,
    ) -> str:
        if prompt is not None and system is None and user is None:
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            if user:
                messages.append({"role": "user", "content": user})
        client = _next_openai_client()
        resp = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=max_tokens,
            messages=messages,
        )
        return resp.choices[0].message.content


# Two LLM handles — the main answerer and the small classifier/judge/decomposer.
# Both use gpt-4o-mini with temperature=0 (deterministic). Hard rule.
llm       = _LLM("gpt-4o-mini", temperature=0)
llm_small = _LLM("gpt-4o-mini", temperature=0)

# ── Qdrant Cloud ─────────────────────────────────────────────────────────────
qdrant_client = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
)

# ── Redis — sessions + cache ─────────────────────────────────────────────────
r = redis.from_url(os.environ["REDIS_URL"])

# ── BM25 sparse encoder — Book 2, Chapter 3 ─────────────────────────────────
# Lightweight (no torch/onnx dependency) — stays in-process, unlike the
# cross-encoder and the dense embedder.
bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")
