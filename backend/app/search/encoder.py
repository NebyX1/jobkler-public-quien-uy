import hashlib
import json
import math
import threading
from pathlib import Path

import numpy as np

from .model_manifest import (
    CHUNK_PROCESSOR_VERSION,
    FASTEMBED_VERSION,
    MODEL_DIMENSION,
    MODEL_FILE,
    MODEL_NAME,
    MODEL_REVISION,
    MODEL_REPOSITORY,
    MODEL_MAX_SEQUENCE_TOKENS,
)

_LOCK = threading.Lock()
_INSTANCES = {}


def model_directory(config):
    cache_root = Path(config["AI_SEARCH_ENCODER_CACHE"]).expanduser().resolve()
    return cache_root / "models" / f"{MODEL_REPOSITORY.replace('/', '--')}--{MODEL_REVISION}"


def prepare_model(config):
    from huggingface_hub import snapshot_download

    destination = model_directory(config)
    destination.parent.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=MODEL_REPOSITORY,
        revision=MODEL_REVISION,
        local_dir=str(destination),
        allow_patterns=[
            MODEL_FILE, "config.json", "ort_config.json", "tokenizer.json",
            "tokenizer_config.json", "special_tokens_map.json", "unigram.json",
        ],
        local_files_only=False,
    )
    model_file = destination / MODEL_FILE
    tokenizer_file = destination / "tokenizer.json"
    if not model_file.is_file() or not tokenizer_file.is_file():
        raise RuntimeError("La revisión fijada no contiene el modelo ONNX y tokenizer esperados.")
    digest = hashlib.sha256()
    with model_file.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    file_hash = digest.hexdigest()
    metadata = {
        "fastembed_version": FASTEMBED_VERSION,
        "repository": MODEL_REPOSITORY,
        "revision": MODEL_REVISION,
        "model_file": MODEL_FILE,
        "sha256": file_hash,
        "dimension": MODEL_DIMENSION,
        "maximum_sequence_tokens": MODEL_MAX_SEQUENCE_TOKENS,
        "chunk_processor_version": CHUNK_PROCESSOR_VERSION,
    }
    (destination / "jobkler-download-manifest.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return destination, metadata


def _new_encoder(config, *, allow_download=False):
    model_path = model_directory(config)
    if not (model_path / MODEL_FILE).is_file():
        if allow_download:
            model_path, _ = prepare_model(config)
        else:
            raise RuntimeError("El modelo semántico no está preparado. Ejecutá `flask search-model-prepare`.")
    from fastembed import TextEmbedding

    encoder = TextEmbedding(
        model_name=MODEL_NAME,
        cache_dir=config["AI_SEARCH_ENCODER_CACHE"],
        threads=config["AI_SEARCH_EMBEDDING_THREADS"],
        providers=["CPUExecutionProvider"],
        specific_model_path=str(model_path),
    )
    if encoder.model is None or encoder.model.tokenizer is None:
        raise RuntimeError("FastEmbed no inicializó el encoder o tokenizer fijado.")
    return encoder


def get_encoder(config, *, allow_download=False):
    key = (config["AI_SEARCH_ENCODER_CACHE"], config["AI_SEARCH_EMBEDDING_THREADS"], allow_download)
    with _LOCK:
        if key not in _INSTANCES:
            _INSTANCES[key] = _new_encoder(config, allow_download=allow_download)
        return _INSTANCES[key]


def encode_normalized(encoder, texts):
    if not texts:
        return np.empty((0, MODEL_DIMENSION), dtype=np.float32)
    vectors = np.asarray(list(encoder.embed(texts, batch_size=32, parallel=None)), dtype=np.float32)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    if vectors.shape != (len(texts), MODEL_DIMENSION) or not np.isfinite(vectors).all():
        raise ValueError("El encoder devolvió una dimensión o valores no válidos.")
    norms = np.linalg.norm(vectors, axis=1)
    if not np.isfinite(norms).all() or np.any(norms < 1e-12):
        raise ValueError("El encoder devolvió un vector sin norma válida.")
    return vectors / norms[:, None]


def token_chunks(encoder, profile_id, source_hash, source_fields):
    """Sentence-aware chunks with bounded, overlapped tokenizer windows and source offsets."""
    import re

    tokenizer = encoder.model.tokenizer
    result = []
    max_tokens = MODEL_MAX_SEQUENCE_TOKENS - 16
    overlap = 12
    for field, text in source_fields.items():
        if not text:
            continue
        units = [(m.start(), m.end()) for m in re.finditer(r"\S(?:[\s\S]*?\S)?(?=(?:[.!?]+\s+|\n+|$))", text)]
        if not units:
            units = [(0, len(text))]
        current_start = None
        current_end = None

        def add_chunk(start, end):
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            if end <= start:
                return
            literal = text[start:end]
            if len(tokenizer.encode(literal).ids) > MODEL_MAX_SEQUENCE_TOKENS:
                raise ValueError("La fragmentación no respetó el límite real de tokens del encoder.")
            chunk_number = len([item for item in result if item["source_field"] == field])
            chunk_id = hashlib.sha256(
                f"{profile_id}\x1f{source_hash}\x1f{field}\x1f{chunk_number}\x1f{start}\x1f{end}".encode("utf-8")
            ).hexdigest()
            result.append({
                "chunk_id": chunk_id, "profile_id": profile_id, "source_hash": source_hash,
                "source_field": field, "literal_text": literal, "start_char": start,
                "end_char": end, "encoder_model": MODEL_NAME, "encoder_revision": MODEL_REVISION,
                "vector_dimension": MODEL_DIMENSION, "vector_dtype": "float32-le",
            })

        for start, end in units:
            unit = text[start:end]
            if len(tokenizer.encode(unit).ids) <= max_tokens:
                if current_start is None:
                    current_start, current_end = start, end
                elif len(tokenizer.encode(text[current_start:end]).ids) <= max_tokens:
                    current_end = end
                else:
                    add_chunk(current_start, current_end)
                    current_start, current_end = start, end
                continue

            if current_start is not None:
                add_chunk(current_start, current_end)
                current_start = current_end = None

            encoded = tokenizer.encode(unit, add_special_tokens=False)
            offsets = encoded.offsets
            index = 0
            while index < len(offsets):
                stop = min(index + max_tokens, len(offsets))
                while stop > index + 1:
                    left = start + offsets[index][0]
                    right = start + offsets[stop - 1][1]
                    if len(tokenizer.encode(text[left:right]).ids) <= MODEL_MAX_SEQUENCE_TOKENS:
                        break
                    stop -= 1
                if stop <= index:
                    raise ValueError("No se pudo fragmentar una frase con el tokenizer del encoder.")
                left = start + offsets[index][0]
                right = start + offsets[stop - 1][1]
                add_chunk(left, right)
                if stop == len(offsets):
                    break
                index = max(index + 1, stop - overlap)

        if current_start is not None:
            add_chunk(current_start, current_end)
    return result


def vector_record(vector):
    normalized = np.asarray(vector, dtype=np.float32).reshape(-1)
    if normalized.size != MODEL_DIMENSION or not np.isfinite(normalized).all():
        raise ValueError("Vector incorrecto al persistir.")
    norm = float(np.linalg.norm(normalized))
    if not math.isfinite(norm) or abs(norm - 1.0) > 1e-3:
        raise ValueError("El vector almacenado debe estar normalizado.")
    return normalized.astype("<f4", copy=False).tobytes(order="C")
