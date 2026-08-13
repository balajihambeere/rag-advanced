# ShopBot — Cost Log

Every OpenAI API operation is logged here before and after it runs.
Format: one entry per run, most recent at the top.
Evaluation scores are written to `evaluation/results/` after each run.

---

## Run 003 — fine_tune/build_dataset.py smoke test (post ingest/agent/rerank/training split)

| Field | Value |
|-------|-------|
| Date | 2026-08-11 |
| Operation | `build_triplets(rows[:2])` in `shopbot-training/` — verifying the triplet-building pipeline (paraphrase expansion + hard-negative sampling) actually runs against real Qdrant data, after fixing the missing chunk_id/product_id/chunk_type payload indexes |
| Model | `gpt-4o-mini` (paraphrase expansion only, via `llm_small.complete()`) |
| Test cases | 2 labeled queries (not the full ~100-query dataset — this was a wiring smoke test, not a real training-data build) |
| Output | 18 triplets built successfully; confirmed anchor/positive/negative shape is correct |
| Estimated cost | <$0.01 (2 short paraphrase-expansion calls, ~200 max_tokens each) |
| Actual cost | (check OpenAI dashboard) |
| Status | Completed |
| Note | `fine_tune/train.py` (the actual GPU fine-tune) was NOT run — that's a real ~₹240 GPU cost and should be logged separately with the full dataset before it's run for real. |

---

## Run 002 — RAGAS Evaluation (Book 1 baseline)

| Field | Value |
|-------|-------|
| Date | 2026-07-21 |
| Operation | `python -m evaluation.evaluate` — 20 test cases |
| Run ID | `run_20260721_070927` |
| Models | `text-embedding-3-small` (retrieval) + `gpt-4o-mini` (generation + scoring) |
| Test cases | 20 |
| Queries retrieved | 19/20 (query 09 — winter wedding — correctly returned fallback) |
| Query embedding tokens | 192 (exact, tiktoken) |
| LLM input tokens | 8,092 |
| LLM output tokens | 1,304 |
| Embedding cost | $0.000004 |
| LLM cost | $0.001996 |
| **Total actual** | **$0.002000** |
| Run time | 76.8s |
| Faithfulness | **0.7494** (book1 stated baseline: 0.71) |
| Context Precision | **0.6417** (book1 stated baseline: 0.82) |
| Status | **Completed** |
| Results file | `evaluation/results/run_20260721_070927.json` |
| Checkpoint file | `evaluation/results/run_20260721_070927_checkpoint.json` |

### Score interpretation

Faithfulness **improved** vs book baseline (0.7494 vs 0.71): the V4 prompt's "Stop when
the evidence stops" clause is holding better than V3.

Context Precision **dropped** vs book baseline (0.6417 vs 0.82): expected consequence of
expanding the catalog from 5 → 50 products. With 255 chunks in the store instead of 28,
similar products (9 additional kurtas, 9 sarees) now compete with the correct chunk and
get retrieved alongside it, adding adjacent noise. This is the retrieval precision cost
of catalog expansion. Book 2 addresses it with hybrid search and re-ranking.

### Note on previous failed attempts

Two earlier pipeline runs (~$0.002 each) were lost to asyncio compatibility failures
between ragas 0.1.22 and Python 3.14. Root cause identified and fixed (see CLAUDE.md
Section 17, Issue 3). Checkpoint system added so pipeline results survive future RAGAS
failures.

---

## Run 001 — Ingest (build Grounding Layer)

| Field | Value |
|-------|-------|
| Date | 2026-07-21 |
| Operation | `python src/ingest.py` — full catalog ingest |
| Model | `text-embedding-3-small` (OpenAI) |
| Encoding | `cl100k_base` (tiktoken exact count) |
| Products | 50 |
| Chunks | 255 |
| Total tokens | 10,905 |
| Price per 1M tokens | $0.02 |
| **Estimated cost** | **$0.000218 (~$0.0002)** |
| Status | **Completed** — 255 chunks ingested successfully |

### Per-product breakdown

