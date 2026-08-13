# ShopBot Training — Embedding Model Lifecycle (Book 3)

> Part of the ShopBot project. Read `../CLAUDE.md` first for the operating principle,
> the book ↔ code chapter map, and how this project relates to `../shopbot-agent/`,
> `../shopbot-ingest/`, and `../shopbot-rerank/`. This file covers only the offline
> model training + export pipeline.

Do not guess, speculate, or fill gaps with assumptions. Every constant and design choice
here traces to a chapter documented in `../CLAUDE.md`'s Chapter Map. If you cannot cite
the chapter, do not write the line.

---

## 1. What This Project Does

Builds the fine-tuned, ONNX-quantised embedding model that `../shopbot-rerank/` serves
at `/embed`. Runs offline, by hand, rarely — not a long-running service, not part of any
request path. Two stages:

1. **Fine-tune** (`fine_tune/`, Ch. 5) — `BAAI/bge-small-en-v1.5` fine-tuned on the zUdyog
   catalog via triplet loss. Requires GPU.
2. **Export** (`export/`, Ch. 6) — the fine-tuned model quantised to ONNX INT8.

**This is not a required runtime dependency of anything.** `../shopbot-rerank/` only needs
this project's *output* (the `models/` directory), copied in before its Docker image is
built — see Section 4. Nothing calls this project's code at request time or imports it.

**Why a fourth standalone project, not folded into `../shopbot-rerank/` or
`../shopbot-ingest/`:** the served inference container should carry zero training-only
dependencies (`openai`, `qdrant-client`, GPU `torch`, `optimum`) or credentials near it —
`../shopbot-rerank/`'s Dockerfile already only installs inference libraries. Keeping this
project standalone means its `requirements.txt`/`.env`/venv are entirely separate from
the serving side, matching `../shopbot-ingest/`'s "own deps, own env, builds its own
clients" pattern rather than `../shopbot-rerank/`'s "stateless, no config" pattern.

Fully standalone: no imports from, or into, any sibling project. `clients.py` and
`chunk_types.py` duplicate the small pieces this project needs (OpenAI/Qdrant client
construction, the `Chunk` dataclass) rather than importing across projects — same
reasoning as `../shopbot-ingest/`.

---

## 2. File Tree

```
shopbot-training/
├── clients.py                 ← Minimal OpenAI + Qdrant clients (standalone, own construction)
├── chunk_types.py              ← Chunk dataclass (duplicated from ../shopbot-agent/infra/types.py)
│
├── fine_tune/                 ← Ch. 5 — embedding model fine-tuning
│   ├── __init__.py
│   ├── catalog_store.py        ← Fetch chunks from Qdrant for triplet construction
│   ├── build_dataset.py        ← build_triplets(): labeled queries → ~3,400 triplets
│   └── train.py                 ← TripletLoss; 4 epochs; saves to models/bge-small-zudyog-v1/
│
├── export/                    ← Ch. 6 — ONNX export
│   └── to_onnx_int8.py          ← FP32 export via Optimum → INT8 dynamic quantisation
│
├── models/                    ← NOT committed to git (large binaries) — build output lands here
│   ├── bge-small-zudyog-v1/              ← fine-tuned PyTorch model (Ch. 5) — ~130 MB
│   ├── bge-small-zudyog-v1-onnx/         ← ONNX FP32 intermediate (Ch. 6) — ~135 MB
│   └── bge-small-zudyog-v1-onnx-int8/   ← ONNX INT8 — 33 MB, ~2 ms/call (Ch. 6) ← ACTIVE
│
├── requirements.txt
├── .env                        ← Never commit
└── .env.example
```

---

## 3. Data Flow

