import asyncio
import json
import re
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import numpy as np
from sqlalchemy import select, text

from app import create_app
from app.extensions import db
from app.models import Account, Profile, ProfileSearchChunk, ProfileSearchDocument, ProfileSearchIndexJob, SeedState
from app.models.jobkler import utcnow
from app.seed_data import seed_jobkler
from app.search.contracts import SearchIntent
from app.search.documents import rebuild_search_documents, sync_profile_search
from app.search.model_manifest import MODEL_DIMENSION, MODEL_NAME, MODEL_REVISION
from app.search.fixtures import seed_search_fixtures
from app.search.expanded_fixtures import SEED_KEY, seed_expanded_profiles
from app.search.llm import InferenceBusy, InferenceUnavailable, extract_intent


def make_intent(*, profession=None, action="reparar", obj="termofones", location="Minas"):
    return SearchIntent(
        status="ok",
        search_text="reparar termofones",
        profession_text=profession,
        action_text=action,
        object_text=obj,
        location_text=location,
        related_terms=["calefón"],
        excluded_terms=[],
    )


class AdvancedSearchTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="jobkler-advanced-test-")
        database = Path(self.temp.name, "advanced.sqlite3").as_posix()
        self.app = create_app(overrides={
            "TESTING": True,
            "APP_ENV": "development",
            "AUTH_MODE": "demo",
            "ALLOW_DEMO_AUTH": True,
            "AI_SEARCH_ENABLED": True,
            "AI_SEARCH_SEMANTIC_ENABLED": False,
            "AI_SEARCH_RATE_LIMIT_PER_HOUR": 20,
            "APP_HOST": "127.0.0.1",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
            "SECRET_KEY": "advanced-test-secret-key-0123456789",
            "AUTH_SESSION_SECRET": "advanced-test-session-secret-0123456789",
            "CSRF_SECRET": "advanced-test-csrf-secret-012345678901",
            "RATELIMIT_ENABLED": False,
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            result = self.app.test_cli_runner().invoke(args=["db", "upgrade"])
            if result.exit_code:
                raise AssertionError(result.output)
            seed_jobkler()
            seed_search_fixtures()
            rebuild_search_documents()
            self.assertIsNotNone(db.session.execute(text("SELECT 1 FROM profile_search_fts LIMIT 1")).first())

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp.cleanup()

    def login(self):
        csrf = self.client.get("/api/auth/csrf").get_json()["csrfToken"]
        response = self.client.post("/api/auth/demo-login", json={"key": "client"}, headers={"X-CSRF-Token": csrf})
        self.assertEqual(response.status_code, 200, response.get_json())
        return {"X-CSRF-Token": self.client.get_cookie("jobkler_csrf").value}

    def post_search(self, query="Necesito reparar termofones en Minas", *, intent=None, body=None, headers=None):
        self.login_if_needed()
        payload = body if body is not None else {"query": query}
        with patch("app.api.advanced_search.extract_intent", return_value=intent or make_intent()):
            return self.client.post("/api/search/advanced", json=payload, headers=headers or self.headers)

    def login_if_needed(self):
        if not getattr(self, "headers", None):
            self.headers = self.login()

    def test_advanced_requires_session_while_common_search_stays_public(self):
        with patch("app.api.advanced_search.extract_intent") as extract:
            response = self.client.post("/api/search/advanced", json={"query": "reparo termofones"})
        self.assertEqual(response.status_code, 401)
        extract.assert_not_called()
        self.assertEqual(self.client.get("/api/profiles?q=termofones").status_code, 200)

    def test_chat_stream_announces_search_before_inference_and_preserves_applied_location(self):
        self.login_if_needed()
        with patch("app.api.advanced_search.extract_intent", return_value=make_intent()) as extract:
            with self.client.post(
                "/api/search/advanced",
                json={"query": "Necesito reparar termofones en Minas"},
                headers={**self.headers, "Accept": "application/x-ndjson"},
                buffered=False,
            ) as response:
                self.assertEqual(response.mimetype, "application/x-ndjson")
                stream = iter(response.response)
                self.assertEqual(json.loads(next(stream)), {"type": "stage", "stage": "interpretation"})
                extract.assert_not_called()
                events = [json.loads(line) for line in stream]

        self.assertEqual([event["stage"] for event in events[:-1]], ["location", "retrieval"])
        terminal = events[-1]
        self.assertEqual(terminal["type"], "result")
        self.assertEqual(terminal["status"], 200)
        self.assertEqual(terminal["result"]["applied_filters"]["localityId"], "minas")

    def test_chat_widening_does_not_reapply_the_original_location(self):
        self.login_if_needed()
        response = self.post_search(body={"query": "Necesito reparar termofones en Minas", "locationScope": "national"})
        self.assertEqual(response.status_code, 200)
        filters = response.get_json()["applied_filters"]
        self.assertEqual(filters["locationSource"], "national")
        self.assertIsNone(filters["localityId"])
        self.assertIsNone(filters["departmentId"])

        response = self.post_search(body={
            "query": "Necesito reparar termofones en Minas",
            "locationScope": "national",
            "localityId": "minas",
        })
        self.assertEqual(response.status_code, 400)

    def test_expanded_seed_indexes_secondary_work_and_preserves_later_changes(self):
        with self.app.app_context():
            result = seed_expanded_profiles()
            self.assertEqual((result["profiles"], result["with_extra"]), (300, 210))
            profiles = db.session.scalars(select(Profile).where(Profile.id.like("expanded-demo-%"))).all()
            self.assertEqual(len(profiles), 300)
            self.assertEqual(len({profile.category_id for profile in profiles}), 10)
            self.assertEqual(len({profile.department_id for profile in profiles}), 19)
            sample = db.session.get(Profile, "expanded-demo-011")
            self.assertIn("aire acondicionado", sample.description)
            self.assertNotIn("aire acondicionado", " ".join((sample.profession, sample.short_description, *sample.tags)).lower())
            self.assertIn("aire acondicionado", db.session.get(ProfileSearchDocument, sample.id).description)
            self.assertTrue(sample.is_demo_fixture)
            self.assertFalse(sample.phone or sample.whatsapp or sample.contact_email)

        intent = SearchIntent(
            status="ok", search_text="instalar aire acondicionado", profession_text=None,
            action_text="instalar", object_text="aire acondicionado", location_text=None,
            related_terms=[], excluded_terms=[],
        )
        response = self.post_search(query="Necesito instalar aire acondicionado", intent=intent)
        self.assertEqual(response.status_code, 200)
        result = next(item for item in response.get_json()["results"] if item["profile"]["id"] == "expanded-demo-011")
        self.assertEqual(result["evidence"]["sourceField"], "description")

        with self.app.app_context():
            sample = db.session.get(Profile, "expanded-demo-011")
            sample.display_name = "Nombre editado Demo"
            db.session.delete(db.session.get(Profile, "expanded-demo-012"))
            db.session.commit()
            self.assertTrue(seed_expanded_profiles()["skipped"])
            self.assertEqual(db.session.get(Profile, "expanded-demo-011").display_name, "Nombre editado Demo")
            self.assertIsNone(db.session.get(Profile, "expanded-demo-012"))

    def test_expanded_seed_rejects_reserved_id_collision(self):
        with self.app.app_context():
            db.session.add(Account(id="expanded-demo-owner-001", display_name="Cuenta existente"))
            db.session.commit()
            with self.assertRaisesRegex(RuntimeError, "ID o slug reservado"):
                seed_expanded_profiles()
            self.assertIsNone(db.session.get(SeedState, SEED_KEY))
            self.assertIsNone(db.session.get(Profile, "expanded-demo-001"))

    def test_advanced_passes_configured_llm_key_only_to_server(self):
        self.app.config["AI_LLM_API_KEY"] = "private-test-key"
        self.login_if_needed()
        with patch("app.api.advanced_search.extract_intent", return_value=make_intent()) as extract:
            response = self.client.post(
                "/api/search/advanced", json={"query": "Reparar termofones en Minas"}, headers=self.headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(extract.call_args.kwargs["api_key"], "private-test-key")
        self.assertNotIn(b"private-test-key", response.data)

    def test_text_evidence_location_coverage_installation_negation_and_inactive_rules(self):
        response = self.post_search()
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["applied_filters"]["locality"], "Minas")
        results = {item["profile"]["id"]: item for item in data["results"]}

        self.assertIn("fixture-search-01", results)  # Profession was not required by the text-only bio evidence.
        self.assertEqual(results["fixture-search-01"]["evidence"]["sourceField"], "description")
        self.assertEqual(results["fixture-search-01"]["evidence"]["matchType"], "direct")
        self.assertIn("fixture-search-02", results)  # Installation is labeled as related, not repair.
        self.assertEqual(results["fixture-search-02"]["evidence"]["matchType"], "related")
        self.assertNotIn("fixture-search-03", results)  # Explicit current negation.
        self.assertNotIn("fixture-search-04", results)  # A bio mention of Minas is not coverage.
        self.assertNotIn("fixture-search-05", results)  # Inactive profiles are filtered before retrieval.
        self.assertIn("fixture-search-06", results)  # Relevant phrase appears after a long prefix.
        self.assertIn("fixture-search-07", results)
        self.assertEqual(results["fixture-search-07"]["locationLabel"], "Atiende en Minas")
        self.assertIn("fixture-search-08", results)
        self.assertIn("declaró cobertura departamental Lavalleja", results["fixture-search-08"]["locationLabel"])
        self.assertNotIn("fixture-search-09", results)
        self.assertTrue(all(item["profile"]["slug"] for item in results.values()))
        self.assertTrue(all(item["evidence"]["text"] in item["profile"]["description"] or item["evidence"]["sourceField"] != "description" for item in results.values()))

    def test_semantic_retrieval_finds_candidate_without_fts_candidates(self):
        from app.api.jobkler import serialize_profile
        from app.search.engine import _lexical_rankings, search_profiles

        with self.app.app_context():
            document = db.session.get(ProfileSearchDocument, "fixture-search-01")
            chunk = ProfileSearchChunk(
                chunk_id="semantic-only-fixture-search-01", profile_id="fixture-search-01",
                source_hash=document.source_hash, source_field="description", literal_text=document.description,
                start_char=0, end_char=len(document.description), encoder_model=MODEL_NAME,
                encoder_revision=MODEL_REVISION, vector_dimension=MODEL_DIMENSION,
                vector_dtype="float32-le", vector_bytes=np.eye(1, MODEL_DIMENSION, 0, dtype="<f4")[0].tobytes(),
            )
            db.session.add(chunk)
            db.session.commit()

            intent = SearchIntent(
                status="ok", search_text="solucionar una avería doméstica", profession_text=None,
                action_text=None, object_text=None, location_text="Minas", related_terms=[], excluded_terms=[],
            )

            class FakeEncoder:
                def embed(self, _texts, batch_size=32, parallel=None):
                    return [np.eye(1, MODEL_DIMENSION, 0, dtype=np.float32)[0]]

            config = dict(self.app.config)
            config["AI_SEARCH_SEMANTIC_ENABLED"] = True
            self.assertEqual(_lexical_rankings({"fixture-search-01"}, intent), [])
            result = search_profiles(
                intent, query="Solucionar una avería doméstica en Minas", config=config,
                encoder=FakeEncoder(), query_vector=np.eye(1, MODEL_DIMENSION, 0, dtype=np.float32)[0],
                serialize_profile=serialize_profile,
            )

        self.assertIn("fixture-search-01", {item["profile"]["id"] for item in result["results"]})
        match = next(item for item in result["results"] if item["profile"]["id"] == "fixture-search-01")
        self.assertEqual(match["evidence"]["matchType"], "related")
        self.assertIsNotNone(match["evidence"]["cosine"])

    def test_evaluation_metrics_helpers_include_recall_and_labeled_specificity(self):
        from app.commands import _metric_summary, _retrieval_metrics

        metrics = _retrieval_metrics([{
            "id": "metric-test", "expected_status": "ok", "relevant_profile_ids": ["expected"],
            "forbidden_profile_ids": ["forbidden"], "result_ids": ["expected"], "result_status": "ok",
        }], field="result_ids", status_field="result_status")
        self.assertEqual(metrics["macro_recall_at_5"], 1.0)
        self.assertEqual(metrics["specificity_on_forbidden_labels"], 1.0)
        self.assertEqual(metrics["calibration_f1"], 1.0)
        self.assertEqual(_metric_summary([1, 3, 2])["mean_ms"], 2.0)

    def test_explicit_profession_filter_is_honored_and_conflict_is_a_clarification(self):
        response = self.post_search(
            query="Carpintero en Minas",
            intent=make_intent(profession="carpintero", action=None, obj=None, location="Minas"),
        )
        ids = {item["profile"]["id"] for item in response.get_json()["results"]}
        self.assertIn("fixture-search-01", ids)
        self.assertNotIn("fixture-search-02", ids)
        self.assertEqual(response.get_json()["applied_filters"]["profession"], "carpintero")

        conflict = self.post_search(
            query="Reparar termofones en Minas",
            body={"query": "Reparar termofones en Minas", "departmentId": "montevideo"},
        )
        self.assertEqual(conflict.status_code, 200)
        self.assertEqual(conflict.get_json()["status"], "ambiguous")
        self.assertEqual(conflict.get_json()["results"], [])

    def test_location_typo_is_suggested_without_selecting_it(self):
        query = "Reparar termofones en Minaz"
        response = self.post_search(
            query=query,
            intent=make_intent(location="Minaz"),
        )
        data = response.get_json()
        self.assertEqual(data["status"], "ambiguous")
        self.assertEqual(data["clarification"]["code"], "location_spelling")
        self.assertEqual(data["clarification"]["requestedText"], "Minaz")
        self.assertEqual(data["results"], [])
        minas = next(option for option in data["clarification"]["options"] if option["name"] == "Minas")
        confirmed = self.post_search(
            body={"query": query, "departmentId": minas["departmentId"], "localityId": minas["localityId"]},
            intent=make_intent(location="Minaz"),
        ).get_json()
        self.assertEqual(confirmed["status"], "ok")
        self.assertEqual(confirmed["applied_filters"]["localityId"], "minas")
        self.assertEqual(confirmed["applied_filters"]["locationSource"], "selected")

    def test_choosing_a_city_resolves_multiple_places_in_the_original_query(self):
        query = "Reparar termofones en Minas o en Montevideo"
        data = self.post_search(query=query, intent=make_intent(location="Minas")).get_json()
        self.assertEqual(data["clarification"]["code"], "ambiguous_location")
        choices = {option["name"]: option for option in data["clarification"]["options"]}
        self.assertEqual(set(choices), {"Minas", "Montevideo"})
        confirmed = self.post_search(
            body={"query": query, "localityId": choices["Minas"]["localityId"]},
            intent=make_intent(location="Minas"),
        ).get_json()
        self.assertEqual(confirmed["status"], "ok")
        self.assertEqual(confirmed["applied_filters"]["localityId"], "minas")
        self.assertEqual(confirmed["applied_filters"]["departmentId"], "lavalleja")
        self.assertTrue(all("Minas" in item["locationLabel"] for item in confirmed["results"]))

    def test_location_remains_applied_when_no_profiles_match_the_requested_trade(self):
        intent = SearchIntent(
            status="ok", search_text="mecánico", profession_text="mecánico", action_text=None,
            object_text=None, location_text=None, related_terms=[], excluded_terms=[],
        )
        data = self.post_search(query="Quiero un mecánico en Minas", intent=intent).get_json()
        self.assertEqual(data["status"], "empty")
        self.assertEqual(data["applied_filters"], {
            "department": "Lavalleja", "departmentId": "lavalleja", "locality": "Minas",
            "localityId": "minas", "locationSource": "query", "profession": "mecánico",
        })

    def test_department_named_explicitly_stays_department_wide(self):
        data = self.post_search(
            query="Reparar termofones en el departamento de Maldonado",
            intent=make_intent(location="Maldonado"),
        ).get_json()
        self.assertEqual(data["applied_filters"]["departmentId"], "maldonado")
        self.assertIsNone(data["applied_filters"]["localityId"])

    def test_missing_qwen_uses_deterministic_text_search_and_marks_degraded(self):
        with patch("app.api.advanced_search.extract_intent", side_effect=InferenceUnavailable("connection refused")):
            response = self.client.post(
                "/api/search/advanced",
                json={"query": "Arregle termofones en Minas"},
                headers=self.login(),
            )
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "degraded")
        self.assertTrue(any(item["profile"]["id"] == "fixture-search-01" for item in data["results"]))
        self.assertTrue(data["degradation"])

    def test_request_schema_rejects_client_identity_and_model_fields(self):
        self.login_if_needed()
        response = self.client.post(
            "/api/search/advanced",
            json={"query": "reparar termofones", "userId": "forged", "model": "external"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("userId", response.get_json())

    def test_profile_create_edit_deactivate_reactivate_and_delete_sync_fts_and_jobs(self):
        headers = self.login()
        payload = {
            "displayName": "Fixture de ciclo de vida",
            "profession": "Carpintero",
            "categoryId": "oficios",
            "departmentId": "lavalleja",
            "localityId": "minas",
            "shortDescription": "Perfil para probar el índice de búsqueda.",
            "description": "Contenido de prueba. Reparo termofones cuando el índice está vigente.",
            "serviceArea": ["Minas"],
            "tags": ["Prueba indexada"],
        }
        created = self.client.post("/api/profiles", json=payload, headers=headers)
        self.assertEqual(created.status_code, 201, created.get_json())
        profile_id = created.get_json()["id"]
        with self.app.app_context():
            document = db.session.get(ProfileSearchDocument, profile_id)
            self.assertIn("termofones", document.search_text)
            first_hash = document.source_hash
            self.assertIsNotNone(db.session.scalar(select(ProfileSearchIndexJob.id).where(ProfileSearchIndexJob.profile_id == profile_id, ProfileSearchIndexJob.status == "pending")))
            fts = db.session.execute(text("SELECT source_hash FROM profile_search_fts WHERE profile_id=:id"), {"id": profile_id}).scalar_one()
            self.assertEqual(fts, first_hash)

        edited = self.client.patch(
            f"/api/profiles/{profile_id}",
            json={"description": "Cambió el texto público y el índice debe reflejar esta revisión."},
            headers=headers,
        )
        self.assertEqual(edited.status_code, 200)
        with self.app.app_context():
            document = db.session.get(ProfileSearchDocument, profile_id)
            self.assertNotEqual(document.source_hash, first_hash)
            self.assertNotIn("termofones", document.search_text)
            self.assertIsNone(db.session.execute(text("SELECT profile_id FROM profile_search_fts WHERE profile_id=:id AND source_hash=:hash"), {"id": profile_id, "hash": first_hash}).first())

        inactive = self.client.post(f"/api/profiles/{profile_id}/status", json={"status": "inactive"}, headers=headers)
        self.assertEqual(inactive.status_code, 200)
        with self.app.app_context():
            self.assertIsNone(db.session.execute(text("SELECT profile_id FROM profile_search_fts WHERE profile_id=:id"), {"id": profile_id}).first())

        active = self.client.post(f"/api/profiles/{profile_id}/status", json={"status": "active"}, headers=headers)
        self.assertEqual(active.status_code, 200)
        with self.app.app_context():
            self.assertIsNotNone(db.session.execute(text("SELECT profile_id FROM profile_search_fts WHERE profile_id=:id"), {"id": profile_id}).first())
            self.assertIsNotNone(db.session.scalar(select(ProfileSearchIndexJob.id).where(ProfileSearchIndexJob.profile_id == profile_id, ProfileSearchIndexJob.status == "pending")))

        deleted = self.client.delete(f"/api/profiles/{profile_id}", headers=headers)
        self.assertEqual(deleted.status_code, 204)
        with self.app.app_context():
            self.assertIsNone(db.session.get(ProfileSearchDocument, profile_id))
            self.assertIsNone(db.session.execute(text("SELECT profile_id FROM profile_search_fts WHERE profile_id=:id"), {"id": profile_id}).first())

    def test_worker_discards_embedding_when_profile_revision_changes_before_publish(self):
        from app.search import indexer

        with self.app.app_context():
            profile = db.session.get(Profile, "fixture-search-01")
            document = db.session.get(ProfileSearchDocument, profile.id)
            old_hash = document.source_hash
            job = db.session.scalar(select(ProfileSearchIndexJob).where(
                ProfileSearchIndexJob.profile_id == profile.id,
                ProfileSearchIndexJob.source_hash == old_hash,
            ))
            job.status = "running"
            job.attempts = 1
            job.started_at = utcnow()
            db.session.commit()
            chunk = {
                "chunk_id": "a" * 64, "profile_id": profile.id, "source_hash": old_hash,
                "source_field": "description", "literal_text": "Reparo termofones.",
                "start_char": 0, "end_char": 20, "encoder_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "encoder_revision": "faf4aa4225822f3bc6376869cb1164e8e3feedd0",
                "vector_dimension": 384, "vector_dtype": "float32-le",
            }

            def change_profile_while_encoding(_encoder, _texts):
                current = db.session.get(Profile, profile.id)
                current.description += " Nueva revisión posterior."
                sync_profile_search(current)
                db.session.commit()
                vector = np.zeros((1, 384), dtype=np.float32)
                vector[0, 0] = 1.0
                return vector

            with patch("app.search.indexer.token_chunks", return_value=[chunk]), patch(
                "app.search.indexer.encode_normalized", side_effect=change_profile_while_encoding
            ):
                state = indexer.process_job(job.id, encoder=object())

            self.assertEqual(state, "superseded")
            self.assertEqual(db.session.scalar(select(ProfileSearchIndexJob.status).where(ProfileSearchIndexJob.id == job.id)), "superseded")
            self.assertIsNone(db.session.get(ProfileSearchChunk, "a" * 64))
            current_document = db.session.get(ProfileSearchDocument, profile.id)
            self.assertNotEqual(current_document.source_hash, old_hash)

    def test_long_text_chunker_keeps_the_last_sentence_with_overlapped_token_windows(self):
        from app.search.encoder import token_chunks

        class Encoded:
            def __init__(self, ids, offsets):
                self.ids = ids
                self.offsets = offsets

        class Tokenizer:
            def encode(self, value, add_special_tokens=True):
                offsets = [(match.start(), match.end()) for match in re.finditer(r"\S+", value)]
                ids = list(range(len(offsets)))
                return Encoded(([0, *ids, 1] if add_special_tokens else ids), offsets)

        class Model:
            tokenizer = Tokenizer()

        class FakeEncoder:
            model = Model()

        text_value = " " .join(f"texto{index}" for index in range(340)) + " Al final reparo termofones."
        chunks = token_chunks(FakeEncoder(), "profile-fixture", "b" * 64, {"description": text_value})
        self.assertGreater(len(chunks), 2)
        self.assertTrue(any("reparo termofones." in chunk["literal_text"] for chunk in chunks))
        self.assertTrue(all(len(FakeEncoder.model.tokenizer.encode(chunk["literal_text"]).ids) <= 128 for chunk in chunks))
        self.assertTrue(all(text_value[chunk["start_char"]:chunk["end_char"]] == chunk["literal_text"] for chunk in chunks))

    def test_llama_schema_request_is_single_and_truncated_output_is_rejected(self):
        valid = {
            "status": "ok", "search_text": "reparar termofones", "profession_text": None,
            "action_text": "reparo", "object_text": "termofones", "location_text": "Minas",
            "related_terms": ["calefón"], "excluded_terms": [],
        }

        class FakeResponse:
            def __init__(self, finish_reason, content):
                self.finish_reason = finish_reason
                self.content = content

            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"finish_reason": self.finish_reason, "message": {"content": self.content}}]}

        class FakeClient:
            def __init__(self, response):
                self.response = response
                self.calls = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def post(self, url, *, json):
                self.calls.append((url, json))
                return self.response

        success_client = FakeClient(FakeResponse("stop", json.dumps(valid)))
        with patch("app.search.llm.httpx.AsyncClient", return_value=success_client) as factory:
            result = extract_intent("Reparo termofones en Minas", base_url="http://127.0.0.1:8081/v1", model="fixture", api_key="private-test-key", timeout_seconds=1, connect_timeout_seconds=0.5)
        self.assertEqual(factory.call_args.kwargs["headers"], {"Authorization": "Bearer private-test-key"})
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(success_client.calls), 1)
        request = success_client.calls[0][1]
        self.assertEqual(request["response_format"]["type"], "json_schema")
        self.assertFalse(request["response_format"]["schema"]["additionalProperties"])
        self.assertEqual(request["chat_template_kwargs"]["enable_thinking"], False)

        truncated_client = FakeClient(FakeResponse("length", json.dumps(valid)))
        with patch("app.search.llm.httpx.AsyncClient", return_value=truncated_client) as factory:
            with self.assertRaises(InferenceUnavailable):
                extract_intent("Reparo termofones en Minas", base_url="http://127.0.0.1:8081/v1", model="fixture", timeout_seconds=1, connect_timeout_seconds=0.5)
        self.assertEqual(factory.call_args.kwargs["headers"], {})
        self.assertEqual(len(truncated_client.calls), 1)

    def test_inference_waits_for_the_active_request_and_reports_a_full_queue(self):
        started = threading.Event()
        release = threading.Event()

        async def fake_request(query, **_kwargs):
            if query == "first":
                started.set()
                await asyncio.to_thread(release.wait, 3)
            return make_intent()

        args = {"base_url": "http://127.0.0.1:8081/v1", "model": "fixture"}
        with patch("app.search.llm._request_intent", side_effect=fake_request):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(extract_intent, "first", **args)
                try:
                    self.assertTrue(started.wait(2))
                    with self.assertRaises(InferenceBusy):
                        extract_intent("busy", queue_wait_seconds=0.05, **args)
                    waiting = pool.submit(extract_intent, "waiting", queue_wait_seconds=1, **args)
                    release.set()
                    self.assertEqual(first.result(timeout=2).status, "ok")
                    self.assertEqual(waiting.result(timeout=2).status, "ok")
                finally:
                    release.set()

    def test_account_rate_limit_is_enforced_by_persistent_sql_rows(self):
        self.app.config["AI_SEARCH_RATE_LIMIT_PER_HOUR"] = 1
        self.login_if_needed()
        with patch("app.api.advanced_search.extract_intent", return_value=make_intent()):
            first = self.client.post("/api/search/advanced", json={"query": "Reparar termofones en Minas"}, headers=self.headers)
            second = self.client.post("/api/search/advanced", json={"query": "Reparar termofones en Minas"}, headers=self.headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.get_json()["error"]["code"], "rate_limited")


if __name__ == "__main__":
    unittest.main()