| Product ID | Name | Chunks | Tokens |
|------------|------|--------|--------|
| p001 | Breathable Cotton Kurta | 6 | 251 |
| p002 | Heavyweight Woolen Shawl | 5 | 197 |
| p003 | Printed Silk Saree | 6 | 278 |
| p004 | Linen Co-ord Set | 5 | 204 |
| p005 | Embroidered Anarkali Suit | 6 | 253 |
| p006 | Chanderi Silk Kurta | 5 | 211 |
| p007 | Block Print Cotton Kurta | 5 | 210 |
| p008 | Rayon Flared Kurta | 5 | 205 |
| p009 | Chikankari Embroidered Kurta | 5 | 252 |
| p010 | Straight Cut Silk Kurta | 5 | 206 |
| p011 | Bandhani Print Cotton Kurta | 5 | 235 |
| p012 | Mirror Work Cotton Kurta | 5 | 206 |
| p013 | Georgette Long Kurta | 5 | 212 |
| p014 | Khadi Straight Kurta | 5 | 208 |
| p015 | Banarasi Silk Saree | 5 | 231 |
| p016 | Cotton Tant Saree | 5 | 215 |
| p017 | Chiffon Printed Saree | 5 | 202 |
| p018 | Kanjivaram Silk Saree | 5 | 269 |
| p019 | Linen Saree | 5 | 201 |
| p020 | Chanderi Saree | 5 | 217 |
| p021 | Georgette Saree | 5 | 212 |
| p022 | Handloom Cotton Saree | 5 | 219 |
| p023 | Organza Saree | 5 | 203 |
| p024 | Straight Cut Palazzo Suit | 5 | 209 |
| p025 | Patiala Salwar Suit | 5 | 228 |
| p026 | Cotton Straight Suit | 5 | 195 |
| p027 | Heavy Embroidered Anarkali | 5 | 231 |
| p028 | Printed Georgette Suit | 5 | 207 |
| p029 | Silk Salwar Kameez | 5 | 215 |
| p030 | Linen Straight Suit | 5 | 194 |
| p031 | Rayon Printed Suit | 5 | 192 |
| p032 | Kurta Sharara Suit | 5 | 217 |
| p033 | Cotton Co-ord Set | 5 | 198 |
| p034 | Silk Co-ord Set | 5 | 209 |
| p035 | Printed Rayon Co-ord Set | 5 | 214 |
| p036 | Embroidered Cotton Co-ord Set | 5 | 226 |
| p037 | Pashmina Shawl | 5 | 241 |
| p038 | Silk Stole | 5 | 190 |
| p039 | Printed Cotton Stole | 5 | 190 |
| p040 | Kaani Woolen Stole | 5 | 221 |
| p041 | Bridal Silk Lehenga | 6 | 262 |
| p042 | Party Wear Net Lehenga | 5 | 211 |
| p043 | Cotton Printed Lehenga Set | 5 | 221 |
| p044 | Embroidered Velvet Lehenga | 5 | 225 |
| p045 | Georgette Lehenga | 5 | 215 |
| p046 | Chiffon Printed Dupatta | 5 | 201 |
| p047 | Silk Embroidered Dupatta | 5 | 214 |
| p048 | Cotton Block Print Dupatta | 5 | 201 |
| p049 | Silk Sharara Set | 6 | 269 |
| p050 | Cotton Sharara Set | 5 | 212 |
| **TOTAL** | | **255** | **10,905** |

### Notes
- 6 products have 6 chunks each (p001, p003, p005, p041, p049 — 2 FAQs each; p050 — 1 FAQ)
- Wait: p050 has 5 chunks. Products with 6 chunks: p001, p003, p005, p041, p049 (2 FAQs each)
- Single `embed_documents()` call — all 255 texts in one API request (Ch. 4 design)
- Token counting uses `tiktoken cl100k_base` — exact, not estimated

---

## Future runs — append below this line

Template for future entries:

```
## Run NNN — [Operation]
| Date | YYYY-MM-DD |
| Operation | ... |
| Model | ... |
| Tokens | ... |
| Estimated cost | $X.XXXXXX |
| Actual cost | (check OpenAI dashboard) |
| Status | Completed / Failed |
```
