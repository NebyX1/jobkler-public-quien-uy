"""Local, CPU-only cross-encoder for comparing a request with profile evidence."""

import hashlib
import tempfile
import threading
from pathlib import Path

import numpy as np


RERANKER_REPOSITORY = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
RERANKER_REVISION = "1427fd652930e4ba29e8149678df786c240d8825"
RERANKER_ONNX = "onnx/model_quint8_avx2.onnx"
RERANKER_TOKENIZER = "tokenizer.json"
RERANKER_FILES = {
    RERANKER_ONNX: (118_620_016, "6c2513767fb63d008a4377bef7a7a3555433d9436342bb53e35a3a72ffc52d4b"),
    RERANKER_TOKENIZER: (17_082_660, "62c24cdc13d4c9952d63718d6c9fa4c287974249e16b7ade6d5a85e7bbb75626"),
}

_LOAD_LOCK = threading.Lock()
_MODELS = {}
_BATCH_SIZE = 8
_MAX_TOKENS = 256
_INPUT_ATTRIBUTES = {"input_ids": "ids", "attention_mask": "attention_mask", "token_type_ids": "type_ids"}


def reranker_directory(config):
    name = RERANKER_REPOSITORY.rsplit("/", 1)[-1]
    return Path(config["AI_SEARCH_RERANKER_CACHE"]).expanduser().resolve() / f"{name}--{RERANKER_REVISION}"


def _file_matches(path, expected):
    size, sha256 = expected
    try:
        if not path.is_file() or path.stat().st_size != size:
            return False
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest() == sha256
    except FileNotFoundError:
        return False


def _download_direct(url, target, expected):
    import requests

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as staging:
        temporary = Path(staging) / target.name
        with requests.get(url, params={"download": "true"}, stream=True, timeout=(5, 30)) as response:
            response.raise_for_status()
            with temporary.open("wb") as stream:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    stream.write(chunk)
        if not _file_matches(temporary, expected):
            raise RuntimeError(f"El archivo {target.name} no coincide con la revisión fijada del reranker.")
        temporary.replace(target)


def prepare_reranker(config):
    """Verify the local cache and download only missing or invalid pinned artifacts."""
    from huggingface_hub import hf_hub_download, hf_hub_url
    from requests import RequestException

    directory = reranker_directory(config)
    for filename, expected in RERANKER_FILES.items():
        target = directory / filename
        if _file_matches(target, expected):
            continue
        try:
            hf_hub_download(
                repo_id=RERANKER_REPOSITORY, filename=filename, revision=RERANKER_REVISION,
                local_dir=directory, force_download=target.exists(), etag_timeout=10,
            )
        except (OSError, RequestException, RuntimeError, ValueError):
            pass
        else:
            if _file_matches(target, expected):
                continue
        # The standard HTTPS path avoids Xet transport issues on some installations.
        url = hf_hub_url(RERANKER_REPOSITORY, filename=filename, revision=RERANKER_REVISION)
        _download_direct(url, target, expected)
    return directory


class _CrossEncoder:
    def __init__(self, directory, threads):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        if not all(_file_matches(directory / filename, expected) for filename, expected in RERANKER_FILES.items()):
            raise RuntimeError("El reranker local falta o está dañado. Ejecutá `flask search-reranker-prepare`.")
        self.tokenizer = Tokenizer.from_file(str(directory / RERANKER_TOKENIZER))
        self.tokenizer.enable_truncation(max_length=_MAX_TOKENS)
        self.tokenizer.enable_padding(pad_id=self.tokenizer.token_to_id("<pad>"), pad_token="<pad>")

        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(directory / RERANKER_ONNX), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.inputs = {item.name: _INPUT_ATTRIBUTES[item.name] for item in self.session.get_inputs()}

    def score(self, query, passages):
        scores = []
        for start in range(0, len(passages), _BATCH_SIZE):
            batch = self.tokenizer.encode_batch([(query, passage) for passage in passages[start:start + _BATCH_SIZE]])
            inputs = {
                name: np.asarray([getattr(row, attribute) for row in batch], dtype=np.int64)
                for name, attribute in self.inputs.items()
            }
            logits = self.session.run(None, inputs)[0].reshape(-1)
            if len(logits) != len(batch) or not np.isfinite(logits).all():
                raise ValueError("El reranker devolvió una cantidad o puntajes no válidos.")
            scores.extend(logits.tolist())
        return scores


def rerank_scores(query: str, passages: list[str], config) -> list[float]:
    """Return one raw logit per passage in input order. Loading is always offline."""
    if not passages:
        return []
    key = (reranker_directory(config), config["AI_SEARCH_RERANKER_THREADS"])
    with _LOAD_LOCK:
        if key not in _MODELS:
            _MODELS[key] = _CrossEncoder(*key)
        model = _MODELS[key]
    return model.score(query, passages)
