import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import AuthSession, Profile, Review
from app.seed_data import seed_jobkler


class JobklerApiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="jobkler-test-")
        database = Path(self.temp.name, "test.sqlite3").as_posix()
        self.app = create_app(overrides={
            "TESTING": True,
            "APP_ENV": "development",
            "AUTH_MODE": "demo",
            "ALLOW_DEMO_AUTH": True,
            "AI_SEARCH_ENABLED": False,
            "APP_HOST": "127.0.0.1",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
            "SECRET_KEY": "test-secret-key-0123456789-0123456789",
            "AUTH_SESSION_SECRET": "test-auth-session-secret-0123456789",
            "CSRF_SECRET": "test-csrf-secret-0123456789-0123456789",
            "RATELIMIT_ENABLED": False,
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            result = self.app.test_cli_runner().invoke(args=["db", "upgrade"])
            if result.exit_code:
                raise AssertionError(result.output)
            seed_jobkler()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp.cleanup()

    def csrf(self):
        response = self.client.get("/api/auth/csrf")
        self.assertEqual(response.status_code, 200)
        return response.get_json()["csrfToken"]

    def login(self, key):
        token = self.csrf()
        response = self.client.post(
            "/api/auth/demo-login", json={"key": key}, headers={"X-CSRF-Token": token}
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertIn("HttpOnly", response.headers.get("Set-Cookie", ""))
        return response.get_json()

    def write_headers(self):
        return {"X-CSRF-Token": self.client.get_cookie("jobkler_csrf").value}

    def test_catalog_search_is_server_filtered_paginated_and_public(self):
        catalog = self.client.get("/api/catalog").get_json()
        self.assertTrue(any(item["id"] == "lavalleja" for item in catalog["departments"]))

        response = self.client.get("/api/profiles?q=programas&page=1&limit=1")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["id"], "profile-003")
        self.assertNotIn("ownerUserId", data["items"][0])
        self.assertNotIn("owner_id", data["items"][0])

        inactive = self.client.get("/api/profiles?q=termofones").get_json()
        self.assertNotIn("profile-006", [item["id"] for item in inactive["items"]])
        mismatch = self.client.get("/api/profiles?department=montevideo&locality=minas").get_json()
        self.assertEqual(mismatch["total"], 0)
        second_page = self.client.get("/api/profiles?department=lavalleja&page=2&limit=1").get_json()
        self.assertEqual(second_page["page"], 2)
        self.assertEqual(second_page["pages"], second_page["total"])
        self.assertEqual(len(second_page["items"]), 1)

    def test_session_csrf_logout_and_session_revocation(self):
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.login("client")
        raw_cookie = self.client.get_cookie("jobkler_session").value
        with self.app.app_context():
            stored = db.session.query(AuthSession).one()
            self.assertNotEqual(stored.token_hash, raw_cookie)
        self.assertTrue(self.client.get("/api/auth/me").get_json()["is_demo"])
        response = self.client.post("/api/auth/logout", headers=self.write_headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_google_login_sends_configured_fusionauth_idp_hint(self):
        self.app.config.update({
            "AUTH_MODE": "fusionauth",
            "FUSIONAUTH_BASE_URL": "https://fusion.example.test",
            "FUSIONAUTH_ISSUER": "https://fusion.example.test",
            "FUSIONAUTH_CLIENT_ID": "jobkler-client",
            "FUSIONAUTH_CLIENT_SECRET": "unit-test-client-secret",
            "FUSIONAUTH_GOOGLE_IDP_ID": "google-idp-test-id",
            "FUSIONAUTH_REDIRECT_URI": "http://127.0.0.1:5000/api/auth/callback",
        })
        with patch("app.api.auth_routes.build_authorization_url", return_value="https://fusion.example.test/oauth2/authorize") as build:
            response = self.client.get("/api/auth/login/google")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(build.call_args.kwargs["idp_hint"], "google-idp-test-id")
        self.assertEqual(build.call_args.kwargs["prompt"], "login")
        self.assertEqual(build.call_args.kwargs["max_age"], 0)
        config = self.client.get("/api/auth/config").get_json()
        self.assertTrue(config["configured"])
        self.assertEqual(config["loginUrl"], "/api/auth/login/google")

    def test_profile_owner_can_edit_but_other_account_cannot_spoof_ownership(self):
        self.login("provider-b")
        payload = {"description": "Intento de editar un perfil ajeno por HTTP."}
        denied = self.client.patch("/api/profiles/profile-001", json=payload, headers=self.write_headers())
        self.assertEqual(denied.status_code, 403)

        self.login("provider-a")
        forbidden = self.client.patch(
            "/api/profiles/profile-001", json={"ownerUserId": "demo-provider-b"}, headers=self.write_headers()
        )
        self.assertEqual(forbidden.status_code, 400)
        for field, value in (("verified", True), ("roles", ["moderator"]), ("reviewsCount", 100), ("rating", 5)):
            rejected = self.client.patch(
                "/api/profiles/profile-001", json={field: value}, headers=self.write_headers()
            )
            self.assertEqual(rejected.status_code, 400, field)
        edited = self.client.patch(
            "/api/profiles/profile-001", json={"description": "Descripción editada desde la API de prueba."},
            headers=self.write_headers(),
        )
        self.assertEqual(edited.status_code, 200, edited.get_json())
        self.assertEqual(edited.get_json()["description"], "Descripción editada desde la API de prueba.")

    def test_client_can_create_one_profile_and_server_sets_ownership(self):
        self.login("client")
        payload = {
            "displayName": "Oficio de Prueba", "profession": "Carpintería",
            "category": "oficios", "department": "lavalleja", "locality": "minas",
            "shortDescription": "Reparaciones en Minas.",
            "description": "Perfil de prueba para revisar la validación y permisos del servidor.",
            "yearsExperience": 3,
        }
        created = self.client.post("/api/profiles", json=payload, headers=self.write_headers())
        self.assertEqual(created.status_code, 201, created.get_json())
        profile = created.get_json()
        self.assertFalse(profile["isFictionalDemo"])
        self.assertTrue(profile["isOwner"])
        self.assertNotIn("ownerUserId", profile)

        duplicate = self.client.post("/api/profiles", json=payload, headers=self.write_headers())
        self.assertEqual(duplicate.status_code, 409)

    def test_review_rules_duplicates_and_moderation(self):
        self.login("provider-a")
        self_review = self.client.post("/api/reviews", json={
            "profileId": "profile-001", "rating": 5, "comment": "Este comentario es suficientemente largo.",
            "acceptedNoEditPolicy": True,
        }, headers=self.write_headers())
        self.assertEqual(self_review.status_code, 403, self_review.get_json())

        self.login("client")
        other_author = self.client.post("/api/reviews", json={
            "profileId": "profile-001", "rating": 5, "comment": "Servicio ficticio muy bien explicado.",
            "acceptedNoEditPolicy": True, "authorUserId": "demo-provider-b",
        }, headers=self.write_headers())
        self.assertEqual(other_author.status_code, 400)
        posted = self.client.post("/api/reviews", json={
            "profileId": "profile-001", "rating": 5, "comment": "Servicio ficticio muy bien explicado.",
            "acceptedNoEditPolicy": True,
        }, headers=self.write_headers())
        self.assertEqual(posted.status_code, 201, posted.get_json())
        self.assertNotIn("authorUserId", posted.get_json())
        duplicate = self.client.post("/api/reviews", json={
            "profileId": "profile-001", "rating": 4, "comment": "Otro comentario de prueba suficientemente largo.",
            "acceptedNoEditPolicy": True,
        }, headers=self.write_headers())
        self.assertEqual(duplicate.status_code, 409)

        self.login("moderator")
        hidden = self.client.patch(
            f"/api/moderation/reviews/{posted.get_json()['id']}", json={"status": "hidden"},
            headers=self.write_headers(),
        )
        self.assertEqual(hidden.status_code, 200)
        self.assertEqual(hidden.get_json()["status"], "hidden")
        public = self.client.get("/api/reviews?profileId=profile-001").get_json()
        self.assertNotIn(posted.get_json()["id"], [item["id"] for item in public])

    def test_seed_is_idempotent_and_does_not_restore_deleted_fixtures(self):
        with self.app.app_context():
            fixture = db.session.get(Profile, "profile-001")
            fixture.display_name = "Cambio conservado Demo"
            db.session.delete(db.session.get(Profile, "profile-002"))
            db.session.commit()
            result = seed_jobkler()
            self.assertTrue(result["skipped"])
            self.assertEqual(db.session.get(Profile, "profile-001").display_name, "Cambio conservado Demo")
            self.assertIsNone(db.session.get(Profile, "profile-002"))

    def test_owner_status_and_delete_permissions(self):
        self.login("provider-a")
        headers = self.write_headers()
        deactivated = self.client.post(
            "/api/profiles/profile-001/status", json={"status": "inactive"}, headers=headers,
        )
        self.assertEqual(deactivated.status_code, 200)
        self.assertEqual(self.client.get("/api/profiles/profile-001").status_code, 200)
        self.assertEqual(self.client.get("/api/profiles?department=lavalleja").get_json()["total"], 28)

        public_detail = self.client.get("/api/profiles/profile-001")
        self.assertEqual(public_detail.get_json()["status"], "inactive")
        self.client.post("/api/auth/logout", headers=self.write_headers())
        self.assertEqual(self.client.get("/api/profiles/profile-001").status_code, 404)
        self.login("provider-a")
        self.assertEqual(self.client.get("/api/profiles/me").get_json()["status"], "inactive")
        self.assertEqual(
            self.client.post("/api/profiles/profile-001/status", json={"status": "active"}, headers=self.write_headers()).status_code,
            200,
        )
        self.assertEqual(self.client.delete("/api/profiles/profile-001", headers=self.write_headers()).status_code, 204)
        self.assertEqual(self.client.get("/api/profiles/profile-001").status_code, 404)
        with self.app.app_context():
            self.assertIsNone(db.session.get(Review, "review-001"))

    def test_catalog_accepts_accented_names_and_slugs_and_search_ignores_accents(self):
        by_name = self.client.get("/api/profiles?department=R%C3%ADo%20Negro&locality=Fray%20Bentos").get_json()
        by_slug = self.client.get("/api/profiles?department=rio-negro&locality=fray-bentos").get_json()
        named_ids = {p["id"] for p in by_name["items"]}
        slugged_ids = {p["id"] for p in by_slug["items"]}
        self.assertIn("profile-005", named_ids)
        self.assertEqual(named_ids, slugged_ids)
        unaccented_search = self.client.get("/api/profiles?q=instalacion").get_json()
        accented_search = self.client.get("/api/profiles?q=instalaci%C3%B3n").get_json()
        unaccented_ids = {p["id"] for p in unaccented_search["items"]}
        accented_ids = {p["id"] for p in accented_search["items"]}
        self.assertIn("profile-003", unaccented_ids)
        self.assertEqual(unaccented_ids, accented_ids)


if __name__ == "__main__":
    unittest.main()
