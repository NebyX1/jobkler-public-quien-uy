"""Stable, intentionally fictional local demo fixtures."""
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.extensions import db
from app.models import Account, Category, Department, Identity, Locality, Profile, Review, SeedState
from app.api.jobkler import normalize, clean_slug, update_search_text

SEED_VERSION = "jobkler-demo-v1"
ROOT = Path(__file__).resolve().parents[2]
CATALOG_FILE = ROOT / "src" / "data" / "db.json"

PLACES = [
    ("lavalleja", "minas"),
    ("lavalleja", "solis-de-mataojo"),
    ("lavalleja", "jose-pedro-varela"),
    ("lavalleja", "mariscala"),
    ("lavalleja", "jose-batlle-y-ordonez"),
    ("lavalleja", "zapican"),
    ("lavalleja", "piraraja"),
    ("montevideo", "montevideo"),
    ("maldonado", "maldonado"),
    ("rio-negro", "fray-bentos"),
]

DEMO_ACCOUNTS = [
    ("demo-client", "Cliente Demo", False, "client"),
    ("demo-provider-a", "Valentina Duarte Demo", False, "provider-a"),
    ("demo-provider-b", "Bruno Silva Demo", False, "provider-b"),
    ("demo-moderator", "Moderación Demo", True, "moderator"),
]

OTHER_NAMES = [
    "Sofía Benítez Demo", "Nicolás Cabrera Demo", "Paula Sosa Demo", "Emiliano Techera Demo",
    "Florencia Olivera Demo", "Federico Méndez Demo", "Agustina Núñez Demo", "Diego Acosta Demo",
    "Mariana Suárez Demo", "Joaquín Rodríguez Demo", "Carolina Fagúndez Demo", "Santiago Silva Demo",
    "Romina Pereira Demo", "Andrés Castro Demo", "Belén Fernández Demo", "Matías López Demo",
    "Camila Torres Demo", "Ignacio Vázquez Demo", "Luciana Moreira Demo", "Gonzalo Gutiérrez Demo",
    "Natalia Ramos Demo", "Sebastián Pérez Demo", "Milagros Correa Demo", "Facundo Alonso Demo",
    "Verónica Méndez Demo", "Tomás García Demo", "Micaela Cardozo Demo", "Leandro Silva Demo",
    "Julieta Suárez Demo", "Pablo Pereira Demo", "Cecilia Núñez Demo", "Rodrigo Díaz Demo",
    "Valeria Morales Demo", "Bruno Acuña Demo", "Ana Clara Demo",
]

JOBS = [
    ("Albañilería", "oficios", "reparaciones de albañilería y colocación de revestimientos"),
    ("Limpieza", "hogar", "limpieza de casas y oficinas"),
    ("Jardinería", "hogar", "poda, mantenimiento de jardines y cuidado de plantas"),
    ("Cuidados domiciliarios", "bienestar-y-salud", "acompañamiento y cuidados domiciliarios"),
    ("Clases particulares", "educacion", "apoyo escolar y clases particulares"),
    ("Servicios rurales", "servicios-rurales", "mantenimiento de alambrados y tareas rurales"),
    ("Carpintería", "oficios", "reparación de muebles y trabajos de carpintería"),
    ("Pintura", "oficios", "pintura interior y mantenimiento de fachadas"),
    ("Electricidad", "oficios", "instalaciones eléctricas y reparación de calefones"),
    ("Sanitaria", "oficios", "reparación de grifería y mantenimiento sanitario"),
]


