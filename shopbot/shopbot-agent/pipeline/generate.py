# pipeline/generate.py
# Source: Book 3, Chapter 4 — From Chain to Graph
# generate_with_chunks: the single generation call used by generate_node.
# Wraps build_prompt_multi + llm.complete into one function so generate_node
# stays a one-liner and the prompt-building logic stays in retrieval/prompt_multi.py.

from infra.clients import llm
from infra.types import Chunk
from memory.session import Session
from retrieval.prompt_multi import build_prompt_multi
from retrieval.system_prompt import SHOPBOT_SYSTEM_B2


def generate_with_chunks(
    query: str,
    chunks: list[Chunk],
    session: Session | None,
) -> str:
    """
    Build the user-turn message and call the LLM.
    sub_queries is empty in Book 3 — CRAG handles the multi-intent case
    via its own sub-query mechanism rather than the Book 2 decomposer.
    """
    user_msg = build_prompt_multi(query, [], chunks, session)
    return llm.complete(system=SHOPBOT_SYSTEM_B2, user=user_msg)
