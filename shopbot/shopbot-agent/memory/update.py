# memory/update.py
# Source: Book 2, Chapter 6 — ShopBot Finally Remembers
# Session update helpers. Called after every answer is returned.
#
# Three pieces:
#   push_turn()           — append turn, keep last 3, update active SKUs
#   maybe_refresh_summary — compress every 4th turn into a 2-sentence summary
#   extract_mentioned_skus — pull SKUs from retrieved chunks

from memory.session import Session, Turn
from infra.clients import llm_small

SUMMARY_PROMPT = (
    "Summarise the conversation so far in two sentences. "
    "Focus on the products being discussed and any constraints "
    "the customer has mentioned. Do not invent facts."
)


def maybe_refresh_summary(session: Session, full_history: list[Turn]) -> None:
    """Refresh the rolling summary every 4th turn."""
    if len(full_history) % 4 != 0:
        return
    transcript = "\n".join(f"{t.role}: {t.content}" for t in full_history)
    try:
        session.summary = llm_small.complete(
            system=SUMMARY_PROMPT,
            user=transcript,
            max_tokens=120,
        )
    except Exception:
        pass  # Stale summary is better than a crashed request


def push_turn(session: Session, turn: Turn, mentioned_skus: list[str]) -> None:
    """
    Append one turn. Keep only the last 3 verbatim.
    Update active_skus: most-recently-mentioned first, cap at 3.
    """
    session.recent_turns.append(turn)
    session.recent_turns = session.recent_turns[-3:]

    for sku in mentioned_skus:
        if sku in session.active_skus:
            session.active_skus.remove(sku)
        session.active_skus.insert(0, sku)
    session.active_skus = session.active_skus[:3]


def extract_mentioned_skus(chunks) -> list[str]:
    """Return unique product_ids from the retrieved chunks."""
    seen = []
    for chunk in chunks:
        pid = chunk.metadata.get("product_id") or chunk.metadata.get("sku", "")
        if pid and pid not in seen:
            seen.append(pid)
    return seen
