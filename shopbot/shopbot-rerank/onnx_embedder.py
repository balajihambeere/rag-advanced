# onnx_embedder.py
# Source: Book 3, Chapter 6 — Eight Bits Per Number
# ONNX Runtime inference wrapper for the fine-tuned INT8 embedding model.
# Standalone — part of ../shopbot-rerank/, not ../shopbot-agent/'s infra/.
#
# Drop-in replacement for SentenceTransformer.encode() at ~2ms vs ~9ms (PyTorch)
# vs ~122ms (OpenAI API). Runs on CPUExecutionProvider; no GPU required.
#
# ONNX Runtime runs the forward pass and returns raw token embeddings.
# Pooling and L2 normalisation are handled here — sentence-transformers is not
# required at inference time (only at training/export time).

import numpy as np
from pathlib import Path

try:
    import onnxruntime as ort
    from transformers import AutoTokenizer
except ImportError:
    raise ImportError("pip install onnxruntime transformers to use ONNXEmbedder")


class ONNXEmbedder:
    """
    bge-small-zudyog-v1 in ONNX INT8.  ~2 ms per embed on CPU.
    Dimensions: 384.  L2-normalised output (cosine-ready).
    """

    def __init__(self, model_dir: str):
        model_path = Path(model_dir) / "model_quantized.onnx"
        if not model_path.exists():
            raise FileNotFoundError(
                f"ONNX model not found at {model_path}. "
                "Run fine_tune/train.py then export/to_onnx_int8.py first."
            )
        self.session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)

    def encode(self, text: str, normalize: bool = True) -> np.ndarray:
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np",
        )
        outputs = self.session.run(None, {
            "input_ids":      inputs["input_ids"],
            "attention_mask": inputs["attention_mask"],
        })
        # Mean pooling — mask out padded positions, average the rest
        token_embeddings = outputs[0]
        mask = np.expand_dims(inputs["attention_mask"], -1).astype(np.float32)
        sum_embeddings = (token_embeddings * mask).sum(axis=1)
        sum_mask = np.maximum(mask.sum(axis=1), 1e-9)
        pooled = sum_embeddings / sum_mask

        if normalize:
            pooled = pooled / np.linalg.norm(pooled, axis=-1, keepdims=True)

        return pooled[0]
