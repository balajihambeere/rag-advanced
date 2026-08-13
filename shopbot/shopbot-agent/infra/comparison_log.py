# infra/comparison_log.py
# Source: Book 2, Chapter 2 + Appendix A — Code Wiring
# Append-only JSONL writer for the shadow-read comparison log (Chapter 2).
# Records per-query agreement between ChromaDB (primary) and Qdrant (shadow)
# during the migration period. Used to verify the migration is safe before cutover.

import json
from pathlib import Path
from threading import Lock

_LOG_PATH = Path("logs/qdrant_shadow_comparison.jsonl")
_LOCK = Lock()


def append(record: dict) -> None:
    """Append one comparison record (thread-safe)."""
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with _LOCK:
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
