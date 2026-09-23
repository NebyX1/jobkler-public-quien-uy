"""Pinned CPU embedding model identity shared by indexing and search."""

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REPOSITORY = "Qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q"
MODEL_REVISION = "faf4aa4225822f3bc6376869cb1164e8e3feedd0"
MODEL_FILE = "model_optimized.onnx"
MODEL_DIMENSION = 384
MODEL_MAX_SEQUENCE_TOKENS = 128
CHUNK_PROCESSOR_VERSION = "sentence-token-window-v1"
FASTEMBED_VERSION = "0.6.1"
