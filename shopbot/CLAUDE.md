# ShopBot — Project Bible (Book 3)

> **This file is the single source of truth for every decision in this project.**
> Every constant, every design choice, every known issue traces to a specific chapter
> of the *RAG Essentials* series. Nothing is guessed. Nothing is approximated.
> Before changing any file, find the relevant section here first.
> Before adding anything new, find the chapter that authorises it.

---

## 0. Two-Way Sync — The Operating Principle

The book and the code are two representations of the same truth.
They must stay in perfect sync in **both directions** at all times.

### Book → Code

Every piece of code traces to a specific chapter or Appendix A section.
Before writing or changing any file: read the chapter that owns it from `book-3/`.
No constant, design decision, or architectural choice exists without a
book citation. If you cannot cite the chapter, you do not write the line.

### Code → Book

Every piece of code that exists is verifiable against the book text.
When they diverge, the divergence is documented explicitly with evidence
from both sides — not silently corrected in either direction.
CLAUDE.md must reflect what the code actually does right now, not what
was intended or remembered.

### Full Awareness — Complete Presence

Do not write from memory of what the chapter said.
Do not write from memory of what the code said.
Read both. Then write. After writing, verify both directions.

### The Bidirectional Check (before closing any task)

| Direction | Question | Must be |
|-----------|----------|---------|
| Book → Code | Does this code implement exactly what the book says? Can I cite the chapter? | Yes |
| Code → Book | Does CLAUDE.md reflect exactly what the code does right now, with no gaps or stale claims? | Yes |

Both must be yes. If either is no, the task is not complete.

---

## 1. What This Project Is

ShopBot is a production-ready RAG product assistant for **zUdyog Fashion**, an Indian
fashion e-commerce store. It follows the **Pramana Framework**: every answer traces to
retrieved product text, not to LLM training weights.

**Book 1** built the Grounding Layer: ChromaDB, attribute-level chunking, threshold-gated
retrieval at 0.75 cosine similarity, a constrained system prompt (V4), FastAPI endpoint,
and a 20-query RAGAS baseline (Faithfulness 0.7494, Context Precision 0.6417).

**Book 2** replaced ChromaDB with Qdrant Cloud, added hybrid search (dense + BM25 via
RRF), cross-encoder reranking, structured session memory (Redis), a three-layer cache,
and expanded RAGAS to all four dimensions. Book 2 ended with the system at 91% success
on seven-thousand-queries-a-day campaign traffic, and split its codebase into three
standalone sibling projects — see Section 2.

**Book 3** starts from the 9% that remained — sorted by hand from the failed-query log
into four distinct failure categories. Each fix changed the *shape* of the pipeline
rather than adding another component to the existing chain.

### Book 2 final baseline (Book 3 starting point — run_book2_final)

| Metric | Score | Notes |
|--------|-------|-------|
| Faithfulness | 0.84 | |
| Answer Relevance | 0.83 | |
| Context Precision | 0.88 | |
| Context Recall | 0.81 | |

### Book 3 per-chapter RAGAS milestones (Bible-locked)

| After chapter | F | AR | CP | CR | Notes |
|---------------|---|----|----|----|-------|
| Ch. 2 — HyDE deployed | 0.85 | 0.85 | 0.88 | 0.83 | vague-query routing |
| Ch. 3 — CRAG deployed | 0.88 | 0.87 | 0.87 | 0.85 | Bible-locked CRAG target |
| Ch. 4 — LangGraph | 0.88 | 0.87 | 0.87 | 0.85 | refactor only — numbers unchanged |
| Ch. 5 — fine-tuned bge-small | 0.88 | 0.88 | 0.91 | 0.86 | Bible-locked fine-tune target met |
| Ch. 6 — ONNX INT8 | 0.88 | 0.87 | 0.90 | 0.85 | −1 CP for 5× latency gain |
| Ch. 8 — post-campaign (blended F) | **0.91** | — | — | — | 38K qpd; p50 280 ms |

### Per-route RAGAS (Book 3 final, week 10 post-campaign)

