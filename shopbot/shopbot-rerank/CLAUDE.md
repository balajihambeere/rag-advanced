# ShopBot Rerank — Standalone Inference Microservice (Book 3)

> Part of the ShopBot project. Read `../CLAUDE.md` first for the operating principle,
> the book ↔ code chapter map, and how this project relates to `../shopbot-agent/`,
> `../shopbot-ingest/`, and `../shopbot-training/`. This file covers only the served
> inference microservice.

Do not guess, speculate, or fill gaps with assumptions. Every constant and design choice
here traces to a chapter documented in `../CLAUDE.md`'s Chapter Map. If you cannot cite
the chapter, do not write the line.

---

## 1. What This Project Does

A FastAPI service combining two models in one container: a cross-encoder for reranking
(`/rerank`, Book 2 Ch. 9) and a fine-tuned ONNX INT8 embedder (`/embed`, Book 3 Ch. 6).
Both are CPU-bound and the main latency contributors under load — this project exists so
they can be deployed, scaled, and resourced independently of `../shopbot-agent`'s API
process.

**This is a required dependency of `../shopbot-agent`, not optional.** `shopbot-agent` has
no in-process cross-encoder or ONNX embedder and no fallback (see
`../shopbot-agent/retrieval/rerank_client.py` and `infra/clients.py:embed()`) — it calls
this service over HTTP for every rerank and every embedding, in every environment
including local dev.

**Stateless and self-contained at runtime:** no env vars, no database connection, no
external API calls. The model files are baked into the Docker image at build time — this
service never needs network access to Qdrant, OpenAI, or any sibling project once running.

**Does not own model training.** `../shopbot-training/` builds the fine-tuned ONNX model
this service serves — see Section 4 for how that artifact crosses the project boundary.
Splitting it out (rather than folding fine-tuning into this project, which is where it
initially lived during the ingest/agent/rerank split) keeps this service's dependency
surface to inference-only libraries, with no training-only deps (`openai`, `qdrant-client`,
GPU `torch`, `optimum`) or credentials anywhere near the served container.

