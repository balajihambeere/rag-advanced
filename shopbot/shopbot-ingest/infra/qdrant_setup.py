# infra/qdrant_setup.py
# Source: Book 2, Chapter 2 — Move Without Breaking Things
# Creates the Qdrant collection with a 1536-dim dense vector and a sparse BM25 field.
# Run once to bootstrap. Safe to re-run — checks before creating.
#
# Collection: "zudyog_catalog"
# Dense:  1536-dim cosine (same embedding model as Book 1 ChromaDB collection)
# Sparse: BM25 (populated by ingestion/bm25_backfill.py in Chapter 3)
#
# Payload indexes — added post-split, run-and-test found the gap:
# ../shopbot-training/fine_tune/catalog_store.py filters scroll() by chunk_id,
# product_id, and chunk_type. Qdrant rejects a filter on a field with no
# payload index (400 Bad Request) — those three fields were populated by
# ingestion/dual_write.py's payload dict but never indexed. create_payload_index()
# is idempotent (safe to re-run; a second call on an already-indexed field is a
# no-op), so it's called unconditionally, on both the fresh-create and
# already-exists paths.

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

load_dotenv()

COLLECTION_NAME = "zudyog_catalog"

# field name -> schema type, all keyword (exact-match) filters
PAYLOAD_INDEXES = {
    "chunk_id":    models.PayloadSchemaType.KEYWORD,
    "product_id":  models.PayloadSchemaType.KEYWORD,
    "chunk_type":  models.PayloadSchemaType.KEYWORD,
}


def create_payload_indexes(client: QdrantClient) -> None:
    for field_name, schema in PAYLOAD_INDEXES.items():
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field_name,
            field_schema=schema,
        )
        print(f"  payload index ensured: {field_name} ({schema})")


def create_collection() -> None:
    client = QdrantClient(
        url=os.environ["QDRANT_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
    )

    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        print(f"Collection '{COLLECTION_NAME}' already exists — skipping creation.")
        create_payload_indexes(client)
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "dense": models.VectorParams(
                size=1536,
                distance=models.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            # Declared empty in Chapter 2; BM25 values filled in Chapter 3.
            "bm25": models.SparseVectorParams(),
        },
    )
    print(f"Collection '{COLLECTION_NAME}' created.")
    print("  dense: 1536-dim cosine — ready for ingestion/dual_write.py")
    print("  bm25:  sparse field declared — populate with ingestion/bm25_backfill.py")
    create_payload_indexes(client)


if __name__ == "__main__":
    create_collection()
