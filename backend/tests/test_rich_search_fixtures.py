import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from sqlalchemy import func, select, text, update

from app import create_app
from app.extensions import db
from app.models import Account, Profile, ProfileCoverage, ProfileSearchDocument, ProfileSearchIndexJob, SeedState
from app.search.catalog import eligible_profile_ids, resolve_filters
from app.search.documents import sync_profile_search
from app.search.expanded_fixtures import seed_expanded_profiles
from app.search.fixtures import seed_search_fixtures
from app.search.rich_fixtures import PROFILES, SEED_KEY, seed_rich_search_profiles
from app.seed_data import seed_jobkler


class RichSearchFixturesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="jobkler-rich-search-test-")
        database = Path(self.temp.name, "fixtures.sqlite3").as_posix()
        self.app = create_app(overrides={
            "TESTING": True,
            "APP_ENV": "development",
            "AUTH_MODE": "demo",
            "ALLOW_DEMO_AUTH": True,
            "AI_SEARCH_ENABLED": True,
            "AI_SEARCH_SEMANTIC_ENABLED": False,
            "APP_HOST": "127.0.0.1",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
            "SECRET_KEY": "rich-fixtures-test-secret-0123456789",
            "AUTH_SESSION_SECRET": "rich-fixtures-test-session-0123456789",
            "CSRF_SECRET": "rich-fixtures-test-csrf-0123456789",
            "RATELIMIT_ENABLED": False,
        })
        self.addCleanup(self.close_database)
        with self.app.app_context():
            result = self.app.test_cli_runner().invoke(args=["db", "upgrade"])
            self.assertEqual(result.exit_code, 0, result.output)
            seed_jobkler()

    def close_database(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp.cleanup()

    def rich_profiles(self):
        return db.session.scalars(select(Profile).where(Profile.id.like("rich-demo-%"))).all()

    def seed_previous_copy(self):
        previous = (
            "Reparo patas de camas de madera y sustituyo travesaños de somieres cuando están quebrados. "
            "Puedo reforzar uniones flojas y enderezar la estructura para que deje de moverse al sentarse. "
            "Si la pieza está astillada, reviso el estado del resto del mueble antes de cotizar. "
            "También restauro sillas de comedor y mesas con patas vencidas."
        )
        fixtures = tuple(
            replace(row, description=previous) if row.key == "pata-cama-minas" else row
            for row in PROFILES
        )
        with patch("app.search.rich_fixtures.PROFILES", fixtures):
            seed_rich_search_profiles()

    def test_seed_adds_varied_profiles_without_contact_details(self):
        with self.app.app_context():
            result = seed_rich_search_profiles()
            self.assertEqual(result, {"skipped": False, "profiles": 43, "active": 42})
            profiles = self.rich_profiles()
            self.assertEqual(len(profiles), 43)
            self.assertEqual(len({profile.category_id for profile in profiles}), 10)
            self.assertGreaterEqual(len({profile.department_id for profile in profiles}), 15)
            self.assertEqual(len({profile.description for profile in profiles}), 43)
            self.assertEqual(len({profile.owner_id for profile in profiles}), 43)
            for profile in profiles:
                with self.subTest(profile=profile.id):
                    self.assertTrue(profile.is_demo_fixture)
                    self.assertFalse(profile.verified)
                    self.assertTrue(profile.display_name.endswith(" Demo"))
                    self.assertGreater(len(profile.description), 200)
                    self.assertFalse(profile.phone or profile.whatsapp or profile.contact_email)
                    self.assertFalse(profile.website or profile.instagram or profile.photo_url or profile.address)
                    self.assertIsNone(profile.owner.email_private)
                    self.assertFalse(profile.owner.identities)

    def test_secondary_tasks_are_searchable_from_biographies(self):
        with self.app.app_context():
            seed_rich_search_profiles()
            cases = {
                "rich-demo-pata-cama-minas": "repuestos",
                "rich-demo-termicas-minas": "termomagnéticas",
                "rich-demo-bomba-aljibe-minas": "cebado",
                "rich-demo-catalogos-montevideo": "reflejos",
                "rich-demo-paseos-minas": "correa",
                "rich-demo-mecanico-solis": "embragues",
            }
            for profile_id, word in cases.items():
                with self.subTest(profile=profile_id):
                    profile = db.session.get(Profile, profile_id)
                    self.assertIn(word, profile.description)
                    self.assertNotIn(word, " ".join((profile.profession, profile.short_description, *profile.tags)))
                    document = db.session.get(ProfileSearchDocument, profile_id)
                    self.assertEqual(document.description, profile.description)
                    indexed = db.session.scalar(text(
                        "SELECT 1 FROM profile_search_fts WHERE profile_search_fts MATCH :phrase AND profile_id = :id"
                    ), {"phrase": f'"{word}"', "id": profile_id})
                    self.assertEqual(indexed, 1)

    def test_only_active_profiles_have_fts_rows_and_embedding_jobs(self):
        with self.app.app_context():
            seed_rich_search_profiles()
            fts_ids = set(db.session.scalars(text(
                "SELECT profile_id FROM profile_search_fts WHERE profile_id LIKE 'rich-demo-%'"
            )))
            job_ids = set(db.session.scalars(select(ProfileSearchIndexJob.profile_id).where(
                ProfileSearchIndexJob.profile_id.like("rich-demo-%"), ProfileSearchIndexJob.status == "pending",
            )))
            active_ids = {profile.id for profile in self.rich_profiles() if profile.status == "active"}
            self.assertEqual(len(active_ids), 42)
            self.assertEqual(fts_ids, active_ids)
            self.assertEqual(job_ids, active_ids)
            self.assertEqual(db.session.get(Profile, "rich-demo-camas-inactivo").status, "inactive")

    def test_furniture_evidence_omits_the_inferred_object(self):
        with self.app.app_context():
            seed_search_fixtures()
            seed_expanded_profiles()
            seed_rich_search_profiles()
            profiles = db.session.scalars(select(Profile).where(Profile.status == "active")).all()
            self.assertEqual(len(profiles), 388)
            for profile in profiles:
                with self.subTest(profile=profile.id):
                    text_value = " ".join((
                        profile.profession, profile.short_description, profile.description, *profile.tags,
                    ))
                    self.assertNotRegex(text_value.lower(), r"\b(?:camas?|somieres?|colch[oó]n(?:es)?)\b")
            profile = db.session.get(Profile, "rich-demo-pata-cama-minas")
            self.assertIn("Reparo muebles de madera", profile.description)

    def test_updates_untouched_previous_copy_and_invalidates_its_search_revision(self):
        with self.app.app_context():
            self.seed_previous_copy()
            profile_id = "rich-demo-pata-cama-minas"
            document = db.session.get(ProfileSearchDocument, profile_id)
            previous_hash = document.source_hash
            self.assertIn("patas de camas", document.description)

            self.assertEqual(seed_rich_search_profiles(), {
                "skipped": True, "profiles": 0, "active": 0, "updated": 1,
            })
            profile = db.session.get(Profile, profile_id)
            self.assertEqual(profile.owner_id, "rich-demo-owner-pata-cama-minas")
            self.assertIn("Reparo muebles de madera", profile.description)
            self.assertNotIn("camas", profile.search_text)
            self.assertEqual(document.description, profile.description)
            self.assertNotEqual(document.source_hash, previous_hash)
            old_hit = db.session.scalar(text(
                "SELECT 1 FROM profile_search_fts WHERE profile_search_fts MATCH 'somieres' AND profile_id = :id"
            ), {"id": profile_id})
            self.assertIsNone(old_hit)
            jobs = dict(db.session.execute(select(ProfileSearchIndexJob.source_hash, ProfileSearchIndexJob.status)
                                           .where(ProfileSearchIndexJob.profile_id == profile_id)).all())
            self.assertEqual(jobs, {previous_hash: "superseded", document.source_hash: "pending"})
            self.assertEqual(seed_rich_search_profiles(), {"skipped": True, "profiles": 0, "active": 0})

    def test_keeps_legacy_profiles_with_edited_metadata_or_copy(self):
        with self.app.app_context():
            self.seed_previous_copy()
            profile = db.session.get(Profile, "rich-demo-pata-cama-minas")
            original = profile.description
            timestamp = profile.updated_at
            db.session.execute(update(Profile).where(Profile.id == profile.id).values(
                display_name="Nombre editado", updated_at=timestamp,
            ))
            db.session.commit()
            self.assertNotIn("updated", seed_rich_search_profiles())
            self.assertEqual(profile.description, original)
            db.session.execute(update(Profile).where(Profile.id == profile.id).values(
                display_name="Andrea Lago Demo", description="Descripción propia.", updated_at=timestamp,
            ))
            db.session.commit()
            self.assertNotIn("updated", seed_rich_search_profiles())
            self.assertEqual(profile.description, "Descripción propia.")

    def test_declared_coverage_beats_mentions_and_respects_inactive_profiles(self):
        with self.app.app_context():
            seed_rich_search_profiles()
            geo, clarification = resolve_filters("reparar patas de camas en Minas", None, None, None)
            self.assertIsNone(clarification)
            eligible = eligible_profile_ids(geo)
            self.assertIn("rich-demo-pata-cama-minas", eligible)
            self.assertIn("rich-demo-camas-solis", eligible)
            self.assertNotIn("rich-demo-camas-inactivo", eligible)
            self.assertNotIn("rich-demo-camas-montevideo", eligible)
            coverages = set(db.session.scalars(select(ProfileCoverage.profile_id).where(
                ProfileCoverage.profile_id.like("rich-demo-%"), ProfileCoverage.locality_id == "minas",
            )))
            self.assertEqual(coverages, {"rich-demo-camas-solis", "rich-demo-bombas-mariscala"})

    def test_mechanics_have_distinct_catalog_locations_and_concrete_auto_repairs(self):
        with self.app.app_context():
            seed_rich_search_profiles()
            for key, department, locality in (
                ("minas", "lavalleja", "minas"),
                ("solis", "lavalleja", "solis-de-mataojo"),
                ("balneario-solis", "maldonado", "balneario-solis"),
            ):
                with self.subTest(locality=locality):
                    profile = db.session.get(Profile, f"rich-demo-mecanico-{key}")
                    self.assertEqual((profile.department_id, profile.locality_id), (department, locality))
                    self.assertRegex(profile.description, r"\bautos?\b")
                    self.assertIn("freno", profile.description)
                    self.assertEqual(profile.service_area, [])

    def test_repeated_seed_preserves_edits_and_does_not_restore_deleted_profiles(self):
        with self.app.app_context():
            seed_rich_search_profiles()
            owner = db.session.get(Account, "rich-demo-owner-camas-solis")
            db.session.get(Profile, "rich-demo-pata-cama-minas").display_name = "Perfil editado"
            db.session.delete(owner.profile)
            db.session.commit()

            self.assertEqual(seed_rich_search_profiles(), {"skipped": True, "profiles": 0, "active": 0})
            self.assertIsNone(db.session.get(Profile, "rich-demo-camas-solis"))
            self.assertEqual(db.session.get(Profile, "rich-demo-pata-cama-minas").display_name, "Perfil editado")
            self.assertIsNotNone(db.session.get(Account, "rich-demo-owner-camas-solis"))

    def test_reserved_collision_does_not_attach_to_existing_account(self):
        with self.app.app_context():
            identifier = "rich-demo-owner-termicas-minas"
            db.session.add(Account(id=identifier, display_name="Cuenta previa"))
            db.session.commit()

            with self.assertRaisesRegex(RuntimeError, "ID o slug reservado"):
                seed_rich_search_profiles()

            self.assertIsNone(db.session.get(SeedState, SEED_KEY))
            self.assertEqual(db.session.get(Account, identifier).display_name, "Cuenta previa")
            self.assertFalse(self.rich_profiles())

    def test_failure_rolls_back_marker_accounts_documents_and_jobs(self):
        with self.app.app_context():
            def fail_on_second(profile):
                if profile.id == "rich-demo-camas-solis":
                    raise RuntimeError("Error simulado al sincronizar")
                return sync_profile_search(profile)

            with patch("app.search.rich_fixtures.sync_profile_search", side_effect=fail_on_second):
                with self.assertRaisesRegex(RuntimeError, "Error simulado"):
                    seed_rich_search_profiles()

            self.assertIsNone(db.session.get(SeedState, SEED_KEY))
            self.assertFalse(self.rich_profiles())
            first_id = "rich-demo-pata-cama-minas"
            self.assertIsNone(db.session.get(Account, "rich-demo-owner-pata-cama-minas"))
            self.assertIsNone(db.session.get(ProfileSearchDocument, first_id))
            self.assertIsNone(db.session.scalar(select(ProfileSearchIndexJob).where(
                ProfileSearchIndexJob.profile_id == first_id,
            )))
            self.assertIsNone(db.session.scalar(text(
                "SELECT 1 FROM profile_search_fts WHERE profile_id = :id"
            ), {"id": first_id}))
            self.assertEqual(seed_rich_search_profiles()["profiles"], 43)

    def test_two_installations_seed_the_same_population_once(self):
        barrier = Barrier(2, timeout=5)

        def seed():
            with self.app.app_context():
                barrier.wait()
                return seed_rich_search_profiles()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [executor.submit(seed), executor.submit(seed)]
            outcomes = [future.result(timeout=10) for future in results]

        self.assertEqual(sorted(result["profiles"] for result in outcomes), [0, 43])
        self.assertEqual(sum(result["skipped"] for result in outcomes), 1)
        with self.app.app_context():
            self.assertEqual(len(self.rich_profiles()), 43)
            owners = db.session.scalar(select(func.count(Account.id)).where(Account.id.like("rich-demo-owner-%")))
            self.assertEqual(owners, 43)


if __name__ == "__main__":
    unittest.main()
