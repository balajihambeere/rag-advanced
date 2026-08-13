# retrieval/rerank.py
# Source: Book 2, Chapter 4 — The Third Result Was Right; Chapter 9 (moved to HTTP)
# Cross-encoder reranking: scores each (query, candidate) pair together.
# Richer relevance judgment than bi-encoder cosine — the model reads query and
# candidate as one input, so attention can cross between them.
#
# Architecture: hybrid retriever produces top-20 candidates; the standalone
# ../shopbot-rerank/ service reranks them; top-3 go to the model. This process
# has no in-process CrossEncoder — see retrieval/rerank_client.py.
# Faithfulness 0.79→0.83, Context Precision 0.85→0.88 (Chapter 4 scores).

from infra.types import Chunk
from retrieval.rerank_client import rerank_remote


def rerank(query: str, candidates: list[Chunk], top_k: int = 3) -> list[Chunk]:
    """Cross-encoder rerank via the remote service. Return top_k."""
    return rerank_remote(query, candidates, top_k)


def retrieve_for_prompt(query: str) -> list[Chunk]:
    """Hybrid retrieval → cross-encoder rerank → top 3. Stateless (no session)."""
    from retrieval.hybrid import retrieve_hybrid
    candidates = retrieve_hybrid(query, top_n=20)
    return rerank(query, candidates, top_k=3)
