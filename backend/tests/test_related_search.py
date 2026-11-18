import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from app.api.jobkler import update_search_text
from app.extensions import db
from app.models import Account, Profile
from app.search.contracts import RelatedEvidenceSelection, RelatedServicePlan, SearchIntent
from app.search.documents import rebuild_search_documents, sync_profile_search
from app.search.engine import _evidence_for_profile
from app.search.llm import InferenceUnavailable, verify_related_evidence
from app.search.rich_fixtures import seed_rich_search_profiles
from app.seed_data import seed_jobkler


CATRE_QUERY = "En Minas se venció el apoyo de un catre. ¿Quién lo arregla?"


def catre_intent(**overrides):
    values = {
        "status": "ok",
        "search_text": "arreglar apoyo de catre",
        "profession_text": None,
        "action_text": "arreglar",
        "object_text": "apoyo de catre",
        "location_text": "Minas",
        "related_terms": [],
        "excluded_terms": [],
        "related_services": ["reparación de muebles de madera", "reparación de camas de madera"],
    }
    return SearchIntent(**(values | overrides))


def approve_all(query, passages, **config):
    return list(range(1, len(passages) + 1))


def shortlist_order(query, passages, config):
    return [10.0] * len(passages)


class RelatedSearchEndpointTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="jobkler-related-search-")
        self.addCleanup(temporary.cleanup)
        database = Path(temporary.name, "related.sqlite3").as_posix()
        self.app = create_app(overrides={
            "TESTING": True,
            "APP_ENV": "development",
            "AUTH_MODE": "demo",
            "ALLOW_DEMO_AUTH": True,
            "AI_SEARCH_ENABLED": True,
            "AI_SEARCH_SEMANTIC_ENABLED": True,
            "AI_SEARCH_RERANKER_ENABLED": True,
            "APP_HOST": "127.0.0.1",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
            "SECRET_KEY": "related-test-secret-key-0123456789",
            "AUTH_SESSION_SECRET": "related-test-session-secret-0123456789",
            "CSRF_SECRET": "related-test-csrf-secret-0123456789",
            "RATELIMIT_ENABLED": False,
        })
        self.addCleanup(self.dispose_database)
        self.client = self.app.test_client()
        with self.app.app_context():
            migration = self.app.test_cli_runner().invoke(args=["db", "upgrade"])
            self.assertEqual(migration.exit_code, 0, migration.output)
            seed_jobkler()
            seed_rich_search_profiles()
            rebuild_search_documents()
        csrf = self.client.get("/api/auth/csrf").get_json()["csrfToken"]
        login = self.client.post("/api/auth/demo-login", json={"key": "client"}, headers={"X-CSRF-Token": csrf})
        self.assertEqual(login.status_code, 200)
        self.headers = {"X-CSRF-Token": self.client.get_cookie("jobkler_csrf").value}
        self.stub("app.search.engine._semantic_rankings", return_value=([], None, 0, 0, 0))
        self.stub("app.search.related._semantic_rankings", return_value=([], None, 0, 0, 0))
        self.rank = self.stub("app.search.related.rerank_scores", side_effect=shortlist_order)
        self.verify = self.stub("app.api.advanced_search.verify_related_evidence", side_effect=approve_all)
        self.expand = self.stub("app.api.advanced_search.propose_related_services", return_value=[])

    def dispose_database(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def stub(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def post(self, query=CATRE_QUERY, *, intent=None, stream=False, **body):
        headers = {**self.headers, "Accept": "application/x-ndjson"} if stream else self.headers
        with patch("app.api.advanced_search.extract_intent", return_value=intent or catre_intent()):
            response = self.client.post(
                "/api/search/advanced", json={"query": query, **body}, headers=headers, buffered=True,
            )
        self.assertEqual(response.status_code, 200, response.data)
        if stream:
            self.assertEqual(response.mimetype, "application/x-ndjson")
            return [json.loads(line) for line in response.data.splitlines()]
        return response.get_json()

    def add_related_profiles(self):
        with self.app.app_context():
            for index in range(5):
                key = f"related-test-{index}"
                owner = Account(id=f"{key}-owner", display_name=f"Prestador {index}")
                profile = Profile(
                    id=key, slug=key, owner=owner, display_name=owner.display_name,
                    profession="Carpintería", profession_normalized="carpinteria", category_id="oficios",
                    department_id="lavalleja", locality_id="minas", tags=["Carpintería"],
                    short_description="Reparación de muebles de madera.",
                    description=f"Reparo muebles de madera y reconstruyo sus patas con refuerzo de tipo {index}.",
                    status="active",
                )
                update_search_text(profile)
                db.session.add(profile)
                sync_profile_search(profile)
            db.session.commit()

    def test_approves_only_literal_evidence_and_applies_declared_coverage(self):
        def approve_wood_repair(query, passages, **config):
            return [i for i, excerpt in enumerate(passages, 1) if "perdieron estabilidad" in excerpt]

        self.verify.side_effect = approve_wood_repair
        data = self.post()
        self.assertEqual(data["applied_filters"]["localityId"], "minas")
        self.assertEqual(data["results"], [])
        self.assertEqual([item["profile"]["id"] for item in data["suggestions"]], ["rich-demo-camas-solis"])
        suggestion = data["suggestions"][0]
        self.assertEqual(suggestion["evidence"]["matchType"], "related")
        self.assertIsNone(suggestion["evidence"]["cosine"])
        self.assertTrue(suggestion["reason"])
        with self.app.app_context():
            profile = db.session.get(Profile, "rich-demo-camas-solis")
            self.assertNotEqual(profile.locality_id, "minas")
            self.assertIn(suggestion["evidence"]["text"], profile.description)
        verified_passages = self.verify.call_args.args[1]
        self.assertFalse(any("en Montevideo" in excerpt or "con los apoyos vencidos" in excerpt for excerpt in verified_passages))
        self.assertEqual(self.rank.call_args.args[0], CATRE_QUERY)

    def test_requests_a_broader_service_when_the_object_is_absent(self):
        self.expand.return_value = ["reparación de muebles de madera"]
        query = "Se rompió la pata de la cama en Minas."
        intent = catre_intent(search_text="reparar cama", object_text="cama", related_services=[])
        data = self.post(query, intent=intent)
        self.expand.assert_called_once()
        self.assertEqual(self.expand.call_args.args[0], query)
        self.assertEqual(data["results"], [])
        suggestions = data.get("suggestions", [])
        self.assertTrue(suggestions, data)
        self.assertTrue(all("cama" not in item["evidence"]["text"].casefold() for item in suggestions))
        self.assertEqual(self.verify.call_args.args[0], query)

    def test_semantic_candidate_without_shared_words_requires_verification(self):
        profile_id = "rich-demo-pata-cama-minas"
        with self.app.app_context():
            profile = db.session.get(Profile, profile_id)
            chunk = SimpleNamespace(source_field="description", literal_text=profile.description)
        self.stub("app.search.related._semantic_rankings", return_value=(
            [(profile_id, (0.40, chunk))], None, 0, 0, 0,
        ))
        self.expand.return_value = ["restauración de armazones domésticos"]
        intent = catre_intent(related_services=[])
        self.verify.side_effect = None
        self.verify.return_value = [1]

        data = self.post(intent=intent)

        self.assertEqual(data["results"], [])
        self.assertEqual([match["profile"]["id"] for match in data["suggestions"]], [profile_id])
        self.assertIn("muebles de madera", self.verify.call_args.args[1][0])
        self.verify.return_value = []
        refused = self.post(intent=intent)
        self.assertEqual(refused["status"], "empty")
        self.assertEqual(refused.get("suggestions", []), [])

    def test_broad_interpretation_cannot_be_reported_as_direct(self):
        self.add_related_profiles()
        for raw_subject in ("muebles de madera", "pata"):
            with self.subTest(raw_subject=raw_subject):
                query = "Se rompió la pata de la cama en Minas."
                intent = catre_intent(search_text=f"reparar {raw_subject}", object_text=raw_subject)
                data = self.post(query, intent=intent)
                self.assertEqual(data["results"], [])

    def test_caps_suggestions_and_never_repeats_profiles(self):
        self.add_related_profiles()
        data = self.post(limit=12)
        suggestions = [item["profile"]["id"] for item in data["suggestions"]]
        original = {item["profile"]["id"] for item in data["results"]}
        self.assertEqual(len(suggestions), 3)
        self.assertEqual(len(set(suggestions)), 3)
        self.assertTrue(original.isdisjoint(suggestions))
        passages = self.verify.call_args.args[1]
        self.assertEqual(len(passages), len(set(passages)))
        self.assertGreater(len(passages), 3)
        self.assertLessEqual(len(self.post(limit=1)["suggestions"]), 1)

    def test_verifier_can_abstain_despite_high_reranker_scores(self):
        self.verify.side_effect = None
        self.verify.return_value = []
        data = self.post()
        self.rank.assert_called_once()
        self.verify.assert_called_once()
        self.assertEqual(data["results"], [])
        self.assertEqual(data.get("suggestions", []), [])
        self.assertEqual(data["status"], "empty")

    def test_direct_evidence_prevents_fallback_model_calls(self):
        query = "¿Quién repara bombas de aljibe en Minas?"
        intent = catre_intent(search_text="reparar bombas de aljibe", object_text="bombas de aljibe")
        data = self.post(query, intent=intent)
        profile_ids = {
            item["profile"]["id"] for item in data["results"] if item["evidence"]["matchType"] == "direct"
        }
        self.assertIn("rich-demo-bomba-aljibe-minas", profile_ids)
        self.assertEqual(data.get("suggestions", []), [])
        self.rank.assert_not_called()
        self.verify.assert_not_called()

    def test_unavailable_reranker_reports_degradation_and_omits_suggestions(self):
        self.rank.side_effect = RuntimeError("falta el modelo ONNX")
        data = self.post()
        self.assertEqual(data["status"], "degraded")
        self.assertTrue(data["degradation"])
        self.assertEqual(data.get("suggestions", []), [])
        self.verify.assert_not_called()

    def test_failed_evidence_verification_leaves_no_unverified_suggestion(self):
        self.verify.side_effect = InferenceUnavailable("respuesta inválida")
        data = self.post()
        self.rank.assert_called_once()
        self.assertEqual(data["status"], "degraded")
        self.assertTrue(data["degradation"])
        self.assertEqual(data.get("suggestions", []), [])

    def test_disabled_reranker_keeps_only_the_existing_search(self):
        self.app.config["AI_SEARCH_RERANKER_ENABLED"] = False
        data = self.post()
        self.assertEqual(data["status"], "empty")
        self.assertEqual(data.get("suggestions", []), [])
        self.rank.assert_not_called()
        self.verify.assert_not_called()

    def test_related_evidence_must_keep_explicit_specialized_type(self):
        intent = catre_intent(
            search_text="reparar cama hospitalaria eléctrica", object_text="cama hospitalaria",
            required_terms=["hospitalaria"],
        )
        data = self.post("En Minas preciso reparar una cama hospitalaria eléctrica.", intent=intent)
        self.assertEqual(data["status"], "empty", data)
        self.assertEqual(data.get("suggestions", []), [])
        self.verify.assert_not_called()

    def test_rewrite_cannot_drop_part_of_the_named_object(self):
        intent = catre_intent(
            search_text="reparar cama elástica", object_text="cama elástica",
            related_services=["reparar camas"],
        )
        data = self.post("Necesito reparar una cama elástica en Minas.", intent=intent)
        self.assertEqual(data["status"], "empty", data)
        self.assertEqual(data.get("suggestions", []), [])
        self.verify.assert_not_called()

    def test_stale_search_document_cannot_be_used_as_evidence(self):
        with self.app.app_context():
            profile = db.session.get(Profile, "rich-demo-camas-solis")
            profile.description = "Me dedico ahora a un trabajo diferente."
            db.session.commit()
        data = self.post()
        ids = {item["profile"]["id"] for item in data.get("suggestions", [])}
        self.assertNotIn("rich-demo-camas-solis", ids)

    def test_edit_during_verification_invalidates_an_approved_excerpt(self):
        def approve_and_edit(query, passages, **config):
            indices = [i for i, excerpt in enumerate(passages, 1) if "perdieron estabilidad" in excerpt]
            self.assertTrue(indices)
            profile = db.session.get(Profile, "rich-demo-camas-solis")
            profile.description = "Ya no reparo camas. Ahora instalo estantes."
            sync_profile_search(profile)
            db.session.commit()
            return indices

        self.verify.side_effect = approve_and_edit
        data = self.post()
        self.assertEqual(data.get("suggestions", []), [])

    def test_stream_final_event_contains_the_separate_suggestions(self):
        events = self.post(stream=True)
        stages = [event["stage"] for event in events if event["type"] == "stage"]
        self.assertEqual(stages, ["interpretation", "location", "retrieval"])
        self.assertEqual(events[-1]["type"], "result")
        self.assertEqual(events[-1]["status"], 200)
        self.assertTrue(events[-1]["result"]["suggestions"])
        self.assertEqual(events[-1]["result"]["results"], [])

    def mechanic_intent(self, location):
        return catre_intent(
            search_text=f"mecánico en {location}", profession_text="mecánico",
            action_text=None, object_text=None, location_text=location, related_services=[],
        )

    def test_mechanic_search_in_minas_and_in_the_department(self):
        for location, expected_locality in (("Minas", "minas"), ("Lavalleja", None), ("Minas, Lavalleja", "minas")):
            with self.subTest(location=location):
                data = self.post(f"Mecánico en {location}", intent=self.mechanic_intent(location))
                ids = {item["profile"]["id"] for item in data["results"]}
                self.assertEqual(data["applied_filters"]["localityId"], expected_locality)
                self.assertEqual(data["applied_filters"]["departmentId"], "lavalleja")
                self.assertIn("rich-demo-mecanico-minas", ids)

    def test_simple_trade_query_uses_catalog_before_calling_qwen(self):
        with patch("app.api.advanced_search.extract_intent", side_effect=AssertionError("El oficio ya está en el catálogo")) as llm:
            response = self.client.post(
                "/api/search/advanced", json={"query": "necesito un mecánico en lavalleja"},
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        llm.assert_not_called()
        results = response.get_json()["results"]
        self.assertEqual({item["profile"]["id"] for item in results}, {
            "rich-demo-mecanico-minas", "rich-demo-mecanico-solis",
        })
        self.assertEqual({item["evidence"]["matchType"] for item in results}, {"direct"})

    def test_solis_shorthand_offers_catalog_choices_with_or_without_a_model_hint(self):
        for location in ("Solís", None):
            with self.subTest(location=location):
                data = self.post("Mecánico en Solís", intent=self.mechanic_intent(location))
                self.assertEqual(data["status"], "ambiguous")
                ids = {option["localityId"] for option in data["clarification"]["options"]}
                self.assertEqual(ids, {"solis-de-mataojo", "balneario-solis"})
        self.rank.assert_not_called()
        self.verify.assert_not_called()

    def test_confirmed_solis_de_mataojo_returns_local_mechanic(self):
        data = self.post(
            "Mecánico en Solís de Mataojo", intent=self.mechanic_intent("Solís de Mataojo"),
        )
        self.assertEqual(data["applied_filters"]["localityId"], "solis-de-mataojo")
        self.assertIn("rich-demo-mecanico-solis", {item["profile"]["id"] for item in data["results"]})

    def test_following_a_solis_suggestion_filters_to_the_selected_locality(self):
        data = self.post(
            "Mecánico en Solís", intent=self.mechanic_intent("Solís"),
            localityId="balneario-solis", departmentId="maldonado",
        )
        self.assertEqual(data["applied_filters"]["localityId"], "balneario-solis")
        ids = {item["profile"]["id"] for item in data["results"]}
        self.assertIn("rich-demo-mecanico-balneario-solis", ids)
        self.assertNotIn("rich-demo-mecanico-solis", ids)


class DirectEvidenceTest(unittest.TestCase):
    def evidence(self, description, **intent_fields):
        document = SimpleNamespace(
            profession="Carpintero", category="", short_description="", description=description, tags="",
        )
        return _evidence_for_profile(None, document, catre_intent(**intent_fields), None, 0.54)

    def test_operations_on_different_objects_are_not_direct(self):
        match = self.evidence(
            "Instalo cámaras de seguridad y reparo computadoras.",
            action_text="reparar", object_text="cámaras de seguridad",
        )
        self.assertEqual(match["matchType"], "related")

    def test_two_operations_may_share_the_same_object(self):
        for action in ("instalar", "reparar"):
            with self.subTest(action=action):
                match = self.evidence("Instalo y reparo termofones.", action_text=action, object_text="termofones")
                self.assertEqual(match["matchType"], "direct")

    def test_profession_title_is_insufficient_for_a_specific_object(self):
        match = self.evidence("Soy carpintero.", profession_text="carpintero", action_text=None)
        self.assertIsNone(match)


class EvidenceVerifierTest(unittest.TestCase):
    connection = {"base_url": "http://127.0.0.1:8081/v1", "model": "fixture-model"}

    def test_extra_model_proposals_are_capped_before_retrieval(self):
        plan = RelatedServicePlan.model_validate({"services": [
            "reparación de mobiliario", "refuerzo de piezas estructurales", "fabricación de muebles",
        ]})
        self.assertEqual(plan.services, ["reparación de mobiliario", "refuerzo de piezas estructurales"])

    def test_verifier_only_exposes_one_based_references_to_literal_passages(self):
        passages = ["Reparo muebles de madera.", "Hago fotografía de productos."]
        with patch("app.search.llm._request_json", return_value=RelatedEvidenceSelection(accepted=[1])) as request:
            self.assertEqual(verify_related_evidence(CATRE_QUERY, passages, **self.connection), [1])
        self.assertEqual(request.call_args.args[0], {
            "consulta": CATRE_QUERY, "fragmentos": [{"n": 1, "cita": passages[0]}, {"n": 2, "cita": passages[1]}],
        })

    def test_out_of_range_or_duplicate_references_fail_closed(self):
        for references in ([3], [1, 1]):
            with self.subTest(references=references), patch(
                "app.search.llm._request_json", return_value=RelatedEvidenceSelection(accepted=references),
            ):
                with self.assertRaisesRegex(InferenceUnavailable, "referencias"):
                    verify_related_evidence(CATRE_QUERY, ["reparación de muebles", "fotografía"], **self.connection)


if __name__ == "__main__":
    unittest.main()
