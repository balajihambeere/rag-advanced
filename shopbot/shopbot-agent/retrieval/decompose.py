# retrieval/decompose.py
# Source: Book 2, Chapter 5 — Two Halves of One Question
#         Book 2, Chapter 6 — ShopBot Finally Remembers (context-aware path)
# Query decomposition: detects one vs two intents in a customer query.
# Single-intent queries pass through unchanged (list of one).
# Two-intent queries are split into two focused sub-queries for separate retrieval.
#
# When a session is supplied, recent_turns are included in the prompt so the
# decomposer can rewrite ambiguous follow-up questions ("What about size L?")
# into self-contained queries ("What sizes are available for the cotton kurta?")
# that the cross-encoder can score correctly.
#
# The prompt also carries a fashion-specific two-intent hint: combining an
# occasion (festive, wedding, office) with a physical property (warm,
# lightweight, breathable) almost always means TWO separate products, so
# the decomposer splits these even when the surface form looks like one query.
#
# Cost: one gpt-4o-mini call per query (~₹0.0008). Single-intent queries still
# pay this cost; the detection call is short. On ~9% of traffic (two-intent
# queries), a second retrieval pass also runs.

import json
from infra.clients import llm_small

DECOMPOSE_PROMPT = """\
The user has asked a question about an Indian fashion catalog. If the question
contains ONE intent, return a JSON list with one paraphrase: ["<paraphrase>"].
If it contains TWO independent intents that need separate retrievals to answer,
return a JSON list with two paraphrases: ["<intent A>", "<intent B>"]. Never
return more than two. Keep paraphrases short and self-contained.

When paraphrasing, use standard fashion catalog vocabulary. Customers often use
Indian English terms — translate them into their standard equivalents so the
catalog search can match correctly (e.g. "function" → "wedding or festive event").

In Indian fashion, combining an occasion (festive, wedding, office, casual) with a
PHYSICAL property — a warmth or texture attribute such as warm, lightweight,
breathable, heavy, woolen, sheer — almost always means TWO separate products: an
occasion garment and a layering/accessory piece. Split these into two intents
(e.g. "festive and warm" → ["festive clothing for a wedding event", "warm layering
for cool weather"]).

Do NOT split on time-of-day qualifiers (evening, morning, daytime, night) — these
narrow the occasion and stay ONE intent (e.g. "office party in the evening" is ONE
intent: "outfit for an evening office gathering").

{context_block}Question: {query}

JSON:
"""

_CONTEXT_BLOCK_TEMPLATE = """\
Recent conversation:
{recent_turns}

Rules for rewriting:
1. Replace ALL pronouns ("it", "they", "them", "that", "those") with the actual \
product name(s) from the conversation.
2. The MOST RECENT assistant message determines the active product(s). Always \
resolve pronouns to products from the most recent assistant message first.
3. Only name multiple products if the MOST RECENT assistant message itself \
recommended multiple products in the same response (e.g. "Are the Straight Cut \
Palazzo Suit and Silk Co-ord Set in stock?"). Do not reach back to older messages \
to add more products.
4. The paraphrase must be fully self-contained — no unresolved pronouns.
Example: "What about size L?" → "What sizes are available for the Linen Co-ord Set?"
Example: "Do you have it in stock?" → "Is the Straight Cut Palazzo Suit in stock?"

"""


def decompose(query: str, session=None) -> list[str]:
    """
    Decompose a customer query into one or two focused sub-queries.
    When session has recent_turns, includes them so follow-up questions are
    rewritten to self-contained queries before retrieval runs.
    Falls back to [query] on any parse error — fail-safe, not fail-hard.
    """
    context_block = ""
    if session is not None:
        turns = getattr(session, "recent_turns", [])
        if turns:
            recent = "\n".join(f"{t.role}: {t.content}" for t in turns)
            context_block = _CONTEXT_BLOCK_TEMPLATE.format(recent_turns=recent)

    raw = llm_small.complete(
        prompt=DECOMPOSE_PROMPT.format(query=query, context_block=context_block),
        max_tokens=120,
    )
    try:
        text = raw.strip()
        # Strip markdown code fences if the model wrapped the JSON
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1].lstrip("json").strip() if len(parts) > 1 else text
        sub_queries = json.loads(text)
        if not isinstance(sub_queries, list) or not 1 <= len(sub_queries) <= 2:
            return [query]
        return [str(sq).strip() for sq in sub_queries if sq]
    except (json.JSONDecodeError, ValueError, IndexError):
        return [query]  # fail-safe — treat as single intent