| Route | n | F | AR | CP | CR |
|-------|---|---|----|----|----|
| A · standard, RELEVANT | 51 | 0.92 | 0.90 | 0.94 | 0.89 |
| B · standard, PARTIAL | 20 | 0.86 | 0.85 | 0.85 | 0.81 |
| C · HyDE, RELEVANT | 22 | 0.93 | 0.92 | 0.94 | 0.92 |
| D · HyDE, PARTIAL | 13 | 0.86 | 0.86 | 0.87 | 0.81 |
| E · fallback | 11 | n/a | n/a | n/a | n/a |

---

## 2. Four Projects, One Pipeline

The codebase is split into four standalone projects — each with its own dependency
manifest, `.env` (where applicable), and `CLAUDE.md`. None imports another; they
communicate only over HTTP (`shopbot-agent` ↔ `shopbot-rerank`), through the Qdrant
collections (`shopbot-ingest` ↔ `shopbot-agent`), or through a one-time file copy
(`shopbot-training` → `shopbot-rerank`, see Section 2's last bullet).

| Project | Role | Detailed doc |
|---------|------|-------------|
| **`shopbot-ingest/`** | Build-time: reads `data/products.py`, chunks it, embeds it, writes it to ChromaDB + Qdrant (dense + BM25). Run once, and re-run whenever the catalog changes. | [`shopbot-ingest/CLAUDE.md`](shopbot-ingest/CLAUDE.md) |
| **`shopbot-agent/`** | Request-time: the FastAPI service (`/ask`) — session memory, three-layer cache, LangGraph pipeline (HyDE/CRAG routing), reranking + embedding (via HTTP to `shopbot-rerank`), LLM answering. Also owns evaluation (RAGAS, per-route) and load testing. | [`shopbot-agent/CLAUDE.md`](shopbot-agent/CLAUDE.md) |
| **`shopbot-rerank/`** | A required dependency of `shopbot-agent`: a standalone, stateless inference microservice (`/rerank` + `/embed`) — cross-encoder reranking and the fine-tuned ONNX INT8 embedder, combined in one container. No in-process fallback exists in `shopbot-agent` for either. Carries no training-only dependencies or credentials — it only ever serves a `models/` directory it receives from `shopbot-training`. | [`shopbot-rerank/CLAUDE.md`](shopbot-rerank/CLAUDE.md) |
| **`shopbot-training/`** | Offline, one-time, by-hand: fine-tunes the embedding model on the catalog and exports it to ONNX INT8 (Book 3 Ch. 5+6). Not a runtime dependency of anything — nothing imports it or calls it at request time. Its output is copied into `shopbot-rerank/models/` before that project's Docker image is built. | [`shopbot-training/CLAUDE.md`](shopbot-training/CLAUDE.md) |

This mirrors Book 2's split (project names, HTTP-only coupling, no in-process fallback for
`shopbot-agent` ↔ `shopbot-rerank`), brought forward into Book 3's checkout — which had
continued from Book 1's monolithic layout despite this Chapter Map already documenting the
Book 2 architecture. Bringing the two in sync surfaced two real bugs the split also fixes:

* **The live request path never called the rerank/embed service.** `infra/clients.py`
  unconditionally built an in-process `CrossEncoder` and `ONNXEmbedder`; the HTTP client
  (`retrieval/rerank_client.py`) existed but nothing called it. Both are now HTTP-only —
  see `shopbot-agent/CLAUDE.md` Section 7.
* **Port collision.** The old `services/inference/main.py` and its `Dockerfile` both
  bound port 8000 — the same port the agent uses. `shopbot-rerank` now binds 8001,
  matching Book 2's `RERANK_URL` convention.

**Why split this way** (same reasoning as Book 2, extended for Book 3's new pieces):
* `shopbot-ingest` vs `shopbot-agent` — `shopbot-ingest`'s scripts (`ingestion/dual_write.py`,
  `ingestion/bm25_backfill.py`, `infra/qdrant_setup.py`) already constructed their own
  OpenAI/Qdrant/fastembed clients inline rather than importing a shared client module —
  they never depended on it. `infra/clients.py`, `infra/types.py`, and
  `infra/comparison_log.py` are only ever imported by request-time, agent-side code. The
  split follows that existing dependency boundary; no import had to be rewritten, only
  relocated.