def fixture_rows():
    explicit = [
        ("Valentina Duarte Demo", "Sanitaria", "oficios", "lavalleja", "minas",
         "Reparación e instalación de termofones en Minas.", "Valentina ofrece reparación e instalación de termofones y mantenimiento sanitario en Minas. Perfil ficticio de demostración.", ["Termofones", "Sanitaria"], True),
        ("Bruno Silva Demo", "Electricista", "oficios", "lavalleja", "solis-de-mataojo",
         "Reparación de calefones eléctricos en Solís de Mataojo.", "Bruno declara reparación de calefones eléctricos, instalaciones y mantenimiento eléctrico. Perfil ficticio de demostración.", ["Calefones eléctricos", "Electricidad"], True),
        ("Camila Ferrer Demo", "Informática", "tecnologia", "lavalleja", "minas",
         "Instalación de programas y reparación de computadoras.", "Camila ofrece instalación de programas, reparación de computadoras y soporte informático en Minas. Perfil ficticio de demostración.", ["Computadoras", "Programas"], True),
        ("Martín Viera Demo", "Herrería", "oficios", "lavalleja", "jose-pedro-varela",
         "Trabajos de herrería en José Pedro Varela.", "Martín realiza trabajos de herrería, reparaciones y piezas metálicas a medida. Perfil ficticio de demostración.", ["Herrería", "Metal"], True),
        ("Lucía Pereira Demo", "Sanitaria", "oficios", "rio-negro", "fray-bentos",
         "Servicio de sanitaria en Fray Bentos, Río Negro.", "Lucía ofrece mantenimiento sanitario y reparación de grifería en Fray Bentos, departamento de Río Negro. Perfil ficticio de demostración.", ["Sanitaria", "Grifería"], True),
        ("Sandra Acuña Demo", "Electricista", "oficios", "lavalleja", "minas",
         "Perfil inactivo: reparación de termofones.", "Perfil ficticio inactivo que menciona reparación de termofones y calefones. Debe quedar fuera de resultados públicos.", ["Termofones"], False),
        ("Pablo Castro Demo", "Jardinería", "hogar", "lavalleja", "mariscala",
         "Mantenimiento de jardines; no ofrece instalación de alarmas.", "Pablo ofrece poda y mantenimiento de jardines en Mariscala. Expresamente no ofrece instalación de alarmas. Perfil ficticio para evaluar búsquedas futuras.", ["Jardinería", "Poda"], True),
    ]
    rows = []
    for index, row in enumerate(explicit, 1):
        name, profession, category, department, locality, short, description, tags, active = row
        rows.append({
            "id": f"profile-{index:03d}", "owner": f"demo-provider-{['a','b'][index-1]}" if index < 3 else f"provider-{index:03d}",
            "name": name, "profession": profession, "category": category, "department": department, "locality": locality,
            "short": short, "description": description, "tags": tags, "active": active, "featured": index <= 5,
        })

    for n, name in enumerate(OTHER_NAMES, 8):
        profession, category, service = JOBS[(n - 8) % len(JOBS)]
        department, locality = PLACES[(n - 8) % len(PLACES)]
        local_name = next(
            item["name"] for item in json.loads(CATALOG_FILE.read_text(encoding="utf-8"))["localities"]
            if item["id"] == locality
        )
        desc = f"{name.removesuffix(' Demo')} brinda {service} en {local_name}. Perfil ficticio de demostración."
        rows.append({
            "id": f"profile-{n:03d}", "owner": f"provider-{n:03d}", "name": name,
            "profession": profession, "category": category, "department": department, "locality": locality,
            "short": f"{profession} en {local_name}.", "description": desc,
            "tags": [profession, "Demostración"], "active": n not in {12, 24, 36},
            "featured": n in {8, 15, 22, 29, 35},
        })
    return rows


