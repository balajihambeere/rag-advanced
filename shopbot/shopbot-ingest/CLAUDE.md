# ShopBot Ingest — Build-Time Pipeline (Book 3)

> Part of the ShopBot project. Read `../CLAUDE.md` first for the operating principle,
> the book ↔ code chapter map, and how this project relates to `../shopbot-agent/` and
> `../shopbot-rerank/`. This file covers only the build-time (ingest) half of the pipeline.

Do not guess, speculate, or fill gaps with assumptions. Every constant and design choice
here traces to a chapter documented in `../CLAUDE.md`'s Chapter Map. If you cannot cite
the chapter, do not write the line.

---

## 1. What This Project Does

Reads the product catalog, chunks it, embeds it, and writes it into both ChromaDB
(Book 1 legacy store, passive) and Qdrant Cloud (dense + BM25 sparse). Run once for the
initial load, and re-run whenever `data/products.py` or the chunking strategy changes.
Nothing in this project serves live traffic — that's `../shopbot-agent/`.

This project is fully standalone: every script here builds its own OpenAI / Qdrant /
fastembed clients inline. It does not import `../shopbot-agent/infra/clients.py`.

---

## 2. File Tree

```
shopbot-ingest/
├── infra/
│   ├── __init__.py
│   └── qdrant_setup.py      ← Create "zudyog_catalog" + "answer_cache" collections
│
├── ingestion/
│   ├── __init__.py
│   ├── dual_write.py        ← Write chunks to ChromaDB AND Qdrant (Book 2 Ch. 2)
│   └── bm25_backfill.py     ← Populate BM25 sparse vectors in Qdrant (Book 2 Ch. 3)
│
├── src/
│   ├── __init__.py
│   └── chunker.py           ← product_to_chunks() — Book 1 baseline, still used here
│
├── data/
│   ├── __init__.py
│   └── products.py          ← Product catalog (Book 1 Ch. 5 + Ch. 10)
│
├── chroma_db/                ← ChromaDB persistent store (written by dual_write.py)
├── requirements.txt
├── .env                      ← Never commit
└── .env.example
```

---

## 3. Data Flow — Build-Time

```
data/products.py
    │  PRODUCTS list
    ▼
src/chunker.py  product_to_chunks()
    │  ~5-6 chunks per product
    ▼
ingestion/dual_write.py
    │  embed_documents() via langchain_openai (batch, text-embedding-3-small, 1536-dim)
    │  ├── ChromaDB upsert → ./chroma_db/  (passive in Book 3 — kept for historical parity)
    │  └── Qdrant upsert  → cloud         (collection: zudyog_catalog)
    ▼
ingestion/bm25_backfill.py
    │  for each chunk: fastembed Qdrant/bm25 sparse encode → qdrant update_vectors
    └── Qdrant "bm25" sparse field filled
```

`chroma_db/` is read by `../shopbot-agent/retrieval/shadow.py` during the (now retired)
migration shadow-read phase.

---

## 4. Product Catalog

**Source:** `data/products.py`. See `../CLAUDE.md` Section 4 for the category/style-code
table. **Note:** the Book 3 narrative (Ch. 5) refers to a larger catalog than what's on
disk — verify the actual product count in `data/products.py` before making catalog-size
assumptions; do not assume the narrative figure without checking the file.

**Book 1 Ch. 10 "function" fix:** `"function"` added to `occasion` field of any product
whose occasion contains `"festive"`. Applied at conversion time.

---

## 5. Chunking Strategy (Book 1, Ch. 5 + Book 2 identity-chunk fix)

**File:** `src/chunker.py → product_to_chunks(product: dict) -> list[dict]`
**Used by:** `ingestion/dual_write.py` and `ingestion/bm25_backfill.py`.

| Chunk ID | Type | Answers |
|----------|------|---------|
| `{pid}_identity` | identity | What is this? Style code? Fabric? Occasion? Category? Colours? Sizes? Price? |
| `{pid}_variants` | variants | Colours? Sizes? Price? In stock? |
| `{pid}_policy` | policy | Return window? Exchange conditions? |
| `{pid}_care` | care | Machine wash? Dry clean? Iron? |
| `{pid}_faq_0`, `{pid}_faq_1`, … | faq | One chunk per FAQ entry |

**Style code in identity chunk:** allows BM25 to match literal SKU lookups (e.g. `"K-1299"`)
directly — dense retrieval alone cannot, since SKU codes carry no semantic meaning.

**Colors/sizes/price in identity chunk (Book 2 fix, inherited):** the identity chunk ends
with `Available in: {colors}. Sizes: {sizes}. Price: {price}.` so it's self-sufficient for
a complete recommendation even when the variants chunk ranks outside the top-3 cutoff.

**After changing the chunker, always re-run ingestion:**
`python -m ingestion.dual_write --force && python -m ingestion.bm25_backfill`.

---

