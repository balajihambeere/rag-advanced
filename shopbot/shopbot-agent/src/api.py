# src/api.py
# Source: Book 2, Chapters 2–9 (pipeline); Book 3, Chapter 4 + Chapter 9 (wiring)
# Book 3 API endpoint — LangGraph pipeline replaces the Book 2 chain.
# Cache (Ch. 7 B2) wraps the pipeline; session memory (Ch. 6 B2) is carried through.
#
# Run this file to serve the Book 3 system: python src/api.py
# The /health and /ask routes mirror Book 1+2 for drop-in compatibility.

from fastapi import FastAPI
from pydantic import BaseModel, field_validator
from contextlib import asynccontextmanager
import re
import uvicorn

from cache.wrapper import answer_with_cache
from memory.session import load_session, save_session, Turn
from memory.update import push_turn, maybe_refresh_summary, extract_mentioned_skus

# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cross-encoder reranking AND dense embedding (Ch. 4/6) always run in the
    # standalone ../shopbot-rerank/ service — a separate project, run via local
    # Docker in dev, same as production. RERANK_URL is required —
    # retrieval/rerank_client.py and infra/clients.py raise KeyError at import
    # time if it's unset, so a missing env var fails before this even runs.
    # Here we additionally confirm the service is actually reachable, so
    # "forgot to `docker run` the rerank container" fails at startup with a
    # clear error instead of on the first customer's /ask request.
    import httpx
    from retrieval.rerank_client import RERANK_URL
    try:
        httpx.get(f"{RERANK_URL}/health", timeout=5.0).raise_for_status()
    except httpx.HTTPError as e:
        raise RuntimeError(
            f"Rerank/inference service unreachable at {RERANK_URL} — start it "
            f"first (../shopbot-rerank/: docker build -t shopbot-rerank . && "
            f"docker run -p 8001:8001 shopbot-rerank). Cause: {e}"
        ) from e

    # Compile the LangGraph graph once at startup.
    # Graph compilation per-request adds latency. See CLAUDE.md Section 19, Rule 6.
    from pipeline.graph import pipeline  # noqa: triggers graph compilation

    import os
    _mlflow_uri = os.getenv("MLFLOW_TRACKING_URI")
    if _mlflow_uri:
        try:
            import mlflow
            import mlflow.openai
            mlflow.set_tracking_uri(_mlflow_uri)
            mlflow.set_experiment("shopbot-eval")
            mlflow.openai.autolog()
            print(f"  MLflow tracing → {_mlflow_uri}  (experiment: shopbot-eval)")
        except Exception as e:
            print(f"  MLflow tracing skipped: {e}")

    print("ShopBot v3 ready (LangGraph · HyDE · CRAG · rerank/embed via shopbot-rerank).")
    yield


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ShopBot API",
    description="Book 3 production pipeline — LangGraph + HyDE + CRAG + fine-tuned ONNX embedder",
    version="3.0.0",
    lifespan=lifespan,
)


# ── Request / Response Models ─────────────────────────────────────────────────
class QuestionRequest(BaseModel):
    question:   str
    session_id: str = "default"

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        v = v.replace("‘", "'").replace("’", "'")   # smart single quotes
        v = v.replace("“", '"').replace("”", '"')   # smart double quotes
        v = v.replace("—", " - ")                        # em dash
        v = v.replace("​", "")                           # zero-width space

        if not v:
            raise ValueError("Question cannot be empty.")
        if len(v) > 500:
            raise ValueError(f"Question too long ({len(v)} chars). Maximum is 500.")

        injection_patterns = [
            r"ignore\s+(all\s+)?previous\s+instructions",
            r"you\s+are\s+now\s+",
            r"act\s+as\s+",
            r"system\s+prompt",
            r"forget\s+(everything|all)",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Invalid question format.")
        return v


class AnswerResponse(BaseModel):
    answer:     str
    session_id: str


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ShopBot", "version": "3.0.0"}


@app.post("/ask", response_model=AnswerResponse)
def ask_shopbot(payload: QuestionRequest):
    session = load_session(payload.session_id)

    # Book 3 pipeline: LangGraph graph replaces the flat Book 2 chain.
    # The cache wrapper (Book 2 Ch. 7) still wraps the pipeline for
    # exact and semantic cache layers — hit rate ~28% at campaign volume.
    answer, retrieved, _ = answer_with_cache(payload.question, session)

    mentioned_skus = extract_mentioned_skus(retrieved)
    push_turn(session, Turn(role="user",      content=payload.question), mentioned_skus)
    push_turn(session, Turn(role="assistant", content=answer),           [])
    maybe_refresh_summary(session, session.recent_turns)
    save_session(session)

    return AnswerResponse(answer=answer, session_id=payload.session_id)


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8000
    print("ShopBot v3 API starting...")
    print(f"  API:     http://localhost:{port}")
    print(f"  Swagger: http://localhost:{port}/docs")
    print(f"  Health:  http://localhost:{port}/health")
    uvicorn.run("src.api:app", host=host, port=port, reload=True)
