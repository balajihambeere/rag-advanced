# retrieval/vague_classifier.py
# Source: Book 3, Chapter 2 — The Answer Before the Question
# Classifies a customer query as VAGUE (no product anchor) or SPECIFIC.
# A vague query triggers HyDE in retrieve_with_optional_hyde(); a specific
# query goes straight to standard hybrid retrieval.
#
# Cost: ~4 output tokens per query (~₹0.0003). Runs on every query before
# the retriever fires. At 9% vague traffic the average overhead is ₹0.0001/query.

from infra.clients import llm_small

VAGUE_CLASSIFIER_PROMPT = """The user asked a fashion-catalog question:
"{query}"

Is this query VAGUE (no specific product, no attribute, no SKU — open-ended)
or SPECIFIC (mentions a product, attribute, size, colour, or SKU)?

Answer with one word: VAGUE or SPECIFIC."""


def is_vague(query: str) -> bool:
    """
    Classify the query as vague (True) or specific (False).
    Single small-LLM call, temperature=0, 4 max_tokens.
    """
    response = llm_small.complete(
        prompt=VAGUE_CLASSIFIER_PROMPT.format(query=query),
        max_tokens=4,
    )
    return response.strip().upper().startswith("VAGUE")
