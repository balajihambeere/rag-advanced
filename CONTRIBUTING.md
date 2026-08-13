# Contributing to The Senior AI Engineer

Thanks for considering a contribution. This repo is the real, working codebase behind Book 3 of the Zudyog RAG Mastery Series — it's meant to stay a runnable, honest reference implementation, not a polished framework. Contributions that keep it that way are the most welcome kind.

## Ground rules

- **Keep it runnable.** Every change should leave the five-step quickstart in [`README.md`](README.md) working from a clean clone: `shopbot-ingest` populates Qdrant, `shopbot-training` produces a model, `shopbot-rerank` serves it via Docker, `shopbot-agent` serves `/ask` through the LangGraph pipeline, `zudyog-fashion` talks to it.
- **Keep it honest.** Concrete rules this codebase already holds itself to — don't quietly loosen any of them in a PR:
  - The cross-encoder confidence floor (`RERANK_CONFIDENCE_FLOOR = 0.55` in `shopbot/shopbot-agent/retrieval/memory_aware.py`) stays where it is. A support fallback is correct behavior when nothing clears it.
  - `shopbot-agent` has no in-process fallback for reranking or embedding — both are HTTP-only calls to `shopbot-rerank` (`RERANK_URL` is required, no default that silently degrades). This was a real bug fixed during the ingest/agent/rerank/training split; don't reintroduce it.
  - The HyDE category-anchor prompt and the CRAG raw-query sub-query behavior (`shopbot-agent/retrieval/hyde.py`, `crag.py`) are Chapter 8 production fixes for specific route regressions found under campaign load. Don't revert either without re-running per-route eval and showing the routes they fixed didn't regress.
  - Per-route RAGAS scores aren't claimed "met" for a route with fewer than 5 labeled samples — see `shopbot-agent/evaluation/per_route.py`. Don't pad the labeled dataset with easy queries to clear that bar; sample from the failed-query log instead.
  - If you think something structural should change instead, open an issue first rather than quietly "fixing" it in a PR.
- **Small PRs over big ones.** A focused PR that does one thing is easier to review and merge than a large one that touches many files — especially here, where a change to `shopbot-agent` might need a matching change in `shopbot-rerank`'s HTTP contract, `shopbot-ingest`'s Qdrant schema, or `shopbot-training`'s model output shape.

## Good first issues

If you're looking for a place to start, these are real gaps in the repo today — genuinely useful, and scoped small enough for a first PR:

1. **Add a GitHub Actions CI workflow.** There's currently no CI at all across any of the four Python projects — even a job that installs each `requirements.txt` and runs `python -m py_compile` (or a real smoke test, once #2 exists) on push/PR would catch broken dependency pins and import errors before they reach `main`.
2. **Add pytest unit tests for `shopbot-ingest/src/chunker.py`.** It's a pure function (`product_to_chunks()` — no API calls, no network), which makes it the easiest part of the pipeline to actually unit test — and right now it has zero test coverage anywhere in the repo.
3. **Add Dockerfiles for `shopbot-ingest`, `shopbot-agent`, and `shopbot-training`.** Only `shopbot-rerank` has one today. There's no containerized path to run the ingest pipeline, the API itself, or the fine-tune/export pipeline — for the API in particular, that's usually the first thing people reach for before setting up Railway.
4. **Automate the `shopbot-training` → `shopbot-rerank` model handoff.** Today it's two manual `cp`/export commands (see the Quickstart in `README.md`) — easy to get wrong (wrong path, stale model) since nothing checks the copy actually happened before `docker build` runs. A small script (or a `Makefile` target) that copies both model directories and fails loudly if either is missing would remove that manual step.
5. **Resolve the embedding-dimension mismatch between `shopbot-ingest` and the live pipeline.** `infra/qdrant_setup.py` provisions the `zudyog_catalog` collection at 1536-dim (Book 2's `text-embedding-3-small`), but the live pipeline is designed around a 384-dim fine-tuned model served by `shopbot-rerank`. Until this is resolved, a full re-ingest against a freshly-provisioned collection will fail on the first upsert. Fixing this needs a decision (documented in an issue first, per the Ground Rules above) on whether `ingestion/dual_write.py` should call `shopbot-rerank`'s `/embed` endpoint instead of the OpenAI API.

Open an issue to claim one before starting, so two people don't end up duplicating work.

## Reporting bugs

Please include:
- Which project it's in — `shopbot-ingest`, `shopbot-agent`, `shopbot-rerank`, `shopbot-training`, or `zudyog-fashion` — each has its own `venv`/`.env`, so bugs are usually scoped to one
- What you ran (exact command) and what you expected vs. what happened
- Your Python/Node/Docker version, and whether the machine has a GPU (relevant for `shopbot-training`)
- Whether it reproduces on a clean clone (rules out local `venv`/`chroma_db`/`models`/cache state issues)

## Pull requests

1. Fork, branch off `main`
2. Make your change; keep commits focused
3. There's no automated test suite yet (see Good First Issues #1–2 above) — until there is, verify manually: start the affected project(s) per the Quickstart in `README.md` and confirm `/health` responds and a sample `/ask` query still returns a grounded answer
4. If you touched `shopbot-agent/retrieval/`, `shopbot-agent/pipeline/`, `shopbot-agent/cache/`, or the system prompt, run `python -m evaluation.per_route` from `shopbot-agent/` and include the before/after per-route scores in your PR description — a change that improves one route while degrading another is not an improvement
5. If you touched `shopbot-training/` or the model itself, log estimated GPU/API cost in `costs/cost_log.md` before running anything, per that project's own rules
6. Open the PR with a short description of *why*, not just *what* — the reasoning is what makes review fast

## Questions

Open a discussion or issue on this repository — no question is too basic.
