# fine_tune/train.py
# Source: Book 3, Chapter 5 — A Smaller Model That Knows the Catalog
# Fine-tunes BAAI/bge-small-en-v1.5 on the zUdyog catalog using TripletLoss.
#
# Prerequisites:
#   pip install sentence-transformers torch
#
# Runtime: ~38 minutes on a single A100 (one-time cost, ~₹240 compute).
# CPU training is possible but takes several hours — use GPU for the fine-tune.
#
# Before running (this project is standalone — the first two live in siblings):
#   1. Ensure ../shopbot-agent/evaluation/labeled_dataset.jsonl has ≥100 labeled queries.
#   2. Ensure Qdrant is populated: ../shopbot-ingest/'s ingestion.dual_write + bm25_backfill.
#   3. Log estimated cost in ../costs/cost_log.md before starting.
#
# Output: models/bge-small-zudyog-v1/
# Next step: python export/to_onnx_int8.py

try:
    from sentence_transformers import SentenceTransformer, losses
    from torch.utils.data import DataLoader
except ImportError:
    raise ImportError("pip install sentence-transformers torch to run fine_tune/train.py")

from fine_tune.build_dataset import build_triplets, load_labeled

# ── Model ────────────────────────────────────────────────────────────────────
# Start from the pre-trained checkpoint. The base model contributes general
# English semantic understanding. Fine-tuning adjusts the later layers for
# catalog-specific vocabulary: fabric, occasion, colour, care, price tier.
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# ── Data ─────────────────────────────────────────────────────────────────────
print("Loading labeled dataset and building triplets...")
triplets = build_triplets(load_labeled())
print(f"Training on {len(triplets)} triplets.")

train_dataloader = DataLoader(triplets, shuffle=True, batch_size=16)

# ── Loss ─────────────────────────────────────────────────────────────────────
# TripletLoss with cosine distance and margin 0.3.
# The margin means: the positive must score at least 0.3 closer (in cosine)
# than the hard negative. Smaller margin → less discrimination. Larger margin
# → harder to satisfy, risks degrading general performance.
train_loss = losses.TripletLoss(
    model=model,
    distance_metric=losses.TripletDistanceMetric.COSINE,
    triplet_margin=0.3,
)

# ── Training ─────────────────────────────────────────────────────────────────
OUTPUT_PATH = "models/bge-small-zudyog-v1"

model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=4,
    warmup_steps=100,
    output_path=OUTPUT_PATH,
    show_progress_bar=True,
)

print(f"Saved to {OUTPUT_PATH}")
print("Next: python export/to_onnx_int8.py")
