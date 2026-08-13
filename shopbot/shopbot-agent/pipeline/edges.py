# pipeline/edges.py
# Source: Book 3, Chapter 4 — From Chain to Graph
# All routing logic lives here. Edge functions return a node name string.
# Two decision points; eight lines of conditional; nothing else.

from pipeline.state import PipelineState


def route_after_classify(state: PipelineState) -> str:
    """After classify_vague: vague → HyDE, specific → standard retrieval."""
    return "hyde" if state["is_vague"] else "standard_retrieve"


def route_after_crag(state: PipelineState) -> str:
    """After crag_judge: RELEVANT → generate, PARTIAL → re_retrieve, else fallback."""
    verdict = state["crag_verdict"]
    if verdict == "RELEVANT":
        return "generate"
    if verdict == "PARTIAL":
        return "re_retrieve"
    return "fallback"
