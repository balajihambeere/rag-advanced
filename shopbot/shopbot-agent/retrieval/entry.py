# retrieval/entry.py
# Source: Book 3, Chapter 2 — The Answer Before the Question
# Single entry point for all retrieval in Book 3.
# Routes vague queries through HyDE; specific queries through standard hybrid.
#
# Used by retrieval/crag.py and pipeline/nodes.py (re_retrieve_node).
# The pipeline/nodes.py standard_retrieve_node uses retrieve_for_prompt_with_memory
# instead (which adds cross-encoder reranking + active-SKU boost before CRAG).

from infra.types import Chunk
from retrieval.vague_classifier import is_vague
from retrieval.hyde import hyde_retrieve
from retrieval.hybrid import retrieve_hybrid


def retrieve_with_optional_hyde(query: str, top_n: int = 10) -> list[Chunk]:
    """
    Routing entry point for CRAG re-retrieval and sub-query retrieval.

    - Vague query  → HyDE (embed hypothetical answer, retrieve against it)
    - Specific query → standard hybrid + RRF (unchanged from Book 2)

    Note: standard_retrieve_node in the LangGraph graph calls
    retrieve_for_prompt_with_memory() instead, which adds cross-encoder
    reranking on top of hybrid retrieval before the CRAG judge fires.
    This function is used for re-retrieval sub-queries and HyDE candidates.
    """
    if is_vague(query):
        return hyde_retrieve(query, top_n=top_n)
    return retrieve_hybrid(query, top_n=top_n)
