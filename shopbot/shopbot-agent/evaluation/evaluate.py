# evaluation/evaluate.py
# Source: Book 2, Chapter 8 — You Cannot Improve What You Do Not Measure
# Runs all four RAGAS dimensions against the labeled dataset.
# Faithfulness and Context Precision: reference-free (no ground truth needed).
# Answer Relevance and Context Recall: require the labeled dataset's reference answers
# and gold_chunk_ids — the two dimensions deferred from Book 1.
#
# Book 2 baseline (Chapter 6 architecture): F=0.83, AR=0.81, CP=0.88, CR=0.79
# Book 1 baseline: F=0.7494, CP=0.6417 (reference-free only)

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

    # Python 3.12+ asyncio monkeypatch for ragas 0.1.22 (same fix as Book 1)
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

import json
import os
from datasets import Dataset
from dotenv import load_dotenv

from retrieval.multi_query import retrieve_multi
from retrieval.prompt_multi import build_prompt_multi
from retrieval.system_prompt import SHOPBOT_SYSTEM_B2
from infra.clients import llm

load_dotenv()

DATASET_PATH = os.path.join(os.path.dirname(__file__), "labeled_dataset.jsonl")


def load_dataset(path: str = DATASET_PATH) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def answer_for_eval(query: str) -> tuple[str, list]:
    """Run one query through the full Book 2 pipeline. Returns (answer, chunks)."""
    retrieved, sub_queries = retrieve_multi(query, session=None)
    if not retrieved:
        answer = (
            "I don't have a product that matches that specifically. "
            "Could you describe what you're looking for differently, "
            "or contact our team at support@example.com?"
        )
    else:
        user_msg = build_prompt_multi(query, sub_queries, retrieved, session=None)
        answer = llm.complete(system=SHOPBOT_SYSTEM_B2, user=user_msg)
    return answer, retrieved


def run_evaluation(dataset_path: str = DATASET_PATH) -> dict:
    """Run all four RAGAS dimensions. Returns {"F": ..., "AR": ..., "CP": ..., "CR": ...}."""
    rows = load_dataset(dataset_path)

    questions, answers, contexts, references = [], [], [], []
    for row in rows:
        answer, chunks = answer_for_eval(row["query"])
        questions.append(row["query"])
        answers.append(answer)
        contexts.append([c.text for c in chunks] if chunks else [""])
        references.append(row["reference_answer"])

    ds = Dataset.from_dict({
        "question":    questions,
        "answer":      answers,
        "contexts":    contexts,
        "ground_truth": references,
    })

    result = evaluate(
        ds,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )

    return {
        "F":  round(result["faithfulness"],      3),
        "AR": round(result["answer_relevancy"],  3),
        "CP": round(result["context_precision"], 3),
        "CR": round(result["context_recall"],    3),
    }


if __name__ == "__main__":
    if not RAGAS_AVAILABLE:
        print(f"ERROR: ragas not importable — {_ragas_error}")
        raise SystemExit(1)

    print("Running full RAGAS evaluation (all 4 dimensions)...")
    print(f"Dataset: {DATASET_PATH}")
    print()
    scores = run_evaluation()
    print(f"Faithfulness:       {scores['F']:.3f}  (Book 2 target: 0.83)")
    print(f"Answer Relevance:   {scores['AR']:.3f}  (Book 2 target: 0.81)")
    print(f"Context Precision:  {scores['CP']:.3f}  (Book 2 target: 0.88)")
    print(f"Context Recall:     {scores['CR']:.3f}  (Book 2 target: 0.79)")

    _mlflow_uri = os.getenv("MLFLOW_TRACKING_URI")
    if _mlflow_uri:
        try:
            import mlflow
            from datetime import datetime
            run_id = "run_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            mlflow.set_tracking_uri(_mlflow_uri)
            mlflow.set_experiment("shopbot-eval")
            with mlflow.start_run(run_name=run_id):
                mlflow.log_params({
                    "model_embed":   "bge-small-zudyog-v1-onnx-int8",
                    "model_llm":     "gpt-4o-mini",
                    "ragas_version": "0.1.22",
                    "total_queries": len(load_dataset()),
                    "dataset_path":  DATASET_PATH,
                })
                mlflow.log_metrics({
                    "faithfulness":      scores["F"],
                    "answer_relevancy":  scores["AR"],
                    "context_precision": scores["CP"],
                    "context_recall":    scores["CR"],
                })
            print(f"  MLflow  → {_mlflow_uri}  (experiment: shopbot-eval)")
        except Exception as _mlflow_err:
            print(f"  MLflow logging skipped: {_mlflow_err}")
