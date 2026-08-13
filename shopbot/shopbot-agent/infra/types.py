# infra/types.py
# Shared data types used across ingestion, retrieval, memory, and cache modules.
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A single catalog chunk returned by retrieval."""
    id: str           # e.g. "p001_identity"
    text: str         # the text that was embedded
    metadata: dict = field(default_factory=dict)
