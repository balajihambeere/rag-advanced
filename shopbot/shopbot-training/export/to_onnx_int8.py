# export/to_onnx_int8.py
# Source: Book 3, Chapter 6 — Eight Bits Per Number
# Exports the fine-tuned bge-small model to ONNX INT8 (dynamic quantisation).
#
# Prerequisites:
#   pip install optimum[onnxruntime]
#   models/bge-small-zudyog-v1/ must exist (run fine_tune/train.py first)
#
# Step 1 — ONNX FP32 export via Optimum's ORTModelForFeatureExtraction.
# Step 2 — INT8 dynamic quantisation using AVX-512 VNNI config.
#
# Dynamic quantisation (is_static=False) computes scale factors at inference
# time from live activations. No calibration dataset required. Quality cost
# vs static quantisation is negligible for embedding models.
#
# AVX-512 VNNI is required on the EXPORT machine only; the inference machine
# can be any CPU. On ARM or older x86, swap avx512_vnni for an appropriate
# AutoQuantizationConfig preset.
#
# RAGAS cost of INT8: CP drops from 0.91 (FP32) to 0.90 — one point for
# 2× latency gain (4ms → 2ms) and 4× container size reduction (135MB → 33MB).
#
# Output: models/bge-small-zudyog-v1-onnx-int8/model_quantized.onnx  (~33 MB)
# Next steps (cross-project — this output is consumed by two siblings):
#   - Copy models/bge-small-zudyog-v1-onnx-int8/ (and a models/cross-encoder/
#     export of the cross-encoder checkpoint) into ../shopbot-rerank/models/
#     before building that project's Docker image — it bakes the model files
#     in at build time, it does not fetch them at runtime.
#   - Update Qdrant collection to 384-dim: in ../shopbot-ingest/,
#     python -m infra.qdrant_setup (after dropping the old collection)
#   - Re-ingest catalog: in ../shopbot-ingest/,
#     python -m ingestion.dual_write && python -m ingestion.bm25_backfill
#   - Validate with 1 query before running full eval

try:
    from optimum.onnxruntime import ORTModelForFeatureExtraction, ORTQuantizer
    from optimum.onnxruntime.configuration import AutoQuantizationConfig
    from transformers import AutoTokenizer
except ImportError:
    raise ImportError("pip install optimum[onnxruntime] transformers to run export/to_onnx_int8.py")

INPUT_MODEL  = "models/bge-small-zudyog-v1"
ONNX_FP32    = "models/bge-small-zudyog-v1-onnx"
ONNX_INT8    = "models/bge-small-zudyog-v1-onnx-int8"

# ── Step 1: Export to ONNX FP32 ─────────────────────────────────────────────
print("Exporting to ONNX FP32...")
model = ORTModelForFeatureExtraction.from_pretrained(INPUT_MODEL, export=True)
model.save_pretrained(ONNX_FP32)

tokenizer = AutoTokenizer.from_pretrained(INPUT_MODEL)
tokenizer.save_pretrained(ONNX_FP32)
print(f"  Saved ONNX FP32 to {ONNX_FP32}")

# ── Step 2: Quantise to INT8 (dynamic, AVX-512 VNNI) ────────────────────────
print("Quantising to INT8 (dynamic)...")
quantizer = ORTQuantizer.from_pretrained(ONNX_FP32)
qconfig   = AutoQuantizationConfig.avx512_vnni(is_static=False)
quantizer.quantize(
    save_dir=ONNX_INT8,
    quantization_config=qconfig,
)
print(f"  Saved ONNX INT8 to {ONNX_INT8}/model_quantized.onnx")

print("\nExport complete.")
print("Next: drop zudyog_catalog + answer_cache in Qdrant, re-run qdrant_setup, re-ingest.")
