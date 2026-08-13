# evaluation/routes.py
# Source: Book 3, Chapter 7 — What the Average Hides
# Maps the final PipelineState to one of five named pipeline routes.
# Used by evaluation/per_route.py to group labeled queries before RAGAS scoring.
#
# Five routes:
#   A — standard retrieval, CRAG ruled RELEVANT
#   B — standard retrieval, CRAG ruled PARTIAL (re-retrieved)
#   C — HyDE retrieval,     CRAG ruled RELEVANT
#   D — HyDE retrieval,     CRAG ruled PARTIAL (re-retrieved)
#   E — fallback            (CRAG ruled IRRELEVANT, or support@zudyog.in in answer)
#   X — unknown             sanity-check bucket; should be empty in normal operation

from pipeline.state import PipelineState

SUPPORT_EMAIL = "support@zudyog.in"


def derive_route(state: PipelineState) -> str:
    """Derive the route label from the pipeline's final state."""
    # Fallback is identified by the support-routing text in the answer,
    # since IRRELEVANT queries never set chunks or produce a generated answer.
    answer = state.get("answer") or ""
    if SUPPORT_EMAIL in answer:
        return "E_fallback"

    hyde = state.get("is_vague") is True
    crag = (state.get("crag_verdict") or "").upper()

    if not hyde and crag == "RELEVANT":
        return "A_standard_relevant"
    if not hyde and crag == "PARTIAL":
        return "B_standard_partial"
    if hyde and crag == "RELEVANT":
        return "C_hyde_relevant"
    if hyde and crag == "PARTIAL":
        return "D_hyde_partial"

    return "X_unknown"