def seed_jobkler():
    state = db.session.get(SeedState, SEED_VERSION)
    source = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    for item in source.get("categories", []):
        if not db.session.get(Category, item["id"]):
            db.session.add(Category(
                id=item["id"], name=item["name"], slug=item["slug"],
                description=item.get("description", ""), icon=item.get("icon", "Briefcase"),
                featured=bool(item.get("featured")), sort_order=int(item.get("sortOrder", 0)),
            ))
    for item in source.get("departments", []):
        if not db.session.get(Department, item["id"]):
            db.session.add(Department(
                id=item["id"], name=item["name"], slug=item["slug"],
                featured=bool(item.get("featured")), sort_order=int(item.get("sortOrder", 0)),
            ))
    db.session.flush()
    for item in source.get("localities", []):
        if not db.session.get(Locality, item["id"]):
            db.session.add(Locality(
                id=item["id"], name=item["name"], slug=item["slug"],
                department_id=item["departmentId"], featured=bool(item.get("featured")),
                sort_order=int(item.get("sortOrder", 0)),
            ))
    if state:
        db.session.commit()
        return {"skipped": True, "reason": "already_seeded"}

    for account_id, name, moderator, _key in DEMO_ACCOUNTS:
        if not db.session.get(Account, account_id):
            db.session.add(Account(id=account_id, display_name=name, is_moderator=moderator))
    db.session.flush()
    for account_id, name, moderator, key in DEMO_ACCOUNTS:
        existing = db.session.scalar(select(Identity).where(
            Identity.provider == "demo", Identity.issuer == "jobkler-local-demo", Identity.subject == key
        ))
        if not existing:
            db.session.add(Identity(
                id=f"identity-demo-{key}", account_id=account_id,
                provider="demo", issuer="jobkler-local-demo", subject=key,
            ))

    profiles = fixture_rows()
    for item in profiles:
        owner = db.session.get(Account, item["owner"])
        if not owner:
            display_name = item["name"]
            db.session.add(Account(id=item["owner"], display_name=display_name))
    db.session.flush()
    for item in profiles:
        if db.session.get(Profile, item["id"]):
            continue
        category = db.session.get(Category, item["category"])
        department = db.session.get(Department, item["department"])
        locality = db.session.get(Locality, item["locality"])
        if not category or not department or not locality or locality.department_id != department.id:
            raise RuntimeError(f"Fixture {item['id']} apunta a catálogos incompatibles.")
        profile = Profile(
            id=item["id"],
            slug=clean_slug(f"{item['name']} {item['profession']} {locality.name}"),
            owner_id=item["owner"],
            display_name=item["name"],
            category_id=category.id,
            profession=item["profession"],
            profession_normalized=normalize(item["profession"]),
            department_id=department.id,
            locality_id=locality.id,
            short_description=item["short"],
            description=item["description"],
            photo_url="",
            phone="",
            whatsapp="",
            contact_email="",
            website="",
            instagram="",
            address="",
            service_area=[locality.name],
            tags=item["tags"],
            availability="Disponible" if item["active"] else "No disponible (perfil inactivo)",
            years_experience=4,
            featured=item["featured"],
            verified=False,
            is_demo_fixture=True,
            status="active" if item["active"] else "inactive",
            created_at=datetime(2026, 7, 3),
            updated_at=datetime(2026, 7, 3),
        )
        update_search_text(profile)
        db.session.add(profile)

    reviewers = [
        ("reviewer-01", "Martina Demo"), ("reviewer-02", "Federico Demo"),
        ("reviewer-03", "Micaela Demo"), ("reviewer-04", "Santiago Demo"),
        ("reviewer-05", "Florencia Demo"), ("reviewer-06", "Andrés Demo"),
        ("reviewer-07", "Cecilia Demo"), ("reviewer-08", "Rodrigo Demo"),
    ]
    for account_id, name in reviewers:
        if not db.session.get(Account, account_id):
            db.session.add(Account(id=account_id, display_name=name))
    db.session.flush()
    review_rows = [
        ("review-001", "profile-001", "reviewer-01", 5, "Reparación de termofón bien explicada y ordenada."),
        ("review-002", "profile-002", "reviewer-02", 4, "Reparó el calefón eléctrico y dejó todo funcionando."),
        ("review-003", "profile-003", "reviewer-03", 5, "Instaló los programas y explicó cómo usarlos."),
        ("review-004", "profile-004", "reviewer-04", 4, "Trabajo de herrería prolijo y en el plazo acordado."),
        ("review-005", "profile-005", "reviewer-05", 5, "Buena atención sanitaria en Fray Bentos."),
        ("review-006", "profile-008", "reviewer-06", 4, "La atención fue clara y puntual."),
        ("review-007", "profile-010", "reviewer-07", 5, "Resolvió el trabajo con mucho cuidado."),
        ("review-008", "profile-014", "reviewer-08", 4, "Servicio de demostración, comunicación clara."),
    ]
    for review_id, profile_id, author_id, rating, comment in review_rows:
        if not db.session.get(Review, review_id):
            db.session.add(Review(
                id=review_id, profile_id=profile_id, author_id=author_id,
                rating=rating, comment=comment, status="published",
                created_at=datetime(2026, 7, 3),
            ))
    db.session.add(SeedState(key=SEED_VERSION, value="applied"))
    db.session.commit()
    return {"skipped": False, "profiles": len(profiles), "reviews": len(review_rows)}
