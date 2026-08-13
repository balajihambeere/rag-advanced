# ShopBot Agent — Request-Time Pipeline (Book 3)

> Part of the ShopBot project. Read `../CLAUDE.md` first for the operating principle,
> the book ↔ code chapter map, and how this project relates to `../shopbot-ingest/` and
> `../shopbot-rerank/`. This file covers only the request-time (agent) half of the pipeline.

Do not guess, speculate, or fill gaps with assumptions. Every constant and design choice
here traces to a chapter documented in `../CLAUDE.md`'s Chapter Map. If you cannot cite
the chapter, do not write the line.

---

## 1. What This Project Does

The FastAPI service (`/ask`) — session memory, three-layer cache, LangGraph pipeline
(vague classification → HyDE or standard hybrid retrieval → CRAG judge → generate/
re-retrieve/fallback), reranking and embedding via HTTP to `../shopbot-rerank/`, LLM
answering. Also owns evaluation (RAGAS, per-route) and load testing.

**Ch. 9 / the ingest-agent-rerank split:** this process has no in-process cross-encoder
or ONNX embedder. Both live exclusively in `../shopbot-rerank/`, a required HTTP
dependency (`RERANK_URL`, no fallback) — see `retrieval/rerank_client.py` and
`infra/clients.py:embed()`.

---

## 2. File Tree

```
shopbot-agent/
├── src/
│   ├── __init__.py
│   └── api.py                  ← FastAPI app; /health + /ask; lifespan checks RERANK_URL
│
├── pipeline/                   ← Ch. 4 LangGraph orchestration
│   ├── __init__.py
│   ├── state.py                ← PipelineState TypedDict
│   ├── nodes.py                ← One function per node
│   ├── edges.py                ← route_after_classify(), route_after_crag()
│   ├── graph.py                ← build_pipeline_graph(); module-level `pipeline` singleton
│   └── respond.py / generate.py
│
├── retrieval/
│   ├── __init__.py
│   ├── vague_classifier.py     ← is_vague(query) — Ch. 2
│   ├── hyde.py                 ← hyde_retrieve(); category-anchored HYDE_PROMPT — Ch. 2, updated Ch. 8
│   ├── entry.py                ← retrieve_with_optional_hyde() — Ch. 2
│   ├── crag.py                 ← crag_judge(), crag_retrieve() — Ch. 3, updated Ch. 8
│   ├── hybrid.py                ← Dense + BM25 via RRF (RRF_K=60) — Book 2 Ch. 3
│   ├── rerank.py                ← Calls ../shopbot-rerank/ over HTTP — Book 2 Ch. 4, moved to HTTP in Ch. 9
│   ├── rerank_client.py         ← Sync HTTP client (rerank_remote, rerank_scores_remote) — Book 2 Ch. 9
│   ├── memory_aware.py          ← Active-SKU boost (0.05) + confidence floor (0.55), scores via rerank_client
│   ├── decompose.py             ← LLM-based 1-vs-2 intent detection — Book 2 Ch. 5+6
│   ├── multi_query.py           ← Decompose → per-sub-query retrieve → RRF merge — Book 2 Ch. 5
│   ├── prompt_multi.py          ← User-message builder — Book 2 Ch. 5+6
│   ├── system_prompt.py         ← SHOPBOT_SYSTEM_B2 — Book 2 Ch. 6
│   └── shadow.py                ← Standalone ChromaDB/Qdrant shadow-read comparison (Book 2 Ch. 2, retired)
│
├── memory/                     ← Book 2 Ch. 6 — unchanged in Book 3
│   ├── __init__.py
│   ├── session.py               ← Redis-backed: last 3 turns + summary + active_skus
│   └── update.py                ← push_turn(), maybe_refresh_summary(), extract_mentioned_skus()
│
├── cache/                      ← Book 2 Ch. 7 — unchanged in Book 3
│   ├── __init__.py
│   ├── layered.py               ← exact (Redis) + semantic (Qdrant 0.97) layers
│   ├── wrapper.py                ← answer_with_cache()
│   └── invalidation.py           ← Redis pub-sub invalidation worker
│
├── infra/
│   ├── __init__.py
│   ├── clients.py               ← llm, llm_small, qdrant_client, r, bm25, embed() (HTTP to shopbot-rerank)
│   ├── types.py                 ← Chunk dataclass
│   └── comparison_log.py        ← Shadow comparison JSONL writer (Book 2 Ch. 2)
│
├── evaluation/                 ← Book 2 Ch. 8, extended Book 3 Ch. 7
│   ├── __init__.py
│   ├── labeled_dataset.jsonl
│   ├── evaluate.py              ← All 4 RAGAS dims; asyncio monkeypatch
│   ├── monday.py                ← Weekly RAGAS + per-route Google Sheets tab
│   ├── routes.py                ← derive_route(state) → A/B/C/D/E
│   └── per_route.py             ← evaluate_per_route(); ≥5 samples to score
│
├── loadtest/
│   ├── __init__.py
│   └── harness.py                ← async httpx; configurable --qpm + --duration; p50/p95
│
├── debug_retrieval.py
├── .vscode/launch.json
├── docker-compose.yml            ← postgres + mlflow (MLflow tracking backend only)
├── Procfile                      ← Railway: uvicorn src.api:app
├── requirements.txt
├── .env                          ← Never commit
└── .env.example
```