* `shopbot-agent` vs `shopbot-rerank` — the cross-encoder and the ONNX embedder are both
  CPU-bound, the main latency contributors under load, sharing no code, no dependencies
  (`sentence-transformers`/`torch`/`onnxruntime` only that service needs), and no deploy
  lifecycle with the rest of the project. The subfolder nesting (`services/inference/`)
  didn't reflect that independence, so it was extracted to a sibling project.
* **`fine_tune/` + `export/` became their own sibling, `shopbot-training`** — new in
  Book 3, no Book 2 precedent. They were initially folded into `shopbot-rerank` during the
  split (the model they produce is only ever consumed there), then split out again once it
  was clear the serving container should carry zero training-only dependencies or
  credentials: `shopbot-rerank`'s Dockerfile only ever installs inference libraries, and
  `shopbot-training` needs GPU `torch`, `optimum`, `openai`, and `qdrant-client` that have
  no business near a stateless, horizontally-scaled serving container. The two are
  connected only by a file copy (`shopbot-training/models/` → `shopbot-rerank/models/`),
  not an import or a live call — see `shopbot-training/CLAUDE.md` Section 4.

This split is new work performed to bring Book 3's checkout in line with the architecture
this Chapter Map already claimed — it is not itself attributed to a numbered book chapter.
Say so plainly rather than inventing a citation (per Section 0's rule).

Every file in any of the four still traces to a chapter of the book (see the Chapter
Map below) — that attribution is documented here, not against a local copy of the text.

---

## 3. Book Chapter Map

| Chapter | Content file | Contribution | Code file(s) |
|---------|-------------|-------------|-------------|
| Preface | `book-3/book3_preface_the_9_problem.md` | Four failure categories; the whiteboard agenda | — |
| Ch. 1 | `book-3/book3_chapter_1_nine_of_every_hundred.md` | Sorting 9% into vague/type-mismatch/routing/cost piles | — |
| Ch. 2 | `book-3/book3_chapter_2_the_answer_before_the_question.md` | HyDE; vague classifier; conditional routing | `shopbot-agent/retrieval/vague_classifier.py`, `shopbot-agent/retrieval/hyde.py`, `shopbot-agent/retrieval/entry.py` |
| Ch. 3 | `book-3/book3_chapter_3_the_chain_that_checks_itself.md` | CRAG judge (RELEVANT/PARTIAL/IRRELEVANT); re-retrieval; support fallback | `shopbot-agent/retrieval/crag.py`, `shopbot-agent/pipeline/respond.py` |
| Ch. 4 | `book-3/book3_chapter_4_from_chain_to_graph.md` | LangGraph graph; PipelineState; five named routes | `shopbot-agent/pipeline/state.py`, `nodes.py`, `edges.py`, `graph.py`, `respond.py` |
| Ch. 5 | `book-3/book3_chapter_5_a_smaller_model_that_knows_the_catalog.md` | bge-small fine-tune; triplet loss; training pairs from labeled queries | `shopbot-training/fine_tune/build_dataset.py`, `shopbot-training/fine_tune/train.py`, `shopbot-training/clients.py` |
| Ch. 6 | `book-3/book3_chapter_6_eight_bits_per_number.md` | ONNX FP32 export; INT8 dynamic quantisation; combined inference container | `shopbot-training/export/to_onnx_int8.py`, `shopbot-rerank/onnx_embedder.py`, `shopbot-rerank/main.py`, `shopbot-agent/infra/clients.py` (HTTP call site) |
| Ch. 7 | `book-3/book3_chapter_7_what_the_average_hides.md` | Per-route RAGAS slicing; derive_route(); RAGAS Monday per-route tab | `shopbot-agent/evaluation/routes.py`, `shopbot-agent/evaluation/per_route.py` |
| Ch. 8 | `book-3/book3_chapter_8_the_architecture_under_traffic.md` | Route-D fix; load test at 600 qpm; campaign at 38K qpd; HyDE prompt anchor fix | `shopbot-agent/retrieval/hyde.py`, `shopbot-agent/retrieval/crag.py`, `shopbot-agent/infra/clients.py` (multi-key) |
| Ch. 9 | `book-3/book3_chapter_9_what_the_system_became.md` | Synthesis; Meera's order; Book 3 arc closure | — |
| Appendix A | `book-3/Appendix_A_Code_Wiring.md` | All Book 3 code assembled; canonical source for all new and updated files (pre-split file paths — see each project's own CLAUDE.md for the post-split locations) | All Book 3 files |

---

## 4. Product Catalog

**Source:** `shopbot-ingest/data/products.py`. Owned by the ingest project since it is
only read at ingest time. **Note:** the Book 3 narrative (Ch. 5) refers to a larger
catalog than what's on disk — verify the actual product count before making
catalog-size assumptions.

**Book 2 catalog (baseline):** 50 products, 8 categories, ~255 chunks.

| Category | IDs | Book 2 count | Style code prefix | Example |
|----------|-----|-------|-------------------|---------|
| kurta | p001, p006–p014 | 10 | `K-` | K-1299 |
| saree | p003, p015–p023 | 10 | `SA-` | SA-4299 |
| suit | p005, p024–p032 | 10 | `SU-` | SU-3499 |
| coord-set | p004, p033–p036 | 5 | `CO-` | CO-1899 |
| shawl | p002, p037–p040 | 5 | `SH-` | SH-2199 |
| lehenga | p041–p045 | 5 | `LH-` | LH-8499 |
| dupatta | p046–p048 | 3 | `DU-` | DU-399 |
| sharara | p049–p050 | 2 | `SR-` | SR-5499 |

---

## 5. What Book 4 Will Address (left open by Book 3)

| Limitation | Book 3 status | Book 4 approach |
|-----------|--------------|-----------------|
| Single-tenant architecture | One zUdyog Fashion catalog, one Qdrant collection | Multi-tenant isolation; per-tenant collections |
| Per-tenant fine-tunes | bge-small-zudyog-v1 is catalog-specific to zUdyog | Per-tenant fine-tune pipeline; shared base, per-tenant adapters |
| Scale: thousands of SKUs per tenant | Tested at a much smaller catalog | Qdrant billion-scale; sharding strategy |
| GDPR / DPDP compliance | No per-tenant audit trail | Per-tenant audit logs; data residency controls |
| Route B still weakest scored route (CP 0.85) | Partial re-retrieval occasionally off-topic | CRAG sub-query quality improvement |
| llm_small still gpt-4o-mini | Same model for classifier, judge, decomposer | Smaller, cheaper model for low-output calls |
| LangGraph state is in-memory per request | No persistence across the graph | Persistent graph state for longer agentic loops |
| Multi-tenant onboarding | Not started | Multi-tenant onboarding pipeline |

---

## 6. Other Project-Wide Files

- `costs/cost_log.md` — running OpenAI/GPU cost audit trail across all three projects.
- `zudyog-fashion/` — the Next.js storefront + chat widget; calls `shopbot-agent`'s
  `/ask` endpoint over HTTP. Untouched by the ingest/agent/rerank split.
- `book-3/` — the Book 3 chapter source files. Unlike Book 2 (which publishes its
  manuscript separately), Book 3 keeps chapter source in-repo — see Section 0's
  Book → Code rule, which reads directly from these files. This is an intentional
  per-book difference, not something to reconcile with Book 2's repo layout.
- `BOOK3_SESSION_PROMPT.md` — paste-at-start-of-session prompt for this project.
- `venv/` — a legacy shared virtualenv from before the split. Each subproject now
  documents its own `python -m venv venv` setup; this one is stale and can be removed
  once all three subprojects have their own environments (`shopbot-rerank/`'s served
  `main.py` typically runs via Docker instead, per its `CLAUDE.md`).
