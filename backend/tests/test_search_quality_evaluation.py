import unittest

import click
from flask import Flask

from app.extensions import db
from app.models import Account, Category, Department, Locality, Profile, ProfileCoverage, ProfileSearchDocument
from app.search.contracts import AdvancedSearchRequest
from app.search.documents import hash_search_fields, profile_search_fields
from app.search.quality_evaluation import _audit_selected_cases, _audit_target_absence, _grade


class TargetAbsenceEvaluationTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        db.init_app(app)
        context = app.app_context()
        context.push()
        self.addCleanup(context.pop)
        self.addCleanup(db.session.remove)
        db.create_all()
        department = Department(id="lavalleja", name="Lavalleja", slug="lavalleja")
        minas = Locality(id="minas", name="Minas", slug="minas", department=department)
        solis = Locality(id="solis", name="Solís de Mataojo", slug="solis", department=department)
        category = Category(id="oficios", name="Oficios", slug="oficios")
        db.session.add_all((minas, solis, category))
        db.session.flush()
        self.create_profile("muebles", minas, [])
        self.create_profile("otro-lugar", solis, ["SOMIÉRES"])
        self.create_profile("inactivo", minas, ["somier"], status="inactive")
        self.case = {
            "id": "reservado",
            "split": "heldout",
            "input": {"query": "Se partió el somier de mi casa en Minas."},
            "expected": "related",
            "filters": {"departmentId": "lavalleja", "localityId": "minas"},
            "absent_target_terms": ["somier"],
            "relationship": "Arreglos de muebles de madera.",
            "relevant": ["muebles"],
        }
        self.payload = AdvancedSearchRequest.model_validate(self.case["input"])

    def create_profile(self, profile_id, locality, tags, *, status="active"):
        profile = Profile(
            id=profile_id, slug=profile_id, owner=Account(id=profile_id, display_name=profile_id),
            display_name=profile_id, category_id="oficios", profession="Carpintería", profession_normalized="carpinteria",
            department_id=locality.department_id, locality_id=locality.id,
            short_description="Restauración de muebles.", description="Arreglos de muebles de madera.",
            tags=tags, status=status,
        )
        db.session.add(profile)
        db.session.flush()
        fields = profile_search_fields(profile)
        db.session.add(ProfileSearchDocument(
            profile_id=profile.id, source_hash=hash_search_fields(fields), search_text=" ".join(fields.values()), **fields,
        ))
        db.session.flush()

    def test_ignores_inactive_and_out_of_scope_but_checks_declared_coverage(self):
        audit = _audit_target_absence(self.case, self.payload)
        self.assertTrue(audit["passed"])
        self.assertEqual((audit["eligible_profiles"], audit["indexed_profiles"]), (1, 1))
        db.session.add(ProfileCoverage(profile_id="otro-lugar", scope_key="locality:minas", locality_id="minas"))
        db.session.flush()
        audit = _audit_target_absence(self.case, self.payload)
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["hits"], [{"profile_id": "otro-lugar", "field": "tags", "term": "somier"}])
        with self.assertRaisesRegex(click.ClickException, "Falló la auditoría"):
            _audit_selected_cases([self.case], {"reservado": self.payload})

    def test_refuses_to_certify_a_stale_index(self):
        db.session.get(Profile, "muebles").description = "Arreglo somieres."
        audit = _audit_target_absence(self.case, self.payload)
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["outdated_index_profile_ids"], ["muebles"])

    def test_reserved_negative_requires_an_eligible_distractor(self):
        negative = {**self.case, "expected": "empty", "relevant": [], "forbidden": ["otro-lugar"]}
        audit = _audit_target_absence(negative, self.payload)
        self.assertFalse(audit["passed"])
        self.assertTrue(audit["missing_negative_control"])
        negative["forbidden"] = ["muebles"]
        audit = _audit_target_absence(negative, self.payload)
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["eligible_forbidden_profile_ids"], ["muebles"])

    def test_reserved_case_requires_a_clean_corpus_and_labeled_suggestions(self):
        evidence = {"text": "Arreglos de muebles de madera.", "sourceField": "description"}
        result = {
            "status": "ok",
            "applied_filters": self.case["filters"],
            "results": [],
            "suggestions": [{"profile": {"id": "muebles"}, "evidence": evidence}],
        }
        self.assertFalse(_grade(self.case, 200, result, {})["passed"])
        audit = _audit_target_absence(self.case, self.payload)
        self.assertTrue(_grade(self.case, 200, result, {}, corpus_audit=audit)["passed"])
        result["suggestions"].append({"profile": {"id": "sin-etiqueta"}, "evidence": evidence})
        row = _grade(self.case, 200, result, {}, corpus_audit=audit)
        self.assertFalse(row["passed"])
        self.assertEqual(row["unjudged_at_3"], ["sin-etiqueta"])


if __name__ == "__main__":
    unittest.main()
