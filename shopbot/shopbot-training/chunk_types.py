# chunk_types.py
# Standalone copy of ../shopbot-agent/infra/types.py's Chunk dataclass — only
# fine_tune/ needs it (to build training triplets from Qdrant chunks), and it's
# small enough that duplicating it beats a cross-project import.
# Named chunk_types.py, not types.py, to avoid shadowing the stdlib `types`
# module once this directory is added to sys.path (fine_tune/*.py do this).
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A single catalog chunk, as returned by Qdrant."""
    id: str           # e.g. "p001_identity"
    text: str         # the text that was embedded
    metadata: dict = field(default_factory=dict)
