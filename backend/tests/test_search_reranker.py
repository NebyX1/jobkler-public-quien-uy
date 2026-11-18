import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
from requests import ConnectionError

from app.search import reranker


def fingerprint(content):
    return len(content), hashlib.sha256(content).hexdigest()


class RerankerPreparationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="jobkler-reranker-test-")
        self.addCleanup(temporary.cleanup)
        self.config = {"AI_SEARCH_RERANKER_CACHE": temporary.name, "AI_SEARCH_RERANKER_THREADS": 2}
        self.directory = reranker.reranker_directory(self.config)

    def write_cache_file(self, name, content):
        path = self.directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def test_verified_cache_is_available_without_network(self):
        content = b"pinned tokenizer"
        self.write_cache_file("tokenizer.json", content)
        with patch.object(reranker, "RERANKER_FILES", {"tokenizer.json": fingerprint(content)}), patch(
            "huggingface_hub.hf_hub_download"
        ) as download:
            self.assertEqual(reranker.prepare_reranker(self.config), self.directory)
        download.assert_not_called()

    def test_corrupt_file_is_replaced_using_the_pinned_revision(self):
        filename = reranker.RERANKER_ONNX
        content = b"new binary"
        self.write_cache_file(filename, b"bad binary")

        def download_file(**kwargs):
            self.write_cache_file(kwargs["filename"], content)

        with patch.object(reranker, "RERANKER_FILES", {filename: fingerprint(content)}), patch(
            "huggingface_hub.hf_hub_download", side_effect=download_file
        ) as download:
            reranker.prepare_reranker(self.config)
        self.assertTrue(download.call_args.kwargs["force_download"])
        self.assertEqual(download.call_args.kwargs["revision"], reranker.RERANKER_REVISION)
        self.assertEqual((self.directory / filename).read_bytes(), content)

    def test_direct_download_handles_hub_transport_failure(self):
        filename = reranker.RERANKER_ONNX
        content = b"local model"
        response = MagicMock()
        response.__enter__.return_value = response
        response.iter_content.return_value = [content[:4], content[4:]]
        with patch.object(reranker, "RERANKER_FILES", {filename: fingerprint(content)}), patch(
            "huggingface_hub.hf_hub_download", side_effect=ConnectionError("transport unavailable")
        ), patch("requests.get", return_value=response) as get:
            reranker.prepare_reranker(self.config)
        self.assertIn(reranker.RERANKER_REVISION, get.call_args.args[0])
        self.assertEqual((self.directory / filename).read_bytes(), content)

    def test_invalid_direct_download_does_not_replace_the_artifact(self):
        filename = reranker.RERANKER_ONNX
        self.write_cache_file(filename, b"old cache")
        response = MagicMock()
        response.__enter__.return_value = response
        response.iter_content.return_value = [b"bad model"]
        with patch.object(reranker, "RERANKER_FILES", {filename: fingerprint(b"new model")}), patch(
            "huggingface_hub.hf_hub_download", side_effect=ConnectionError("transport unavailable")
        ), patch("requests.get", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "revisión fijada"):
                reranker.prepare_reranker(self.config)
        self.assertEqual((self.directory / filename).read_bytes(), b"old cache")
        self.assertEqual(list((self.directory / filename).parent.iterdir()), [self.directory / filename])


class RerankerInferenceTest(unittest.TestCase):
    def make_model(self):
        model = reranker._CrossEncoder.__new__(reranker._CrossEncoder)
        row = SimpleNamespace(ids=[0, 2], attention_mask=[1, 1])
        model.tokenizer = MagicMock()
        model.tokenizer.encode_batch.side_effect = lambda pairs: [row] * len(pairs)
        model.session = MagicMock()
        model.inputs = {"input_ids": "ids", "attention_mask": "attention_mask"}
        return model

    def test_logits_keep_pair_order_across_batches(self):
        model = self.make_model()
        model.session.run.side_effect = [[np.arange(8)[:, None]], [np.array([[-4.0]])]]
        passages = [f"perfil {index}" for index in range(9)]
        self.assertEqual(model.score("pata de cama", passages), [*range(8), -4.0])
        self.assertEqual(model.tokenizer.encode_batch.call_args.args[0], [("pata de cama", passages[-1])])
        inputs = model.session.run.call_args.args[1]
        self.assertEqual(inputs["input_ids"].dtype, np.int64)
        self.assertEqual(inputs["attention_mask"].shape, (1, 2))

    def test_nonfinite_or_missing_logit_is_rejected(self):
        for logits in (np.array([[float("nan")]]), np.empty((0, 1))):
            with self.subTest(logits=logits):
                model = self.make_model()
                model.session.run.return_value = [logits]
                with self.assertRaisesRegex(ValueError, "puntajes"):
                    model.score("pata de cama", ["reparación de muebles"])

    def test_loading_is_lazy_and_reused_for_matching_configuration(self):
        config = {"AI_SEARCH_RERANKER_CACHE": ".", "AI_SEARCH_RERANKER_THREADS": 2}
        with patch.object(reranker, "_MODELS", {}), patch.object(reranker, "_CrossEncoder") as constructor:
            model = constructor.return_value
            model.score.return_value = [1.5]
            self.assertEqual(reranker.rerank_scores("consulta", [], {}), [])
            constructor.assert_not_called()
            self.assertEqual(reranker.rerank_scores("consulta", ["perfil"], config), [1.5])
            self.assertEqual(reranker.rerank_scores("consulta", ["otro perfil"], config), [1.5])
            constructor.assert_called_once_with(reranker.reranker_directory(config), 2)


if __name__ == "__main__":
    unittest.main()
