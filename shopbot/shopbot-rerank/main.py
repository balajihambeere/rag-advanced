# main.py
# Source: Book 3, Chapter 6 — Eight Bits Per Number; the ingest/agent/rerank split
# Standalone combined inference service — its own project, not a subfolder of
# ../shopbot-agent/. Cross-encoder reranking (Book 2 Ch. 9) + ONNX INT8
# embedding (Book 3 Ch. 6), both in one container. The model files this service
# serves are trained/exported entirely in ../shopbot-training/ and copied into
# models/ before the Docker image is built — this project only ever serves them.
#
# Two models, 280 MB total, one CPU box, no GPU.
# Cross-encoder serves /rerank; ONNX embedder serves /embed.
# Both models are pre-warmed at startup (see Dockerfile CMD).
#
# ../shopbot-agent/ calls this over HTTP only (retrieval/rerank_client.py,
# infra/clients.py:embed()) and has no in-process fallback for either.
#
# Scale: 3 replicas recommended at ≥400 qpm campaign load (Ch. 8).
# At 600 qpm / 3 replicas: ~42% CPU per replica on the cross-encoder path.

from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import CrossEncoder
from onnx_embedder import ONNXEmbedder

RERANK_MODEL  = "cross-encoder/ms-marco-MiniLM-L-6-v2"
EMBED_MODEL   = "models/bge-small-zudyog-v1-onnx-int8"

reranker = CrossEncoder(RERANK_MODEL, max_length=512)
embedder = ONNXEmbedder(EMBED_MODEL)

app = FastAPI(title="ShopBot Inference Service", version="3.0.0")


# ── Health ──────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "inference", "version": "3.0.0"}


# ── Rerank ───────────────────────────────────────────────────────────────────
class RerankRequest(BaseModel):
    query:      str
    candidates: list[dict]   # [{"id": str, "text": str}]
    top_k:      int = 3


class RerankResponse(BaseModel):
    ranked_ids: list[str]
    scores:     list[float]


@app.post("/rerank", response_model=RerankResponse)
def rerank(req: RerankRequest) -> RerankResponse:
    if not req.candidates:
        return RerankResponse(ranked_ids=[], scores=[])
    pairs  = [(req.query, c["text"]) for c in req.candidates]
    scores = reranker.predict(pairs).tolist()
    ranked = sorted(zip(req.candidates, scores), key=lambda p: -p[1])
    top    = ranked[:req.top_k]
    return RerankResponse(
        ranked_ids=[c["id"] for c, _ in top],
        scores=[round(s, 4) for _, s in top],
    )


# ── Embed ─────────────────────────────────────────────────────────────────────
class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    embedding: list[float]
    dim:       int


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    vec = embedder.encode(req.text, normalize=True).tolist()
    return EmbedResponse(embedding=vec, dim=len(vec))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, workers=2)
