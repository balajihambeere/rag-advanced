# ingestion/dual_write.py
# Source: Book 2, Chapter 2 — Move Without Breaking Things
# Dual-write ingestion: each catalog chunk is indexed into both ChromaDB (old path)
# and Qdrant (new path) under the same logical chunk id.
# Run once for the initial migration; re-run with --force after any catalog change.
#
# Chunk IDs ("p001_identity") are converted to UUID strings for Qdrant using uuid5.
# The original string id is stored in the Qdrant payload as "chunk_id" for
# cross-store comparisons in the shadow-read phase (retrieval/shadow.py).

import os
import sys
import uuid
import chromadb
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

load_dotenv()

CHROMA_COLLECTION = "zudyog_products"
QDRANT_COLLECTION = "zudyog_catalog"

# Stable UUID namespace for converting Book 1 chunk string IDs to Qdrant UUIDs
_NS = uuid.UUID("00000000-0000-0000-0000-000000000001")


def chunk_id_to_qdrant_uuid(chunk_id: str) -> str:
    """Convert a Book 1 string chunk ID to a stable UUID string for Qdrant."""
    return str(uuid.uuid5(_NS, chunk_id))


# ── Clients ──────────────────────────────────────────────────────────────────
embeddings_model = OpenAIEmbeddings()  # text-embedding-3-small — same as Book 1

chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = chroma_client.get_or_create_collection(
    name=CHROMA_COLLECTION,
    metadata={"hnsw:space": "cosine"},
)

qdrant_client = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
)


def index_chunk(chunk: dict, embedding: list[float]) -> None:
    """
    Write one catalog chunk to ChromaDB and Qdrant.
    embedding is pre-computed by the caller (single embed call for all chunks).
    """
    # ChromaDB — upsert is safe to re-run
    chroma_collection.upsert(
        ids=[chunk["id"]],
        embeddings=[embedding],
        documents=[chunk["text"]],
        metadatas=[chunk["metadata"]],
    )

    # Qdrant — dense vector only; BM25 filled separately by bm25_backfill.py
    qdrant_client.upsert(
        collection_name=QDRANT_COLLECTION,
        points=[
            models.PointStruct(
                id=chunk_id_to_qdrant_uuid(chunk["id"]),
                vector={"dense": embedding},
                payload=chunk["metadata"] | {
                    "text":     chunk["text"],
                    "chunk_id": chunk["id"],   # original string id for shadow comparison
                },
            )
        ],
    )


def run_dual_ingest(force: bool = False) -> None:
    """
    Build chunks from the product catalog, embed all in a single call,
    then dual-write to ChromaDB and Qdrant.
    """
    from data.products import PRODUCTS
    from src.chunker import product_to_chunks

    qdrant_count = qdrant_client.count(QDRANT_COLLECTION, exact=True).count
    if qdrant_count > 0 and not force:
        print(f"Qdrant already has {qdrant_count} points — skipping (use --force to re-index).")
        return

    all_chunks = []
    for product in PRODUCTS:
        chunks = product_to_chunks(product)
        all_chunks.extend(chunks)
        print(f"  {product['name']}: {len(chunks)} chunks")

    print(f"\nTotal chunks: {len(all_chunks)}")
    print("Embedding all chunks in a single API call...")
    texts = [c["text"] for c in all_chunks]
    embeddings = embeddings_model.embed_documents(texts)

    print("Dual-writing to ChromaDB and Qdrant...")
    for chunk, embedding in zip(all_chunks, embeddings):
        index_chunk(chunk, embedding)

    print(f"Done: {len(all_chunks)} chunks in both stores.")
    print("Next step: python -m ingestion.bm25_backfill")


if __name__ == "__main__":
    force = "--force" in sys.argv
    run_dual_ingest(force=force)
