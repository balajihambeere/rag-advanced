# clients.py
# Minimal client construction for fine_tune/ (offline model training/export
# tooling only — the served main.py needs no clients at all, it's stateless).
# Standalone: this project does not import ../shopbot-agent/infra/clients.py,
# mirroring ../shopbot-ingest/'s pattern of building clients inline rather than
# sharing a module across sibling projects.

import os
from openai import OpenAI
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()

_openai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


class _LLM:
    """Thin wrapper over chat.completions — mirrors ../shopbot-agent/infra/clients.py's _LLM."""

    def __init__(self, model: str, temperature: float = 0):
        self.model = model
        self.temperature = temperature

    def complete(
        self,
        *,
        system: str | None = None,
        user: str | None = None,
        prompt: str | None = None,
        max_tokens: int = 800,
    ) -> str:
        if prompt is not None and system is None and user is None:
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            if user:
                messages.append({"role": "user", "content": user})
        resp = _openai.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=max_tokens,
            messages=messages,
        )
        return resp.choices[0].message.content


llm_small = _LLM("gpt-4o-mini", temperature=0)

qdrant_client = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
)
