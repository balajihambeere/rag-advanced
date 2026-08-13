# retrieval/crag.py
# Source: Book 3, Chapter 3 — The Chain That Checks Itself
# CRAG: Corrective Retrieval-Augmented Generation.
#
# Type-mismatch failures looked like successes from every angle except the
# customer's: retrieval correct, model received accurate evidence, chain ran
# clean, answer was either fabrication or an unhelpful terse refusal.
# The fix: a judge step between retrieval and generation that reads the query
# and the retrieved context together and classifies the relationship.
#
# Three verdicts:
#   RELEVANT   — context directly addresses the question. Pass through.
#   PARTIAL    — context about the right product but wrong dimension
#                (e.g. saree chunk for a jewellery question). Generate a
#                refined sub-query, re-retrieve, merge, pass through.
#   IRRELEVANT — context does not address the question. Route to support.
#
# Ch. 8 update (Route-D fix): when the original retrieval was HyDE-routed,
# the sub-query prompt receives the raw customer query — not the hypothetical —
# so the corrective re-retrieval anchors on the customer's actual words.

from infra.clients import llm_small
from infra.types import Chunk
from retrieval.entry import retrieve_with_optional_hyde
from retrieval.hybrid import reciprocal_rank_fusion

CRAG_JUDGE_PROMPT = """You are a retrieval judge for a fashion catalog chatbot.

Customer query:
{query}

Retrieved context:
{context}

Decide whether the context DIRECTLY addresses the customer's question:

- RELEVANT   : The context answers the question as asked.
- PARTIAL    : The context is about the right product but does not address
               the specific dimension the customer asked about (e.g., asks
               about jewellery but context only describes clothing).
- IRRELEVANT : The context is about the wrong product entirely, or no
               usable context was retrieved.

Respond with the verdict on the first line.
If PARTIAL, on the second line write a refined sub-query in plain English
that targets the missing dimension.  Otherwise leave the second line blank.

Verdict:"""


def crag_judge(query: str, context: str) -> tuple[str, str | None]:
    """
    Classify the relationship between query and retrieved context.

    Returns (verdict, sub_query).
    verdict: RELEVANT | PARTIAL | IRRELEVANT.
    sub_query: str if verdict is PARTIAL, else None.
    """
    raw = llm_small.complete(
        prompt=CRAG_JUDGE_PROMPT.format(query=query, context=context),
        max_tokens=80,
    )
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    verdict = lines[0].upper() if lines else "IRRELEVANT"
    sub = lines[1] if len(lines) > 1 else None
    return verdict, sub


def crag_retrieve(
    query: str,
    *,
    raw_query: str | None = None,
    top_n: int = 10,
) -> list[Chunk] | None:
    """
    Retrieve, judge, branch.

    raw_query: the original customer query before any HyDE rewriting.
    When provided and the verdict is PARTIAL, the sub-query is generated
    from raw_query rather than the (possibly hypothetical) query — this is
    the Ch. 8 Route-D fix that moved Route D F from 0.79 to 0.86.

    Returns list[Chunk] if verdict is RELEVANT or PARTIAL.
    Returns None if verdict is IRRELEVANT — caller must produce support fallback.
    """
    chunks = retrieve_with_optional_hyde(query, top_n=top_n)
    if not chunks:
        return None

    context = "\n\n".join(c.text for c in chunks[:5])
    anchor = raw_query if raw_query is not None else query
    verdict, sub_query = crag_judge(anchor, context)

    if verdict == "RELEVANT":
        return chunks

    if verdict == "PARTIAL" and sub_query:
        extra = retrieve_with_optional_hyde(sub_query, top_n=top_n)
        if extra:
            return [chunk for chunk, _ in reciprocal_rank_fusion(chunks, extra)[:top_n]]
        # Sub-query found nothing — return original context with partial coverage
        return chunks

    # IRRELEVANT — honest refusal
    return None
