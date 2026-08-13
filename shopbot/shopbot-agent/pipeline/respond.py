# pipeline/respond.py
# Source: Book 3, Chapter 4 — From Chain to Graph
# Public entry point for the Book 3 pipeline.
# Delegates to the compiled LangGraph pipeline singleton.
# Called by src/api.py in place of the Book 2 answer_with_cache() path.

from memory.session import Session
from pipeline.graph import pipeline
from pipeline.state import PipelineState


def respond(query: str, session: Session) -> str:
    """
    Run the LangGraph pipeline for one query.
    Returns the answer string (either generated or the support fallback).
    """
    initial: PipelineState = {
        "query":        query,
        "session":      session,
        "is_vague":     None,
        "crag_verdict": None,
        "sub_query":    None,
        "chunks":       None,
        "answer":       None,
    }
    final = pipeline.invoke(initial)
    return final["answer"] or ""
