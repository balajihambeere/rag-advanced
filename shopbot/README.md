# ShopBot — RAG Product Assistant for zUdyog Fashion

A production-ready RAG chatbot built from *RAG Essentials* (Books 1–3) using the
Pramana Framework — every answer traces to retrieved product text, not LLM training weights.

Five applications work together: four standalone Python backends (**shopbot-ingest**,
**shopbot-agent**, **shopbot-rerank**, **shopbot-training**) and a **Next.js frontend**
(zUdyog Fashion store).

---

## Architecture (Book 3)

```
shopbot-ingest/     ← Build-time: chunk + embed + write catalog to Qdrant   (no server)
shopbot-agent/       ← FastAPI RAG backend — the /ask endpoint              (port 8000)
shopbot-rerank/       ← Cross-encoder + ONNX embedder microservice          (port 8001)
shopbot-training/       ← Offline: fine-tune + export the embedding model   (no server;
                            hands a models/ directory to shopbot-rerank, by hand, rarely)
zudyog-fashion/           ← Next.js storefront + chat widget                (port 3000)
```

**Request-time pipeline** (`shopbot-agent`, every `/ask` call):

```
POST /ask
  → session memory load (Redis)
  → three-layer cache (exact → semantic → full pipeline)
  → LangGraph pipeline:
      classify_vague_node → [HyDE | standard hybrid retrieve] → crag_judge_node
        → generate_node | re_retrieve_node → generate_node | fallback_node
    (rerank + embed inside retrieval: HTTP calls to shopbot-rerank)
  → cache write + session update
```

See each project's own `CLAUDE.md` for full detail; `CLAUDE.md` at this level is the
chapter map and the "why split this way" rationale.

---

## Prerequisites

- Python 3.11+
- Node.js 18+ (frontend only)
- Docker (for `shopbot-rerank`)
- **OpenAI API key** — LLM (`gpt-4o-mini`); `shopbot-ingest` also uses it for batch embedding
- **Qdrant Cloud cluster** — free tier, GCP asia-south1 (Mumbai) — [cloud.qdrant.io](https://cloud.qdrant.io)
- **Redis instance** — free tier works — [app.redislabs.com](https://app.redislabs.com)
- **GPU** — only needed once, to fine-tune the embedding model (`shopbot-training/fine_tune/train.py`)

---

## Quickstart

```bash
# 1 — Build the catalog (once; re-run whenever the product data changes)
cd shopbot-ingest
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env               # OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY
python -m infra.qdrant_setup && python -m ingestion.dual_write && python -m ingestion.bm25_backfill

# 2 — Fine-tune + export the embedding model (one-time; re-run only if the model needs retraining)
cd ../shopbot-training
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env               # OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY
python -m fine_tune.train          # ~38 min on GPU; produces models/bge-small-zudyog-v1/
python export/to_onnx_int8.py      # produces models/bge-small-zudyog-v1-onnx-int8/

# 3 — Hand the model to shopbot-rerank, then start it (required — no in-process fallback)
cd ../shopbot-rerank
cp -r ../shopbot-training/models/bge-small-zudyog-v1-onnx-int8 models/
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2').save('models/cross-encoder')"
docker build -t shopbot-rerank . && docker run -p 8001:8001 shopbot-rerank

# 4 — Start the backend (separate terminal)
cd ../shopbot-agent
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env               # + REDIS_URL, RERANK_URL=http://localhost:8001
uvicorn src.api:app --host 0.0.0.0 --port 8000   # → http://localhost:8000/docs

# 5 — Start the frontend (separate terminal)
cd ../zudyog-fashion
npm install && npm run dev          # → http://localhost:3000
```

Each project's `.env.example` documents the environment variables it needs (`shopbot-rerank`
needs none — it's stateless). Steps 1–3 are one-time (re-run 1 after catalog changes,
re-run 2–3 only if the embedding model needs retraining); steps 4–5 are what you run day
to day.

**Quick test** (once `shopbot-agent` is up):

```bash
curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "What can I wear to a small office party in the evening?", "session_id": "demo"}'
```

`session_id` enables multi-turn memory (Book 2, Chapter 6). Use any string; omit it for
the default session.

---

## Evaluation (Book 2 Ch. 8 + Book 3 Ch. 7)

```bash
cd shopbot-agent
# Validate one case before running the full labeled set — avoids wasting API cost on a crash
python -c "
from evaluation.evaluate import answer_for_eval
a, chunks = answer_for_eval('Does the silk saree come with a blouse?')
print(a)
print(f'{len(chunks)} chunks retrieved')
"

# Full four-dimension RAGAS evaluation
python -m evaluation.evaluate

# Per-route slicing (Book 3, Ch. 7)
python -m evaluation.per_route
```

Book 3 milestones: F=0.91 (post-campaign, blended) · see `CLAUDE.md` Section 1 for the
full per-chapter and per-route tables. Book 1 baseline: F=0.7494 · CP=0.6417.

---

## Load Test (Book 2 Ch. 9, re-run Book 3 Ch. 8)

```bash
cd shopbot-agent
python -m loadtest.harness --qpm 10 --duration 60     # safe starting point
python -m loadtest.harness --qpm 600 --duration 60     # Book 3 campaign-load test
```

---

## Deploy

**shopbot-agent (Railway):**

```bash
cd shopbot-agent
npm install -g @railway/cli
railway login
railway up
```

Set env vars in Railway's dashboard per `shopbot-agent/.env.example`. Railway reads
`Procfile`: `web: uvicorn src.api:app --host 0.0.0.0 --port $PORT`.

**shopbot-rerank:** deploy the Docker image built in Quickstart Step 3 — 3 replicas
recommended under campaign load (≥400 qpm).

**Frontend:** deploy `zudyog-fashion/` to Vercel. Set `SHOPBOT_API_URL` to your Railway
backend URL.

---

## Re-ingestion (after catalog changes)

```bash
cd shopbot-ingest
python -m ingestion.dual_write --force   # re-embed and dual-write all chunks
python -m ingestion.bm25_backfill        # re-populate BM25 sparse vectors
```

`--force` bypasses the "already indexed" check. Required whenever `data/products.py` changes.
