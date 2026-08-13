# fine_tune/build_dataset.py
# Source: Book 3, Chapter 5 — A Smaller Model That Knows the Catalog
# Builds contrastive training triplets from the labeled evaluation dataset.
#
# A triplet is (query, positive_chunk, hard_negative_chunk).
#   positive  — a chunk labeled as relevant for this query
#   hard_neg  — a chunk from the same product but a different chunk_type
#               (e.g. identity vs care vs FAQ). Same-product negatives force
#               the model to distinguish dimensions, not just products.
#
# Each seed query is expanded into 8 paraphrases using the LLM, so a
# 100-query labeled set produces ~3,400 triplets — enough to fine-tune a
# 33M-parameter model without overfitting.

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clients import llm_small
from chunk_types import Chunk
from fine_tune.catalog_store import get_chunk, sample_hard_negative

try:
    from sentence_transformers import InputExample
except ImportError:
    raise ImportError("pip install sentence-transformers to run fine_tune/build_dataset.py")

# The labeled dataset lives in the sibling ../shopbot-agent/ project (it's the
# same dataset RAGAS Monday scores against — see evaluation/labeled_dataset.jsonl
# there). Fine-tuning is a manual, one-time, offline step, so a relative
# cross-sibling path is acceptable here — no shared import, just a file read.
# (This also fixes a pre-existing path bug: the old path pointed at "../eval/",
# a directory that has never existed; the real one is "evaluation/".)
DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "shopbot-agent", "evaluation", "labeled_dataset.jsonl"
)

PARAPHRASE_PROMPT = """Rewrite the following customer question eight times using
different phrasing. Keep the same intent. Vary formality, word order, and
completeness — include some short casual phrasings and some longer specific ones.
Output one rewrite per line, no numbering.

Question: {query}

Rewrites:"""


def load_labeled(path: str = DATASET_PATH) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def expand_queries(query: str) -> list[str]:
    """Generate 8 paraphrases of a seed query."""
    raw = llm_small.complete(
        prompt=PARAPHRASE_PROMPT.format(query=query),
        max_tokens=200,
    )
    return [line.strip() for line in raw.strip().splitlines() if line.strip()]


def build_triplets(labeled: list[dict]) -> list["InputExample"]:
    """
    Build (query, positive_chunk, hard_negative) triplets.
    A 100-query dataset with ~3.8 relevant chunks/query × 9 query variants
    yields ~3,400 triplets.
    """
    triplets = []
    for case in labeled:
        seed = case["query"]
        relevant_ids = case.get("gold_chunk_ids", [])
        if not relevant_ids:
            continue

        queries = [seed] + expand_queries(seed)

        for query in queries:
            for pos_id in relevant_ids:
                try:
                    pos_chunk = get_chunk(pos_id)
                except ValueError:
                    continue

                neg_chunk = sample_hard_negative(
                    product_id=pos_chunk.metadata.get("product_id", ""),
                    exclude_chunk_type=pos_chunk.metadata.get("chunk_type", ""),
                )
                if neg_chunk is None:
                    continue

                triplets.append(InputExample(
                    texts=[query, pos_chunk.text, neg_chunk.text]
                ))

    return triplets


if __name__ == "__main__":
    rows = load_labeled()
    print(f"Loaded {len(rows)} labeled queries.")
    triplets = build_triplets(rows[:5])  # dry-run on 5 queries
    print(f"Built {len(triplets)} triplets from 5 queries (dry-run).")
    if triplets:
        print(f"  Sample anchor: {triplets[0].texts[0][:80]}")
