# loadtest/harness.py
# Source: Book 2, Chapter 9 — Real Production
# Async load-test harness. Issues queries at a configurable rate (queries-per-minute)
# for a configurable duration, then reports p50 and p95 latency.
#
# Query pool: labeled_dataset.jsonl + any failed-query log (if present).
# Run: python -m loadtest.harness --qpm 500 --duration 60
#
# Chapter 9 findings:
#   50 qpm   → 380ms p50 (baseline)
#   500 qpm  → 1200ms p50 (cross-encoder bottleneck — move to separate service)
#   500 qpm* → 420ms p50 (after cross-encoder split, Chapter 9)
#   1000 qpm → 580ms p50 (Qdrant doubled, Chapter 9)
#   * The target for a campaign day (7000 queries).

import asyncio
import json
import os
import random
import statistics
import time
import argparse

import httpx

SHOPBOT_URL = os.environ.get("SHOPBOT_URL", "http://localhost:8000")


def load_query_pool(*paths: str) -> list[str]:
    queries = []
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if "query" in row:
                        queries.append(row["query"])
                except json.JSONDecodeError:
                    pass
    return queries or ["Does the silk saree come with a blouse?"]  # fallback


QUERIES: list[str] = load_query_pool(
    "evaluation/labeled_dataset.jsonl",
    "logs/failed_queries.jsonl",
)


async def fire_one(client: httpx.AsyncClient, query: str) -> float:
    t0 = time.perf_counter()
    r = await client.post(
        f"{SHOPBOT_URL}/ask",
        json={"question": query, "session_id": f"loadtest-{random.randint(1, 99)}"},
        timeout=30.0,
    )
    r.raise_for_status()
    return time.perf_counter() - t0


async def _record(client, query, sink):
    try:
        sink.append(await fire_one(client, query))
    except Exception:
        sink.append(float("inf"))  # count failures as infinite latency


async def run(qpm: int, duration_s: int) -> None:
    interval = 60.0 / qpm
    latencies: list[float] = []

    async with httpx.AsyncClient() as client:
        deadline = time.time() + duration_s
        while time.time() < deadline:
            query = random.choice(QUERIES)
            asyncio.create_task(_record(client, query, latencies))
            await asyncio.sleep(interval)

    # Wait briefly for in-flight requests
    await asyncio.sleep(5)

    valid = [l for l in latencies if l != float("inf")]
    errors = len(latencies) - len(valid)

    if valid:
        p50 = statistics.median(valid)
        p95 = statistics.quantiles(valid, n=20)[18]
        print(f"qpm={qpm}  n={len(latencies)}  errors={errors}  "
              f"p50={p50*1000:.0f}ms  p95={p95*1000:.0f}ms")
    else:
        print(f"qpm={qpm}  all {len(latencies)} requests failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qpm",      type=int, default=50,   help="Queries per minute")
    parser.add_argument("--duration", type=int, default=60,   help="Test duration in seconds")
    parser.add_argument("--url",      type=str, default="",   help="ShopBot API base URL")
    args = parser.parse_args()

    if args.url:
        SHOPBOT_URL = args.url

    print(f"Load test: {args.qpm} qpm for {args.duration}s → {SHOPBOT_URL}/ask")
    asyncio.run(run(args.qpm, args.duration))
