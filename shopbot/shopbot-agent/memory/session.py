# memory/session.py
# Source: Book 2, Chapter 6 — ShopBot Finally Remembers
# Redis-backed session: last 3 verbatim turns + rolling 2-sentence summary +
# list of up to 3 active SKUs (products discussed most recently).
#
# TTL: 24 hours per session. Sessions are keyed by session_id (passed in from
# the API — matches the session_id already tracked in Book 1's QuestionRequest).

import json
import os
from dataclasses import dataclass, field, asdict
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Turn:
    role: str      # "user" | "assistant"
    content: str


@dataclass
class Session:
    session_id: str
    recent_turns: list[Turn] = field(default_factory=list)   # last 3 verbatim
    summary: str = ""                                         # rolling, 2 sentences
    active_skus: list[str] = field(default_factory=list)     # most-recent 3 SKUs

    def key(self) -> str:
        return f"session:{self.session_id}"


def _get_redis():
    import redis
    return redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


def load_session(session_id: str) -> Session:
    try:
        r = _get_redis()
        raw = r.get(f"session:{session_id}")
        if not raw:
            return Session(session_id=session_id)
        data = json.loads(raw)
        data["recent_turns"] = [Turn(**t) for t in data["recent_turns"]]
        return Session(**data)
    except Exception:
        # If Redis is unavailable, return an empty session — stateless fallback
        return Session(session_id=session_id)


def save_session(s: Session) -> None:
    try:
        r = _get_redis()
        r.setex(s.key(), 60 * 60 * 24, json.dumps(asdict(s)))
    except Exception:
        pass  # Non-fatal — session is lost but the response still goes out
