# Dockerfile
# Source: Book 3, Chapter 6 — Eight Bits Per Number; the ingest/agent/rerank split
# Combined inference container: cross-encoder (rerank) + ONNX INT8 embedder.
# Standalone project — all COPY paths are local to this directory, not the monorepo root.
#
# Container size: ~280 MB (vs 1.8 GB for PyTorch-only embedder + cross-encoder).
# Cold start: ~6 s (vs 41 s PyTorch; 9 s ONNX FP32).
# Deploy 3 replicas under campaign load (≥400 qpm) — see CLAUDE.md.

FROM python:3.11-slim

WORKDIR /app

# CPU-only torch build, to keep the image small — it's a transitive dependency
# of sentence-transformers and pip would otherwise pull the full CUDA build.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    sentence-transformers \
    onnxruntime \
    transformers \
    numpy

COPY main.py .
COPY onnx_embedder.py .

# Models baked into the image at build time — run fine_tune/train.py then
# export/to_onnx_int8.py first to produce models/bge-small-zudyog-v1-onnx-int8/.
COPY models/cross-encoder/ models/cross-encoder/
COPY models/bge-small-zudyog-v1-onnx-int8/ models/bge-small-zudyog-v1-onnx-int8/

# Pre-warm both models so the first request has no cold-start delay
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('models/cross-encoder')"
RUN python -c "from onnx_embedder import ONNXEmbedder; ONNXEmbedder('models/bge-small-zudyog-v1-onnx-int8')"

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