---

## 3. Data Flow — Request-Time

```
POST /ask  {"question": "...", "session_id": "..."}
    │
src/api.py  QuestionRequest validator
    │  normalise smart quotes, em-dash; reject empty/long/injection
    │
    ├── memory/session.py  load_session(session_id)
    │
cache/wrapper.py  answer_with_cache(question, session)
    │
    ├── Layer 1 — Exact match (Redis)
    ├── Layer 2 — Semantic match (embed() → HTTP to shopbot-rerank → Qdrant "answer_cache" ≥0.97)
    └── Layer 3 — Full pipeline (cache miss)
            pipeline/graph.py  pipeline.invoke(initial_state)
                classify_vague_node → [HyDE | standard] retrieve → crag_judge_node
                    → generate_node | re_retrieve_node → generate_node | fallback_node
            (rerank inside retrieval: HTTP POST {RERANK_URL}/rerank via retrieval/rerank_client.py)
    │
    ├── cache/layered.py  put_exact() + put_semantic()
    ├── memory/update.py  push_turn() × 2, extract_mentioned_skus(), maybe_refresh_summary()
    └── memory/session.py  save_session()
    ▼
AnswerResponse {"answer": "...", "session_id": "..."}
```

### The five pipeline routes

| Route | Path through nodes | Typical traffic share |
|-------|-------------------|----------------------|
| A — standard + RELEVANT | classify_vague → standard_retrieve → crag_judge → generate | ~50% |
| B — standard + PARTIAL | classify_vague → standard_retrieve → crag_judge → re_retrieve → generate | ~18% |
| C — HyDE + RELEVANT | classify_vague → hyde → crag_judge → generate | ~16% |
| D — HyDE + PARTIAL | classify_vague → hyde → crag_judge → re_retrieve → generate | ~9% |
| E — fallback | [any] → crag_judge(IRRELEVANT) → fallback | ~10% |

---

## 4. Retrieval Constants

| Constant | Value | Defined in |
|----------|-------|-----------|
| RRF_K | 60 | `retrieval/hybrid.py` |
| RERANK_CONFIDENCE_FLOOR | 0.55 | `retrieval/memory_aware.py` |
| ACTIVE_SKU_BOOST | 0.05 | `retrieval/memory_aware.py` |
| VAGUE_CLASSIFIER_PROMPT | max_tokens=4, temperature=0 | `retrieval/vague_classifier.py` |
| HYDE_PROMPT | max_tokens=120, temperature=0, category-anchored (Ch. 8 fix) | `retrieval/hyde.py` |
| CRAG_JUDGE_PROMPT | max_tokens=80, temperature=0 | `retrieval/crag.py` |
| Dense/BM25 candidates per query | 20 | `retrieval/hybrid.py` |
| Hybrid top-n to rerank | 10 (default), 20 (memory-aware path) | `retrieval/hybrid.py` / `retrieval/memory_aware.py` |
| Final chunks to prompt | 3 | `retrieval/memory_aware.py`, `retrieval/rerank.py` |

**CRAG sub-query (Ch. 8 Route-D fix):** when CRAG rules PARTIAL on a HyDE-routed
retrieval, the sub-query prompt uses the **original raw customer query**, not the HyDE
hypothetical. Do not revert.

---

## 5. Session Memory (Book 2, Ch. 6) — unchanged in Book 3

**Files:** `memory/session.py`, `memory/update.py`. Backend: Redis; TTL = 86,400s.
Key: `session:{session_id}`.