## 6. ChromaDB (Book 1 baseline — passive in Book 3)

```python
# ingestion/dual_write.py
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="zudyog_products",
    metadata={"hnsw:space": "cosine"},
)
```

Not used in any Book 3 retrieval path — all reads go through
`../shopbot-agent/retrieval/hybrid.py` → Qdrant. `dual_write.py` still writes here for
historical parity with the Book 2 migration.

---

## 7. Qdrant Setup

**File:** `infra/qdrant_setup.py`
**Collection name:** `"zudyog_catalog"` (plus `"answer_cache"`, owned/read by
`../shopbot-agent/`).

**Known dimension mismatch — pre-existing, not introduced by this split:**
`../CLAUDE.md`'s top-level chapter map documents a Book 3 change from 1536-dim
(`text-embedding-3-small`) to 384-dim (`bge-small-zudyog-v1-onnx-int8`, served by
`../shopbot-rerank/`'s `/embed` endpoint). `infra/qdrant_setup.py` in this checkout
already creates the collection at 384-dim, but `ingestion/dual_write.py` still embeds
with `langchain_openai.OpenAIEmbeddings` (1536-dim) — inserting those vectors into a
384-dim collection will fail. This divergence predates the ingest/agent/rerank split and
is out of scope for it; documenting it here per the project's divergence rule (`../CLAUDE.md`
§0) rather than silently picking a fix. Before running `dual_write.py` against a fresh
384-dim collection, either point `qdrant_setup.py` back at 1536-dim, or switch
`dual_write.py` to call `../shopbot-rerank/`'s `/embed` endpoint over HTTP.

```python
client.create_collection(
    collection_name="zudyog_catalog",
    vectors_config={
        "dense": models.VectorParams(size=384, distance=models.Distance.COSINE),
    },
    sparse_vectors_config={
        "bm25": models.SparseVectorParams(
            index=models.SparseIndexParams(on_disk=False),
        ),
    },
)
```

**Qdrant point IDs:** Chunk IDs are strings (`"p001_identity"`). Qdrant requires unsigned
integer or UUID. Conversion: `uuid.uuid5(_NS, chunk_id)` where
`_NS = uuid.UUID("00000000-0000-0000-0000-000000000001")`. Original string stored in
`payload["chunk_id"]`. The same namespace UUID and conversion function are duplicated in
`ingestion/dual_write.py`, `ingestion/bm25_backfill.py`, and
`../shopbot-agent/retrieval/shadow.py` — they must stay in sync if ever changed.

---

## 8. Run Order

```bash
# 1 — Create virtual environment (once)
python -m venv venv && source venv/bin/activate

# 2 — Install dependencies
pip install -r requirements.txt

# 3 — Set env vars
cp .env.example .env
# Fill in: OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY

# 4 — Create Qdrant collections (once)
python -m infra.qdrant_setup

# 5 — Dual-write catalog to ChromaDB + Qdrant (once; re-run with --force after catalog changes)
python -m ingestion.dual_write

# 6 — Populate BM25 sparse vectors (once per ingest)
python -m ingestion.bm25_backfill
```

After Step 6, start `../shopbot-rerank/` then `../shopbot-agent/` to serve queries
against the collection this project just populated.

---

## 9. Known Dependency Issues

### chromadb==0.6.3 pin vs installed version

`requirements.txt` pins `chromadb==0.6.3` to protect the on-disk `chroma_db/` schema.
Do not change the pin without a fresh `ingestion/dual_write.py` run.

### qdrant-client >= 1.12 removed `.search()`

All code uses the replacement `query_points()` API. This project's scripts only ever
*write*, so they're unaffected by the removal, but keep the client version aligned with
`../shopbot-agent/`'s if both are upgraded.

### LangChain imports in dual_write.py

`ingestion/dual_write.py` uses `langchain_openai.OpenAIEmbeddings` for batch embedding
(`embed_documents()`) to keep ingest cost to one API call for the whole catalog.
`langchain-openai` is kept in `requirements.txt` for this reason alone.

### Embedding dimension mismatch — see Section 7

384-dim collection vs 1536-dim ingest embeddings. Resolve before running a fresh ingest;
see Section 7 for the two options.

---

## 10. Rules for Future Changes

1. **Re-run ingestion after any catalog change.** `data/products.py` is only read at
   ingest time. Changes have no effect until `ingestion/dual_write.py` and
   `ingestion/bm25_backfill.py` are re-run.

2. **After changing the chunker, always re-run both ingestion scripts** — see Section 5.

3. **Before running any OpenAI script:** log estimated cost in `../costs/cost_log.md`,
   validate with 1 case first.

4. **Every constant must trace to a chapter.** The UUID namespace, collection names, and
   chunk-type list are fixed by Book 2 Chapters 2–3 — do not change them without updating
   `../shopbot-agent/` in lockstep, since it reads the same Qdrant collection.
