# retrieval/hyde.py
# Source: Book 3, Chapter 2 — The Answer Before the Question
# HyDE: Hypothetical Document Embeddings.
#
# Vague queries ("anything light", "something nice for the weekend") embed
# poorly because question-vectors and catalog-description-vectors sit in
# different regions of embedding space even when they share the same topic.
# HyDE generates a hypothetical product recommendation, embeds THAT, and
# retrieves against the hypothetical. The original query drives generation;
# only the retrieval step uses the hypothetical.
#
# Ch. 8 update: HYDE_PROMPT now anchors to named product categories to prevent
# generic hypotheticals when first-time-customer queries lack product vocabulary.
# This fixed the Route-C mid-campaign regression (F −0.04, CP −0.05).

from infra.clients import llm_small
from infra.types import Chunk
from retrieval.hybrid import retrieve_hybrid

HYDE_PROMPT = """A customer browsing zUdyog Fashion asked:
"{query}"

Write 2-3 sentences as if you were recommending a specific product from
zUdyog's catalog. Focus on concrete attributes — fabric, colour, occasion,
sizes, price. Do not actually invent a product name; describe the *kind*
of product that would answer the question. When at all plausible, anchor
your hypothetical to one of these product categories: cotton kurta, woolen
shawl, silk saree, linen co-ord set, anarkali suit.

Hypothetical recommendation:"""


def hyde_retrieve(query: str, top_n: int = 10) -> list[Chunk]:
    """
    Generate a hypothetical recommendation, embed it, retrieve against it.

    The retriever receives the hypothetical not the original query.
    The hypothetical does not need to be factually correct — it only needs
    to look like a product recommendation in shape and vocabulary.
    The original query is passed to the generation model later.
    """
    hypothetical = llm_small.complete(
        prompt=HYDE_PROMPT.format(query=query),
        max_tokens=120,
    )
    return retrieve_hybrid(hypothetical, top_n=top_n)