```python
@dataclass
class Session:
    session_id:   str
    recent_turns: list[Turn] = field(default_factory=list)  # last 3 verbatim
    summary:      str = ""                                   # rolling, ≤2 sentences
    active_skus:  list[str] = field(default_factory=list)   # most recent 3
```

Context arrives in the **user message** via `build_prompt_multi()`, not the system prompt —
`SHOPBOT_SYSTEM_B2` has no `{context}` placeholder.

---

## 6. Three-Layer Cache (Book 2, Ch. 7) — unchanged in Book 3

**Files:** `cache/layered.py`, `cache/wrapper.py`, `cache/invalidation.py`

| Layer | Mechanism | Threshold | TTL |
|-------|-----------|-----------|-----|
| Exact | Redis hash(query) | exact string | 1 hour |
| Semantic | Qdrant cosine on query vector | ≥0.97 | 1 hour |
| Full pipeline | LangGraph graph | — | — |

**Context-sensitive bypass:** when `session.recent_turns` is non-empty, L1/L2 are skipped
and the result is not written back — the same query string means different things in
different sessions. Only context-free (turn-1) queries are cached.

**The `"answer_cache"` Qdrant collection stores 384-dim vectors** (bge-small ONNX INT8,
served by `../shopbot-rerank/`). Must be rebuilt when migrating from a Book 2 (1536-dim)
checkout.

---

## 7. Reranking and Embedding — moved to HTTP (Ch. 9 / the split)

Full details (model, fine-tune, ONNX export, RAGAS comparison) live in
`../shopbot-rerank/CLAUDE.md`. This project only calls it:

- `retrieval/rerank_client.py` — `rerank_remote()` (top-k winners),
  `rerank_scores_remote()` (full-candidate scores, used by `memory_aware.py`'s
  active-SKU boost). Sync `httpx.Client`, 5s timeout, no fallback.
- `infra/clients.py:embed()` — `POST {RERANK_URL}/embed`, no fallback.
- `src/api.py`'s `lifespan()` checks `{RERANK_URL}/health` at startup and raises a clear
  `RuntimeError` if `../shopbot-rerank/` isn't running — a forgotten `docker run` fails
  loudly at boot, not on the first customer request.

`RERANK_URL` is a required env var (`os.environ["RERANK_URL"]`, no `.get()` default).

---

## 8. LLM (Book 1 Ch. 7 + Appendix A + Book 3 Ch. 8)

```python
# infra/clients.py
llm       = _LLM("gpt-4o-mini", temperature=0)   # main answerer + HyDE generation
llm_small = _LLM("gpt-4o-mini", temperature=0)   # vague classifier + CRAG judge + decomposer
```

**temperature=0** — deterministic. Hard rule.

**Multi-key round-robin (Ch. 8):** at 600 qpm (~1,300 LLM calls/min: HyDE + CRAG +
generate), a single API key throttles. `OPENAI_API_KEY_PRIMARY` / `_SECONDARY` in `.env`;
falls back to `OPENAI_API_KEY` alone if `_SECONDARY` is unset.

**`_LLM.complete()` does not accept a `temperature` kwarg** — it's fixed at construction.
Some book chapter snippets show `complete(..., temperature=0)`; the actual code correctly
omits it. The code is authoritative; the snippets are illustrative.

---

## 9. System Prompt (Book 2 Ch. 6 + Book 1 Ch. 7/10)

**File:** `retrieval/system_prompt.py` → `SHOPBOT_SYSTEM_B2`. Unchanged in Book 3 — warm,
honest, Pramana-grounded, type-mismatch guard. No `{context}` placeholder.

Do not edit without running `evaluation/per_route.py` and recording before/after per-route
scores — a change that improves Route A while degrading Route D is not an improvement.

---

## 10. Evaluation Framework (Book 2 Ch. 8 + Book 3 Ch. 7)

| Metric | Reference-free? | What it measures |
|--------|----------------|-----------------|
| Faithfulness | Yes | Are model claims grounded in retrieved chunks? |
| Answer Relevance | No — needs labels | Does the answer address the actual question? |
| Context Precision | Yes | Are retrieved chunks the relevant ones? |
| Context Recall | No — needs labels | Were all chunks needed for the answer retrieved? |

**Labeled dataset:** `evaluation/labeled_dataset.jsonl`. Grew from 100 (Book 2 target)
during Book 3 by adding ~20/week from the failed-query log, stratified across routes.

