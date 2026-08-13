# evaluation/labeled_dataset.py
# Source: Book 3, Chapter 7 — What the Average Hides
# Utility for loading the labeled evaluation dataset.
# Shared by evaluation/evaluate.py, evaluation/per_route.py, and fine_tune/build_dataset.py.

import json
import os

DATASET_PATH = os.path.join(os.path.dirname(__file__), "labeled_dataset.jsonl")


def load_labeled(path: str = DATASET_PATH) -> list[dict]:
    """Load all labeled queries from the JSONL file."""
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]
