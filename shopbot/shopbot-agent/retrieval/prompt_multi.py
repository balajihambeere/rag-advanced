# retrieval/prompt_multi.py
# Source: Book 2, Chapter 5 + Chapter 6
# Builds the full user-turn message that the LLM receives.
# In Book 2, context moves from the system prompt into the user message so that
# session memory (summary, recent turns) can be included in the same turn.
#
# Structure of the user message:
#   # Conversation summary      (if session has one)
#   # Note to the assistant     (if two-intent query)
#   # Recent turns              (last 3 verbatim)
#   # Retrieved catalog evidence
#   # Current customer message

from infra.types import Chunk


def build_prompt_multi(
    query: str,
    sub_queries: list[str],
    retrieved: list[Chunk],
    session=None,
) -> str:
    """
    Build the user-turn prompt string for the LLM.
    Incorporates session state and multi-intent awareness.
    """
    parts = []

    if session is not None and getattr(session, "summary", ""):
        parts.append(f"# Conversation summary\n{session.summary}\n")

    if len(sub_queries) > 1:
        parts.append(
            "# Note to the assistant\n"
            "The customer has asked a question with two distinct intents. "
            "Both must be acknowledged. The retrieved evidence below contains "
            "products relevant to each intent. Do not collapse the answer into "
            "one recommendation if both intents need separate products.\n"
            f"Detected sub-queries: {sub_queries}\n"
        )

    if session is not None and getattr(session, "recent_turns", []):
        recent = "\n".join(
            f"{t.role}: {t.content}" for t in session.recent_turns
        )
        parts.append(f"# Recent turns\n{recent}\n")

    if retrieved:
        context = "\n\n".join(c.text for c in retrieved)
        parts.append(f"# Retrieved catalog evidence\n{context}\n")
    else:
        parts.append("# Retrieved catalog evidence\n(none)\n")

    parts.append(f"# Current customer message\n{query}\n")

    return "\n".join(parts)