```
../shopbot-agent/evaluation/labeled_dataset.jsonl  (read via relative sibling path)
    │
fine_tune/build_dataset.py  build_triplets()
    │  seed query → 8 LLM paraphrases (clients.py:llm_small)
    │  + hard-negative sampling from Qdrant (fine_tune/catalog_store.py, clients.py:qdrant_client)
    ▼
fine_tune/train.py
    │  TripletLoss, margin=0.3, 4 epochs, batch_size=16 (GPU, ~38 min on A100)
    ▼
models/bge-small-zudyog-v1/          (PyTorch)
    │
export/to_onnx_int8.py
    │  Step 1: ONNX FP32 export (Optimum ORTModelForFeatureExtraction)
    │  Step 2: INT8 dynamic quantisation (AutoQuantizationConfig.avx512_vnni)
    ▼
models/bge-small-zudyog-v1-onnx-int8/model_quantized.onnx   (~33 MB)
    │
    │  ── manual copy step, crosses the project boundary ──
    ▼
../shopbot-rerank/models/bge-small-zudyog-v1-onnx-int8/
    (baked into that project's Docker image at build time — see Section 4)
```

The `DATASET_PATH` in `fine_tune/build_dataset.py` reads
`../shopbot-agent/evaluation/labeled_dataset.jsonl` — the same dataset RAGAS Monday scores
against. This is the one place this project reads a sibling's file directly, rather than
through an API or a copied artifact; fine-tuning is manual and infrequent enough that a
relative path is acceptable (documented here per Section 0's divergence rule, since it's
the one exception to "no cross-project coupling" in Section 1).

---

## 4. Handoff to `../shopbot-rerank/` — the artifact boundary

This project and `../shopbot-rerank/` are not connected by an import or an HTTP call —
only by a **file copy**, done by hand (or by a build script, if automated later):

```bash
# After export/to_onnx_int8.py completes:
cp -r models/bge-small-zudyog-v1-onnx-int8 ../shopbot-rerank/models/
# Also provide models/cross-encoder/ — export the HF cross-encoder checkpoint the same way
# (see ../shopbot-rerank/CLAUDE.md Section 4 for the exact model name/version).

cd ../shopbot-rerank
docker build -t shopbot-rerank .   # bakes models/ into the image at build time
```

Models are baked in at Docker build time, not fetched at container startup — this is a
deliberate choice from Ch. 6 (cold-start latency: pre-warmed image vs. a runtime download).
It means `../shopbot-rerank/` never needs network access to this project, Qdrant, or
OpenAI at runtime — it's fully self-contained and stateless.

---

## 5. Run Order

```bash
# 1 — Create virtual environment (once)
python -m venv venv && source venv/bin/activate

# 2 — Install dependencies
pip install -r requirements.txt
# Training requires a real (GPU) torch build, not the CPU-only wheel
# ../shopbot-rerank/'s Dockerfile uses — install torch per your GPU/CUDA setup.

# 3 — Set env vars
cp .env.example .env
# Fill in: OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY

# 4 — Prerequisites
#     - ../shopbot-agent/evaluation/labeled_dataset.jsonl has ≥100 labeled queries
#     - ../shopbot-ingest/ has populated Qdrant
#     - Log estimated cost in ../costs/cost_log.md before starting (GPU + OpenAI calls)

# 5 — Fine-tune (GPU; ~38 min on A100)
python -m fine_tune.train

# 6 — Export to ONNX INT8
python export/to_onnx_int8.py

# 7 — Hand off to ../shopbot-rerank/ — see Section 4

# 8 — In ../shopbot-ingest/: drop and recreate Qdrant collections at 384-dim, re-ingest
```

---

## 6. Rules for Future Changes

1. **Do not import from `../shopbot-agent`, `../shopbot-ingest`, or `../shopbot-rerank`.**
   The one sanctioned cross-project coupling is the `DATASET_PATH` file read (Section 3)
   and the `models/` copy handoff (Section 4) — both documented, both file-level, neither
   a Python import or a live call.
2. **`AutoQuantizationConfig.avx512_vnni` requires AVX-512 VNNI on this (export) machine
   only.** The exported `model_quantized.onnx` runs on any CPU — `../shopbot-rerank/`'s
   serving machine does not need this instruction set. On ARM or older x86, swap it for
   an appropriate preset here.
3. **Re-run fine-tuning after significant catalog changes.** The model is catalog-specific
   (`bge-small-zudyog-v1`) — new products or attributes in `../shopbot-ingest/data/products.py`
   are not reflected until this pipeline runs again.
4. **Log cost before every GPU run.** Fine-tuning is ~₹240 in compute per run; log it in
   `../costs/cost_log.md` alongside the OpenAI paraphrase-generation cost.