**Superseded `services/rerank/` from Book 2:** the pre-split checkout had two
rerank-shaped services — the Book 2 leftover `services/rerank/` (cross-encoder only) and
`services/inference/` (this project's origin, cross-encoder + ONNX embedder). The former
was already dead code (CLAUDE.md called it superseded; nothing referenced it) and was
dropped during the split rather than carried forward.

Fully standalone: no imports from, or into, any sibling project. The only coupling is the
HTTP contract below (with `../shopbot-agent`) and the `models/` file handoff (with
`../shopbot-training/`).

---

## 2. File Tree

```
shopbot-rerank/
├── main.py               ← FastAPI app: /health, /rerank, /embed
├── onnx_embedder.py       ← ONNXEmbedder: ONNX session + tokenizer; mean-pool + L2 normalize
├── Dockerfile             ← python:3.11-slim; CPU torch + onnxruntime; pre-warms both models
├── requirements.txt
│
└── models/                ← NOT committed to git — copied in from ../shopbot-training/
    ├── cross-encoder/                     ← cross-encoder/ms-marco-MiniLM-L-6-v2 checkpoint
    └── bge-small-zudyog-v1-onnx-int8/    ← 33 MB, ~2 ms/call (Book 3 Ch. 6) ← ACTIVE
```

No `.env` — this service takes no configuration; model paths and the port are constants
in `main.py`.

---

## 3. HTTP Contract

**Port:** 8001 (fixed — matches `../shopbot-agent/.env.example`'s default `RERANK_URL`).
Note: the pre-split `services/inference/main.py` bound port 8000, colliding with
`../shopbot-agent`'s own port — that was a bug, fixed during the split, not a design change.

| Method | Path | Request | Response |
|--------|------|---------|----------|
| GET | `/health` | — | `{"status": "ok", "service": "inference", "version": "3.0.0"}` |
| POST | `/rerank` | `{"query": str, "candidates": [{"id": str, "text": str}], "top_k": int}` | `{"ranked_ids": [str], "scores": [float]}` |
| POST | `/embed` | `{"text": str}` | `{"embedding": [float], "dim": int}` |

`ranked_ids`/`scores` are sorted descending by score, truncated to `top_k`. Callers that
need scores for the *full* candidate set — `../shopbot-agent`'s `memory_aware.py`
boost/floor logic does — pass `top_k=len(candidates)` to get everything back. See
`../shopbot-agent/retrieval/rerank_client.py` for both call shapes.

---

## 4. Models

### Cross-encoder (Book 2, Ch. 4)

```python
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
```

~22M params, CPU inference, ~50ms per 20 candidates per query.

### Embedder (Book 3, Ch. 5+6) — built by `../shopbot-training/`, served here

**Base model:** `BAAI/bge-small-en-v1.5`, fine-tuned on the zUdyog catalog, exported to
ONNX INT8 — 384-dim, ~2ms p50 (vs ~122ms for the Book 2 OpenAI API), ₹0/query.
Full training/export detail (triplet loss, RAGAS comparison across each stage) lives in
`../shopbot-training/CLAUDE.md` — this project only serves the finished artifact.

**Dimensions:** 384 (down from Book 2's 1536, `text-embedding-3-small`). Every Qdrant
collection `../shopbot-ingest/` and `../shopbot-agent/` touch must be 384-dim — see
`../shopbot-ingest/CLAUDE.md` Section 7 for the pre-existing dimension-mismatch issue
this split did not resolve.

Both models are loaded once at process start and pre-warmed again at Docker **build**
time (`RUN python -c "..."` in the `Dockerfile`), so the image ships with both already
cached — the container's first request has no cold-start.

---

## 5. Receiving the model from `../shopbot-training/`

This project does not build its own model — it only serves whatever's copied into
`models/` before the Docker image is built:

```bash
# After ../shopbot-training/'s fine-tune + export pipeline completes:
cp -r ../shopbot-training/models/bge-small-zudyog-v1-onnx-int8 models/
# Cross-encoder checkpoint (unchanged from Book 2 — export once, reuse):
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2').save('models/cross-encoder')"
```

Without `models/` populated, `docker build` fails at the pre-warm `RUN` steps — this is
expected until `../shopbot-training/`'s pipeline has been run at least once.

---

## 6. Run Order

```bash
# 1 — Ensure models/ is populated — see Section 5
docker build -t shopbot-rerank .

# 2 — Run (port 8001, matches ../shopbot-agent/.env.example's default RERANK_URL)
docker run -p 8001:8001 shopbot-rerank

# 3 — Verify
curl http://localhost:8001/health
```

Start this **before** `../shopbot-agent`'s API — its startup lifespan pings
`{RERANK_URL}/health` and refuses to start if this isn't reachable.

**Local dev without Docker** (not the primary path):
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

---

## 7. Scaling (Ch. 8)

`--workers 2` in the Dockerfile CMD; 3 replicas recommended at ≥400 qpm campaign load
(600 qpm / 3 replicas: ~42% CPU per replica on the cross-encoder path). Stateless — no
session, no cache, no database connection — so any replica can answer any request.
`../shopbot-agent/loadtest/harness.py` exercises the full `../shopbot-agent` → this
service path end to end.

---

## 8. Rules for Future Changes

1. **Keep the HTTP contract in sync with `../shopbot-agent/retrieval/rerank_client.py`
   and `infra/clients.py:embed()`.** `rerank_remote()`, `rerank_scores_remote()`
   (`top_k=len(candidates)`), and `embed()` all depend on the exact request/response
   shapes in Section 3.
2. **Do not add imports from any sibling project, and do not add training-only
   dependencies here.** If the model needs retraining, that happens in
   `../shopbot-training/`; this project only ever receives the finished `models/` files.
3. **If the cross-encoder model changes**, update the constant in `main.py`, the
   `Dockerfile`'s build-time pre-warm command, and re-validate against
   `../shopbot-agent/CLAUDE.md`'s known-issues section (calibrated against
   `ms-marco-MiniLM-L-6-v2` specifically).
4. **Do not accept a model below 384-dim without updating both sibling projects in
   lockstep.** Mixing dimensions in the same Qdrant collection silently corrupts retrieval.
5. **The inference container needs 3 replicas under campaign load (≥400 qpm).** 2 is
   sufficient for normal traffic — scale before a campaign, not during.
