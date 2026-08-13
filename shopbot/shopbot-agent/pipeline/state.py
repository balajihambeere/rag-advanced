# pipeline/state.py
# Source: Book 3, Chapter 4 — From Chain to Graph
# The single typed dictionary that flows through every node of the LangGraph pipeline.
# Every node reads from it, modifies it, and returns it. No node calls another node.
# The connections between nodes are in graph.py, not in function bodies.

from typing import Optional, TypedDict
from infra.types import Chunk
from memory.session import Session


class PipelineState(TypedDict):
    # ── Inputs ──────────────────────────────────────────────────────────────────
    query:   str
    session: Session

    # ── Routing decisions (written by nodes, read by edge functions) ─────────────
    is_vague:     Optional[bool]
    crag_verdict: Optional[str]   # RELEVANT | PARTIAL | IRRELEVANT
    sub_query:    Optional[str]

    # ── Intermediate results ─────────────────────────────────────────────────────
    chunks: Optional[list[Chunk]]

    # ── Output ───────────────────────────────────────────────────────────────────
    answer: Optional[str]