**Per-route evaluation (Ch. 7):** `evaluation/routes.py` derives A/B/C/D/E from the final
`PipelineState`; `evaluation/per_route.py` scores each route (≥5 samples required).
RAGAS Monday's Google Sheet has a *Blended* tab and a *Per-Route* tab — the per-route tab
is the diagnostic signal; a blended-number change not explained by a route move is a flag.

**asyncio monkeypatch:** `evaluation/evaluate.py` and `evaluation/per_route.py` carry a
monkeypatch for a `ragas==0.1.22` bug (`ensure_future()` scheduling tasks on the wrong
loop before `asyncio.run()`). Never use
`asyncio.set_event_loop(asyncio.new_event_loop())` — causes a 25-minute hang for the same
root cause. See Section 12, Issue 1.

**Note:** older narrative/doc references to `eval/run_ragas.py` are stale — the actual file
is `evaluation/evaluate.py`.

---

## 11. API Endpoint

**File:** `src/api.py`

| Method | Path | Response |
|--------|------|----------|
| GET | `/health` | `{"status": "ok", "service": "ShopBot", "version": "3.0.0"}` |
| POST | `/ask` | `{"answer": str, "session_id": str}` |

**Input validation:** smart quote normalisation, em-dash normalisation, 500-char limit,
5 injection patterns (reject, don't sanitize-and-continue).

**Lifespan:** checks `{RERANK_URL}/health` (raises if unreachable), compiles the
LangGraph pipeline singleton, and enables MLflow tracing if `MLFLOW_TRACKING_URI` is set.

---

## 12. Run Order

```bash
# 1 — Create virtual environment (once)
python -m venv venv && source venv/bin/activate

# 2 — Install dependencies
pip install -r requirements.txt

# 3 — Set env vars
cp .env.example .env
# Fill in: OPENAI_API_KEY (+ optionally _PRIMARY/_SECONDARY), QDRANT_URL, QDRANT_API_KEY,
#          REDIS_URL, RERANK_URL, and optionally GOOGLE_APPLICATION_CREDENTIALS,
#          MLFLOW_TRACKING_URI

# 4 — Start ../shopbot-rerank/ first (required, no in-process fallback)
#     cd ../shopbot-rerank && docker build -t shopbot-rerank . && docker run -p 8001:8001 shopbot-rerank

# 5 — Ensure ../shopbot-ingest/ has populated the Qdrant collection at least once

# 6 — Start the API
uvicorn src.api:app --host 0.0.0.0 --port 8000
# → http://localhost:8000/docs
```

---

## 13. Known Dependency Issues

1. **ragas==0.1.22 asyncio hang** — see Section 10. Fixed via monkeypatch; do not revert.
2. **LangChain imports in `retrieval/shadow.py`** — uses `langchain_openai.OpenAIEmbeddings`
   for the retired shadow-read comparison. `langchain-openai` stays in `requirements.txt`
   for this reason alone.
3. **chromadb==0.6.3 pin** — protects the on-disk `../shopbot-ingest/chroma_db/` schema
   that `shadow.py` reads. Do not change without a fresh ingest run.
4. **langgraph version compatibility** — `StateGraph`'s `add_conditional_edges()` signature
   and `END` import location can differ across minor versions. After any upgrade, verify
   with `pipeline.graph.pipeline.get_graph().draw_ascii()` and run one query end-to-end.
5. **`_LLM.complete()` has no `temperature` kwarg** — see Section 8.

---

## 14. Rules for Future Changes

1. **Every constant must trace to a chapter** — see Section 4 and `../CLAUDE.md`'s Chapter Map.
2. **The CRAG sub-query for HyDE-routed queries uses the original raw query as context**
   (Ch. 8 Route-D fix) — do not revert.
3. **The HYDE_PROMPT includes a category anchor list** (Ch. 8 Route-C fix) — do not remove;
   update it if the catalog's product categories change.
4. **Do not lower RERANK_CONFIDENCE_FLOOR below 0.55.** A fallback is correct behaviour
   when nothing passes.
5. **Do not move pipeline construction into request handlers.** The `lifespan()` pattern
   compiles the LangGraph graph once at startup — per-request compilation adds latency.
6. **Every prompt change must be tested with per-route eval**, not just the blended number.
7. **Expand the labeled dataset continuously** — ~20 queries/week from the failed-query log,
   stratified across routes.
8. **`RERANK_URL` must stay required, with no in-process fallback.** A silent fallback to
   an in-process CrossEncoder/ONNXEmbedder is exactly the drift this split fixed — see
   `../CLAUDE.md`'s "Three Projects, One Pipeline" section for why.
