"""Synthetic-only profiles used by the local advanced-search evaluation corpus."""

from datetime import datetime

from sqlalchemy import select

from app.api.jobkler import normalize, update_search_text
from app.extensions import db
from app.models import Account, Category, Department, Locality, Profile


SEARCH_FIXTURES = (
    {
        "id": "fixture-search-01", "slug": "fixture-search-carpintero-minas", "owner": "fixture-search-owner-01",
        "name": "Fixture de búsqueda 01", "profession": "Carpintero", "department": "lavalleja", "locality": "minas",
        "short": "Carpintería en Minas. Fixture sintético de evaluación.",
        "description": "Perfil ficticio de evaluación; no representa a un proveedor real. Trabajo como carpintero en Minas. Reparo termofones a pedido como caso de prueba.",
        "tags": ["Carpintería", "Fixture de evaluación"], "coverage": [], "active": True,
    },
    {
        "id": "fixture-search-02", "slug": "fixture-search-solo-instala-minas", "owner": "fixture-search-owner-02",
        "name": "Fixture de búsqueda 02", "profession": "Sanitario", "department": "lavalleja", "locality": "minas",
        "short": "Instalación de termofones. Fixture sintético de evaluación.",
        "description": "Perfil ficticio de evaluación; no representa a un proveedor real. Instalo termofones y calefones; mi actividad declarada es la instalación.",
        "tags": ["Termofones", "Fixture de evaluación"], "coverage": [], "active": True,
    },
    {
        "id": "fixture-search-03", "slug": "fixture-search-niega-reparacion-minas", "owner": "fixture-search-owner-03",
        "name": "Fixture de búsqueda 03", "profession": "Sanitario", "department": "lavalleja", "locality": "minas",
        "short": "Instalación de calefones. Fixture sintético de evaluación.",
        "description": "Perfil ficticio de evaluación; no representa a un proveedor real. No reparo termofones; solo instalo calefones.",
        "tags": ["Termofones", "Fixture de evaluación"], "coverage": [], "active": True,
    },
    {
        "id": "fixture-search-04", "slug": "fixture-search-fuera-de-minas", "owner": "fixture-search-owner-04",
        "name": "Fixture de búsqueda 04", "profession": "Sanitario", "department": "montevideo", "locality": "montevideo",
        "short": "Reparación de termofones. Fixture sintético de evaluación.",
        "description": "Perfil ficticio de evaluación; no representa a un proveedor real. Reparo termofones en Montevideo. Una vez trabajé en Minas, pero no declaro cobertura actual allí.",
        "tags": ["Termofones", "Fixture de evaluación"], "coverage": [], "active": True,
    },
    {
        "id": "fixture-search-05", "slug": "fixture-search-inactivo-minas", "owner": "fixture-search-owner-05",
        "name": "Fixture de búsqueda 05", "profession": "Carpintero", "department": "lavalleja", "locality": "minas",
        "short": "Perfil inactivo. Fixture sintético de evaluación.",
        "description": "Perfil ficticio inactivo de evaluación. Reparo termofones; no debe aparecer mientras esté retirado.",
        "tags": ["Fixture de evaluación"], "coverage": [], "active": False,
    },
    {
        "id": "fixture-search-06", "slug": "fixture-search-bio-larga", "owner": "fixture-search-owner-06",
        "name": "Fixture de búsqueda 06", "profession": "Carpintero", "department": "lavalleja", "locality": "minas",
        "short": "Carpintería en Minas. Fixture sintético de evaluación.",
        "description": "Perfil ficticio de evaluación; no representa a un proveedor real. " + ("Trabajo de carpintería general, restauración de madera y tareas de taller. " * 70) + "Al final de mi experiencia declaro que reparo termofones y calefones; esta frase final comprueba que el índice conserva el cierre de una biografía larga.",
        "tags": ["Carpintería", "Fixture de evaluación"], "coverage": [], "active": True,
    },
    {
        "id": "fixture-search-07", "slug": "fixture-search-cobertura-minas", "owner": "fixture-search-owner-07",
        "name": "Fixture de búsqueda 07", "profession": "Sanitario", "department": "lavalleja", "locality": "solis-de-mataojo",
        "short": "Servicio con cobertura declarada. Fixture sintético de evaluación.",
        "description": "Perfil ficticio de evaluación; no representa a un proveedor real. Reparo termofones en las localidades de Lavalleja que declaro en mi cobertura.",
        "tags": ["Termofones", "Fixture de evaluación"], "coverage": ["Minas"], "active": True,
    },
    {
        "id": "fixture-search-08", "slug": "fixture-search-cobertura-departamental", "owner": "fixture-search-owner-08",
        "name": "Fixture de búsqueda 08", "profession": "Sanitario", "department": "montevideo", "locality": "montevideo",
        "short": "Cobertura departamental declarada. Fixture sintético de evaluación.",
        "description": "Perfil ficticio de evaluación; no representa a un proveedor real. Realizo reparación de termofones en el departamento de Lavalleja, donde declaré cobertura.",
        "tags": ["Termofones", "Fixture de evaluación"], "coverage": ["Lavalleja"], "active": True,
    },
    {
        "id": "fixture-search-09", "slug": "fixture-search-irrelevante-minas", "owner": "fixture-search-owner-09",
        "name": "Fixture de búsqueda 09", "profession": "Pintor", "department": "lavalleja", "locality": "minas",
        "short": "Pintura interior en Minas. Fixture sintético de evaluación.",
        "description": "Perfil ficticio de evaluación; no representa a un proveedor real. Pinto interiores y fachadas; no declaro trabajos de sanitaria o reparación de termofones.",
        "tags": ["Pintura", "Fixture de evaluación"], "coverage": [], "active": True,
    },
)


def seed_search_fixtures():
    category = db.session.get(Category, "oficios")
    if not category:
        raise RuntimeError("Inicializá el catálogo local antes de sembrar fixtures de búsqueda.")
    added = 0
    for item in SEARCH_FIXTURES:
        if db.session.get(Profile, item["id"]):
            continue
        owner = db.session.get(Account, item["owner"])
        if not owner:
            owner = Account(id=item["owner"], display_name=f"Cuenta ficticia {item['id']}")
            db.session.add(owner)
            db.session.flush()
        department = db.session.get(Department, item["department"])
        locality = db.session.get(Locality, item["locality"])
        profile = Profile(
            id=item["id"], slug=item["slug"], owner_id=owner.id,
            display_name=item["name"], category_id=category.id,
            profession=item["profession"], profession_normalized=normalize(item["profession"]),
            department_id=department.id, locality_id=locality.id,
            short_description=item["short"], description=item["description"],
            photo_url="", phone="", whatsapp="", contact_email="", website="", instagram="", address="",
            service_area=item["coverage"], tags=item["tags"], availability="", years_experience=0,
            featured=False, verified=False, is_demo_fixture=True,
            status="active" if item["active"] else "inactive",
            created_at=datetime(2026, 9, 23), updated_at=datetime(2026, 9, 23),
        )
        update_search_text(profile)
        db.session.add(profile)
        db.session.flush()
        from .catalog import resolve_coverage_values
        from .documents import sync_profile_search
        resolve_coverage_values(profile.id, profile.service_area)
        sync_profile_search(profile)
        added += 1
    db.session.commit()
    return added
