import importlib.util
import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ENGINE_FILE = Path(__file__).resolve().parents[2] / "ai-engine" / "engine.py"
spec = importlib.util.spec_from_file_location("jobkler_local_engine", ENGINE_FILE)
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


class AiEngineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="jobkler-engine-test-")
        self.root = Path(self.temp.name)
        self.engine_dir = self.root / "ai-engine"
        self.engine_dir.mkdir()
        self.backend_env = self.root / "backend.env"
        self.backend_env.write_text("AI_LLM_MANAGED=true\nAI_LLM_API_KEY=\n", encoding="utf-8")
        self.engine_env = self.engine_dir / ".env"
        (self.engine_dir / ".env.example").write_text("LLM_API_KEY=\n", encoding="utf-8")
        self.patches = [
            patch.object(engine, "ROOT", self.root),
            patch.object(engine, "ENGINE_DIR", self.engine_dir),
            patch.object(engine, "ENGINE_ENV", self.engine_env),
            patch.object(engine, "STATE_FILE", self.root / ".jobkler" / "ai-engine.pid"),
            patch.dict(os.environ, {"JOBKLER_ENV_FILE": str(self.backend_env)}, clear=True),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_prepare_generates_shared_secret_and_preserves_it(self):
        self.assertTrue(engine.prepare()["managed"])
        backend_key = engine.read_env(self.backend_env)["AI_LLM_API_KEY"]
        self.assertGreaterEqual(len(backend_key), 32)
        self.assertEqual(engine.read_env(self.engine_env)["LLM_API_KEY"], backend_key)
        self.assertTrue(engine.prepare()["managed"])
        self.assertEqual(engine.read_env(self.backend_env)["AI_LLM_API_KEY"], backend_key)

    def test_prepare_rejects_conflicting_secrets_without_overwriting_them(self):
        self.backend_env.write_text("AI_LLM_API_KEY=" + "a" * 40 + "\n", encoding="utf-8")
        self.engine_env.write_text("LLM_API_KEY=" + "b" * 40 + "\n", encoding="utf-8")
        with self.assertRaisesRegex(engine.EngineError, "no coinciden"):
            engine.prepare()
        self.assertEqual(engine.read_env(self.backend_env)["AI_LLM_API_KEY"], "a" * 40)
        self.assertEqual(engine.read_env(self.engine_env)["LLM_API_KEY"], "b" * 40)

    def test_external_mode_does_not_create_or_start_a_local_engine(self):
        self.backend_env.write_text("AI_LLM_MANAGED=false\n", encoding="utf-8")
        self.assertFalse(engine.start()["managed"])
        self.assertFalse(self.engine_env.exists())
        self.assertFalse(engine.STATE_FILE.exists())

    def test_occupied_port_never_stops_an_unrelated_server(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            self.backend_env.write_text(f"AI_LLM_MANAGED=true\nAI_LLM_BASE_URL=http://127.0.0.1:{port}/v1\n", encoding="utf-8")
            (self.engine_dir / ".env.example").write_text(f"LLM_PORT={port}\nLLM_API_KEY=\n", encoding="utf-8")
            (self.engine_dir / "bin").mkdir()
            (self.engine_dir / "models").mkdir()
            binary = "llama-server.exe" if os.name == "nt" else "llama-server"
            (self.engine_dir / "bin" / binary).touch()
            (self.engine_dir / "models" / engine.DEFAULT_ALIAS).touch()
            with self.assertRaisesRegex(engine.EngineError, "ocupado"):
                engine.start()
            self.assertFalse(engine.STATE_FILE.exists())
            self.assertEqual(listener.getsockname()[1], port)

    def test_stop_does_not_kill_a_reused_pid(self):
        engine.STATE_FILE.parent.mkdir()
        engine.STATE_FILE.write_text('{"pid": 123, "created": "old", "executable": "unrelated"}', encoding="utf-8")
        with patch.object(engine, "identity", return_value={"created": "new", "executable": "unrelated"}), patch.object(engine.os, "kill") as kill:
            result = engine.stop()
        self.assertTrue(result["stale_record"])
        kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
