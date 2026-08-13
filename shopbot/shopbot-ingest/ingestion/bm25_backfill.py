# ingestion/bm25_backfill.py
# Source: Book 2, Chapter 3 — Two Signals Are Better Than One
# Populates the BM25 sparse vector field in Qdrant for every catalog chunk.
# Run after dual_write.py has placed dense vectors. Safe to re-run.
#
# Why a separate script: embedding all text into dense vectors is one API call
# (expensive, done once in dual_write.py). BM25 is a local sparse encoding
# with no API cost — safe to run on-the-fly or in batch.

import os
import sys
import uuid
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from fastembed import SparseTextEmbedding

load_dotenv()

QDRANT_COLLECTION = "zudyog_catalog"
_NS = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _to_uuid(chunk_id: str) -> str:
    return str(uuid.uuid5(_NS, chunk_id))


def backfill_bm25() -> None:
    """Compute and store BM25 sparse vectors for every catalog chunk."""
    from data.products import PRODUCTS
    from src.chunker import product_to_chunks

    qdrant_client = QdrantClient(
        url=os.environ["QDRANT_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
    )
    bm25 = SparseTextEmbedding(model_name="Qdrant/bm25")

    all_chunks = []
    for product in PRODUCTS:
        all_chunks.extend(product_to_chunks(product))

    print(f"BM25 backfill: {len(all_chunks)} chunks")

    for i, chunk in enumerate(all_chunks, 1):
        sparse = next(iter(bm25.embed([chunk["text"]])))
        qdrant_client.update_vectors(
            collection_name=QDRANT_COLLECTION,
            points=[
                models.PointVectors(
                    id=_to_uuid(chunk["id"]),
                    vector={
                        "bm25": models.SparseVector(
                            indices=sparse.indices.tolist(),
                            values=sparse.values.tolist(),
                        )
                    },
                )
            ],
        )
        if i % 50 == 0 or i == len(all_chunks):
            print(f"  {i}/{len(all_chunks)} done")

    print("BM25 backfill complete.")
    print("Hybrid search (Chapter 3) is now active.")


if __name__ == "__main__":
    backfill_bm25()
