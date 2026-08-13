# pipeline/nodes.py
# Source: Book 3, Chapter 4 — From Chain to Graph
# One function per node. Each reads state, does exactly one thing, returns state.
# Nodes do not call each other. All connections are in graph.py.
#
# standard_retrieve_node uses retrieve_for_prompt_with_memory() (hybrid top-20
# → cross-encoder rerank → active-SKU boost → floor 0.55 → top 3) so the
# cross-encoder still runs on the standard path before CRAG, as confirmed by
# the Ch. 9 end-to-end latency trace (step 4: cross-encoder rerank 31ms).
# hyde_retrieve_node uses hyde_retrieve() (hypothetical → hybrid, no reranker).
# re_retrieve_node uses retrieve_with_optional_hyde() for sub-query re-retrieval.

from infra.types import Chunk
from retrieval.hyde import hyde_retrieve
from retrieval.entry import retrieve_with_optional_hyde
from retrieval.memory_aware import retrieve_for_prompt_with_memory
from retrieval.crag import crag_judge
from retrieval.hybrid import reciprocal_rank_fusion
from pipeline.generate import generate_with_chunks
from pipeline.state import PipelineState

SUPPORT_FALLBACK = (
    "I can find product information for our catalog, but that "
    "specific question is not something I can answer from what "
    "we stock. Please reach our team at support@zudyog.in for help."
)


def classify_vague_node(state: PipelineState) -> PipelineState:
    from retrieval.vague_classifier import is_vague
    state["is_vague"] = is_vague(state["query"])
    return state


def hyde_retrieve_node(state: PipelineState) -> PipelineState:
    state["chunks"] = hyde_retrieve(state["query"])
    return state


def standard_retrieve_node(state: PipelineState) -> PipelineState:
    state["chunks"] = retrieve_for_prompt_with_memory(
        state["query"], state["session"]
    )
    return state


def crag_judge_node(state: PipelineState) -> PipelineState:
    chunks = state["chunks"] or []
    context = "\n\n".join(c.text for c in chunks[:5])
    # Ch. 8 Route-D fix: pass raw query as anchor so PARTIAL sub-queries use
    # the customer's original words, not any HyDE-rewritten form.
    verdict, sub = crag_judge(state["query"], context)
    state["crag_verdict"] = verdict
    state["sub_query"] = sub
    return state


def re_retrieve_node(state: PipelineState) -> PipelineState:
    if state["sub_query"]:
        extra = retrieve_with_optional_hyde(state["sub_query"])
        if extra:
            fused = reciprocal_rank_fusion(state["chunks"] or [], extra)
            state["chunks"] = [chunk for chunk, _ in fused[:10]]
    return state


def generate_node(state: PipelineState) -> PipelineState:
    state["answer"] = generate_with_chunks(
        state["query"],
        state["chunks"] or [],
        state["session"],
    )
    return state


def fallback_node(state: PipelineState) -> PipelineState:
    state["answer"] = SUPPORT_FALLBACK
    return state
