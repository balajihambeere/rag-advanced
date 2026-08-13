# pipeline/graph.py
# Source: Book 3, Chapter 4 — From Chain to Graph
# Assembles the LangGraph pipeline from nodes and edges.
# The module-level `pipeline` singleton is compiled once at import time;
# the lifespan in src/api.py triggers this import at server startup.
#
# Draw the graph: print(pipeline.get_graph().draw_ascii())
#
#                       [ classify_vague ]
#                               │
#               ┌──────vague────┴────specific────┐
#               ▼                                 ▼
#           [ hyde ]                  [ standard_retrieve ]
#               │                                 │
#               └─────────────┬───────────────────┘
#                             ▼
#                      [ crag_judge ]
#             ┌──────────────┼──────────────┐
#             ▼              ▼              ▼
#       [ generate ]  [ re_retrieve ]  [ fallback ]
#             │              │              │
#             ▼              ▼              ▼
#            END       [ generate ]        END
#                            │
#                            ▼
#                           END

from langgraph.graph import StateGraph, END

from pipeline.state import PipelineState
from pipeline.nodes import (
    classify_vague_node,
    hyde_retrieve_node,
    standard_retrieve_node,
    crag_judge_node,
    re_retrieve_node,
    generate_node,
    fallback_node,
)
from pipeline.edges import route_after_classify, route_after_crag


def build_pipeline_graph():
    g = StateGraph(PipelineState)

    # ── Register nodes ──────────────────────────────────────────────────────────
    g.add_node("classify_vague",    classify_vague_node)
    g.add_node("hyde",              hyde_retrieve_node)
    g.add_node("standard_retrieve", standard_retrieve_node)
    g.add_node("crag_judge",        crag_judge_node)
    g.add_node("re_retrieve",       re_retrieve_node)
    g.add_node("generate",          generate_node)
    g.add_node("fallback",          fallback_node)

    # ── Entry point ─────────────────────────────────────────────────────────────
    g.set_entry_point("classify_vague")

    # ── vague → HyDE, specific → standard retrieval ─────────────────────────────
    g.add_conditional_edges(
        "classify_vague",
        route_after_classify,
        {"hyde": "hyde", "standard_retrieve": "standard_retrieve"},
    )

    # ── Both retrieval paths converge at the CRAG judge ─────────────────────────
    g.add_edge("hyde",              "crag_judge")
    g.add_edge("standard_retrieve", "crag_judge")

    # ── RELEVANT → generate, PARTIAL → re_retrieve, IRRELEVANT → fallback ───────
    g.add_conditional_edges(
        "crag_judge",
        route_after_crag,
        {
            "generate":    "generate",
            "re_retrieve": "re_retrieve",
            "fallback":    "fallback",
        },
    )

    # ── Re-retrieve always flows into generate ──────────────────────────────────
    g.add_edge("re_retrieve", "generate")

    # ── Terminal edges ───────────────────────────────────────────────────────────
    g.add_edge("generate", END)
    g.add_edge("fallback", END)

    return g.compile()


# Module-level singleton — built once at startup, invoked per request
pipeline = build_pipeline_graph()
