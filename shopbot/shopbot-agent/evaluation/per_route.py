# evaluation/per_route.py
# Source: Book 3, Chapter 7 — What the Average Hides
# Per-route RAGAS evaluation.
#
# A blended RAGAS score across a graph-shaped pipeline averages performance
# over routes doing very different work. The blended number can move up or down
# in three different ways without telling you which route changed.
# This script groups the labeled dataset by the route each query takes, then
# scores each group independently. The blended number stays as a top-line;
# the per-route numbers carry the diagnostic signal.
#
# Minimum samples per route: 5. Routes below this are recorded but not scored —
# RAGAS metrics on very small samples are too noisy to be actionable.
#
# Cost: ~₹6 per run (₹1.50 pipeline + ₹4.50 RAGAS LLM calls for ~180 queries).

try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    )
    import ragas.executor as _rex
    from tqdm.auto import tqdm as _tqdm_auto

    # Same asyncio monkeypatch as evaluation/evaluate.py — see CLAUDE.md Section 18 Issue 1
    def _patched_executor_results(self):
        import asyncio
        if _rex.is_event_loop_running():
            try:
                import nest_asyncio
            except ImportError:
                raise ImportError("pip install nest_asyncio")
            if not self._nest_asyncio_applied:
                nest_asyncio.apply()
                self._nest_asyncio_applied = True

        coros = [f(*a, **kw) for f, a, kw, _ in self.jobs]
        max_workers = (self.run_config or _rex.RunConfig()).max_workers

        async def _run():
            futs = _rex.as_completed(coros, max_workers)
            results = []
            for fut_coro in _tqdm_auto(futs, desc=self.desc, total=len(self.jobs),
                                       leave=self.keep_progress_bar):
                results.append(await fut_coro)
            return results

        raw = asyncio.run(_run())
        return [r[1] for r in sorted(raw, key=lambda x: x[0])]

    _rex.Executor.results = _patched_executor_results
    RAGAS_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    RAGAS_AVAILABLE = False
    _ragas_error = e

import os
from collections import defaultdict
from datasets import Dataset
from dotenv import load_dotenv

from evaluation.labeled_dataset import load_labeled, DATASET_PATH
from evaluation.routes import derive_route
from memory.session import Session
from pipeline.graph import pipeline
from pipeline.state import PipelineState

load_dotenv()

MIN_ROUTE_SAMPLES = 5


def _new_eval_session() -> Session:
    """Fresh session per query — no cross-contamination between eval rows."""
    import uuid
    return Session(session_id=f"eval-{uuid.uuid4().hex[:8]}")


def evaluate_per_route(dataset_path: str = DATASET_PATH) -> dict[str, dict]:
    """
    Run labeled dataset through the live pipeline, group by route, score each group.
    Returns {route_label: {"n": int, "scored": bool, "F": float, ...}}.
    """
    rows = load_labeled(dataset_path)
    by_route: dict[str, list[dict]] = defaultdict(list)

    print(f"Running {len(rows)} queries through the pipeline...")
    for r in rows:
        initial: PipelineState = {
            "query":        r["query"],
            "session":      _new_eval_session(),
            "is_vague":     None,
            "crag_verdict": None,
            "sub_query":    None,
            "chunks":       None,
            "answer":       None,
        }
        final  = pipeline.invoke(initial)
        route  = derive_route(final)
        chunks = final.get("chunks") or []

        by_route[route].append({
            "question":     r["query"],
            "answer":       final["answer"] or "",
            "contexts":     [c.text for c in chunks],
            "ground_truth": r["reference_answer"],
        })

    results = {}
    for route, queries in sorted(by_route.items()):
        n = len(queries)
        if n < MIN_ROUTE_SAMPLES:
            results[route] = {"n": n, "scored": False}
            continue

        ds     = Dataset.from_list(queries)
        scored = evaluate(
            ds,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )
        results[route] = {
            "n":      n,
            "scored": True,
            "F":      round(scored["faithfulness"],      3),
            "AR":     round(scored["answer_relevancy"],  3),
            "CP":     round(scored["context_precision"], 3),
            "CR":     round(scored["context_recall"],    3),
        }

    return results


if __name__ == "__main__":
    if not RAGAS_AVAILABLE:
        print(f"ERROR: ragas not importable — {_ragas_error}")
        raise SystemExit(1)

    print("Per-route RAGAS evaluation (Book 3)...")
    print(f"Dataset: {DATASET_PATH}")
    print()
    results = evaluate_per_route()

    header = f"{'Route':<30}  {'n':>4}  {'F':>6}  {'AR':>6}  {'CP':>6}  {'CR':>6}"
    print(header)
    print("─" * len(header))
    for route, data in sorted(results.items()):
        if data["scored"]:
            watch = "  ← WATCH" if route == "D_hyde_partial" and data["F"] < 0.85 else ""
            print(
                f"{route:<30}  {data['n']:>4}  "
                f"{data['F']:>6.3f}  {data['AR']:>6.3f}  "
                f"{data['CP']:>6.3f}  {data['CR']:>6.3f}{watch}"
            )
        else:
            print(f"{route:<30}  {data['n']:>4}  (too few to score — need {MIN_ROUTE_SAMPLES}+)")
