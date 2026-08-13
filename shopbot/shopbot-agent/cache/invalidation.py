# cache/invalidation.py
# Source: Book 2, Chapter 7 — Paying Twice for the Same Answer
# Cache invalidation worker. Listens on Redis pub-sub for catalog-change events.
# When a chunk is re-indexed (e.g., a product description is edited), any cached
# answer that cited the affected SKU is removed from the semantic cache.
# Exact-match cache is cleared by its own 1h TTL (conservative but sufficient).
#
# Run as a long-lived process alongside the API:
#   python -m cache.invalidation

import json
import os
from dotenv import load_dotenv
from qdrant_client import models

load_dotenv()

CACHE_COLLECTION = "answer_cache"
CATALOG_CHANNEL  = "catalog.updated"


def invalidate_skus(affected_skus: list[str]) -> None:
    """Remove semantic-cache entries that cite any of the affected SKUs."""
    from infra.clients import qdrant_client
    if not affected_skus:
        return
    try:
        qdrant_client.delete(
            collection_name=CACHE_COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="retrieved_skus",
                            match=models.MatchAny(any=affected_skus),
                        )
                    ]
                )
            ),
        )
        print(f"Cache: invalidated entries for SKUs {affected_skus}")
    except Exception as e:
        print(f"Cache invalidation error: {e}")


def publish_catalog_update(skus: list[str]) -> None:
    """Publish a catalog-change event on the Redis channel. Called by ingestion scripts."""
    from infra.clients import r
    try:
        r.publish(CATALOG_CHANNEL, json.dumps({"skus": skus}))
    except Exception:
        pass  # Non-fatal: cache self-heals within TTL


def listen_for_catalog_changes() -> None:
    """Background worker — block forever, invalidating on each catalog-change message."""
    from infra.clients import r
    pubsub = r.pubsub()
    pubsub.subscribe(CATALOG_CHANNEL)
    print(f"Cache invalidation worker listening on '{CATALOG_CHANNEL}'...")
    for msg in pubsub.listen():
        if msg["type"] != "message":
            continue
        try:
            affected = json.loads(msg["data"])["skus"]
            invalidate_skus(affected)
        except Exception as e:
            print(f"Error processing catalog update: {e}")


if __name__ == "__main__":
    listen_for_catalog_changes()
