"""One-time, fictional profiles for exploring searches across full biographies."""

from datetime import datetime

from sqlalchemy import select

from app.api.jobkler import normalize, update_search_text
from app.extensions import db
from app.models import Account, Category, Locality, Profile, SeedState

from .documents import sync_profile_search


SEED_KEY = "jobkler-expanded-demo-v1"
PROFILES_PER_PROFESSION = 10
EXTRA_WORK_PER_PROFESSION = 7

# The main service supplies the profession, short description and tags. The
# extra sentences appear only in the full description, as search evidence.
PROFESSIONS = (
    ("oficios", "Albañilería", "reparaciones de albañilería y colocación de revestimientos", (
        "También he instalado equipos de aire acondicionado tipo split en viviendas.",
        "En otros trabajos armé huertas y realicé mantenimiento de jardines.",
        "Además, he reparado muebles de madera y ajustado sus puertas.",
    )),
    ("oficios", "Electricidad", "instalaciones eléctricas domiciliarias y revisión de tableros", (
        "También instalo equipos de aire acondicionado tipo split en viviendas.",
        "En otros encargos configuré cámaras de seguridad y redes inalámbricas.",
        "Además he reparado computadoras y cambiado componentes de notebooks.",
    )),
    ("oficios", "Carpintería", "fabricación y reparación de muebles de madera", (
        "También reparo termofones y calefones eléctricos.",
        "En celebraciones he armado decoración y fondos para fotografías.",
        "Además, he instalado sistemas de riego para jardines y huertas.",
    )),
    ("hogar", "Limpieza del hogar", "limpieza de casas y apartamentos", (
        "También he cuidado perros y realizado paseos de mascotas.",
        "En otros encargos preparé arreglos florales para cumpleaños.",
        "Además he organizado documentos y planillas para pequeños comercios.",
    )),
    ("hogar", "Jardinería", "poda y mantenimiento de jardines y huertas", (
        "También he instalado riego por goteo y programadores de riego.",
        "En otras ocasiones reparé termofones y calefones en viviendas.",
        "Además, he cuidado mascotas durante viajes y paseado perros.",
    )),
    ("hogar", "Cuidado de mascotas", "paseos y cuidado de perros y gatos", (
        "También he realizado limpieza de piscinas y cuidado del agua.",
        "En otros encargos preparé viandas vegetarianas para reuniones.",
        "Además, he dado apoyo escolar de matemática a niños.",
    )),
    ("tecnologia", "Soporte informático", "reparación de computadoras e instalación de programas", (
        "También he instalado cámaras de seguridad en casas y comercios.",
        "En otros trabajos realicé fotografía de productos para tiendas.",
        "Además doy clases de planillas y hojas de cálculo para principiantes.",
    )),
    ("tecnologia", "Diseño gráfico", "diseño de identidades visuales y piezas digitales", (
        "También hago fotografía de productos para catálogos y tiendas.",
        "En otros eventos preparé mesas dulces y decoración de cumpleaños.",
        "Además he dado clases de dibujo y pintura para principiantes.",
    )),
    ("tecnologia", "Desarrollo web", "creación de sitios web para pequeños emprendimientos", (
        "También he dictado clases de inglés para adultos principiantes.",
        "En otros encargos reparé computadoras y cambié discos de notebooks.",
        "Además he tomado fotografías de productos para catálogos digitales.",
    )),
    ("profesionales", "Contabilidad", "organización de registros contables para emprendimientos", (
        "También doy clases de planillas y hojas de cálculo para principiantes.",
        "En otros proyectos preparé fotografía de productos para comercios.",
        "Además he traducido textos breves entre inglés y español.",
    )),
    ("profesionales", "Administración", "organización administrativa y gestión de documentos", (
        "También he organizado cumpleaños y coordinado decoración de eventos.",
        "En otros encargos preparé viandas vegetarianas para reuniones.",
        "Además doy apoyo escolar de matemática a estudiantes de secundaria.",
    )),
    ("profesionales", "Traducción", "traducción de textos entre español e inglés", (
        "También doy clases particulares de inglés para principiantes.",
        "En otros trabajos diseñé invitaciones y tarjetas para celebraciones.",
        "Además he cuidado perros y realizado paseos de mascotas.",
    )),
    ("bienestar-y-salud", "Masajes", "masajes de bienestar y relajación", (
        "También he guiado clases de respiración y meditación para grupos.",
        "En otros encargos preparé arreglos florales para celebraciones.",
        "Además doy clases de dibujo y pintura para principiantes.",
    )),
    ("bienestar-y-salud", "Actividad física", "acompañamiento en rutinas de movimiento y actividad física", (
        "También he guiado clases de yoga y estiramiento para principiantes.",
        "En otros trabajos he cuidado perros y realizado paseos de mascotas.",
        "Además preparé viandas vegetarianas para encuentros pequeños.",
    )),
    ("bienestar-y-salud", "Acompañamiento domiciliario", "acompañamiento cotidiano de personas mayores", (
        "También he cuidado mascotas y paseado perros para familias.",
        "En otros encargos preparé comidas caseras y viandas vegetarianas.",
        "Además he realizado mantenimiento sencillo de jardines y huertas.",
    )),
    ("belleza", "Peluquería", "cortes y peinados para distintas ocasiones", (
        "También he realizado maquillaje para fiestas y celebraciones.",
        "En otros eventos armé decoración y fondos para fotografías.",
        "Además he tomado fotografías de productos para pequeños negocios.",
    )),
    ("belleza", "Manicuría", "cuidado estético de uñas y manicuría", (
        "También he preparado arreglos florales para cumpleaños.",
        "En otros trabajos diseñé invitaciones y tarjetas para eventos.",
        "Además doy clases de dibujo y pintura para principiantes.",
    )),
    ("belleza", "Maquillaje", "maquillaje para fiestas y sesiones fotográficas", (
        "También hago fotografía de productos para catálogos y tiendas.",
        "En otros encargos confeccioné arreglos florales para celebraciones.",
        "Además he dado clases particulares de inglés para principiantes.",
    )),
    ("educacion", "Apoyo escolar", "acompañamiento escolar y clases particulares de matemática", (
        "También he reparado computadoras y configurado programas de estudio.",
        "En otros encargos cuidé perros y realicé paseos de mascotas.",
        "Además doy clases de planillas y hojas de cálculo para principiantes.",
    )),
    ("educacion", "Clases de inglés", "clases particulares de inglés para jóvenes y adultos", (
        "También he traducido textos breves entre inglés y español.",
        "En otros trabajos tomé fotografías de productos para tiendas.",
        "Además he organizado cumpleaños y decoración para celebraciones.",
    )),
    ("educacion", "Clases de música", "clases de guitarra y lectura musical para principiantes", (
        "También he operado sonido y micrófonos en eventos pequeños.",
        "En otros encargos reparé computadoras y configuré programas.",
        "Además doy clases de dibujo y pintura para principiantes.",
    )),
    ("espiritualidad", "Meditación", "encuentros de meditación y ejercicios de respiración", (
        "También he guiado clases de yoga y estiramiento para principiantes.",
        "En otros encargos preparé arreglos florales para celebraciones.",
        "Además he cuidado perros y realizado paseos de mascotas.",
    )),
    ("espiritualidad", "Lecturas de tarot", "lecturas de tarot para reflexión personal", (
        "También he diseñado invitaciones y tarjetas para cumpleaños.",
        "En otros trabajos tomé fotografías de productos para tiendas.",
        "Además he cuidado plantas y realizado mantenimiento de jardines.",
    )),
    ("espiritualidad", "Reiki", "sesiones de reiki orientadas al bienestar", (
        "También he guiado clases de respiración y meditación para grupos.",
        "En otros encargos preparé viandas vegetarianas para reuniones.",
        "Además he tomado fotografías de productos para catálogos digitales.",
    )),
    ("eventos", "Fotografía de eventos", "fotografía de cumpleaños y reuniones familiares", (
        "También he diseñado invitaciones y tarjetas para celebraciones.",
        "En otros trabajos configuré sitios web para pequeños comercios.",
        "Además doy clases de inglés para adultos principiantes.",
    )),
    ("eventos", "Sonido para eventos", "instalación y operación de sonido para eventos pequeños", (
        "También he instalado cámaras de seguridad en casas y comercios.",
        "En otros trabajos reparé computadoras y cambié discos de notebooks.",
        "Además he dado clases de guitarra para principiantes.",
    )),
    ("eventos", "Organización de eventos", "organización de cumpleaños y reuniones familiares", (
        "También preparo viandas vegetarianas y mesas dulces para reuniones.",
        "En otros encargos tomé fotografías de productos para tiendas.",
        "Además he realizado mantenimiento de jardines y armado huertas.",
    )),
    ("servicios-rurales", "Mantenimiento rural", "reparación de alambrados y mantenimiento de predios", (
        "También he instalado sistemas de riego por goteo para huertas.",
        "En otros encargos reparé bombas de agua domiciliarias.",
        "Además he reparado muebles y puertas de madera.",
    )),
    ("servicios-rurales", "Cuidado de animales", "cuidado y alimentación de animales en predios rurales", (
        "También he cuidado perros y realizado paseos de mascotas.",
        "En otros trabajos armé huertas y realicé mantenimiento de jardines.",
        "Además preparé comidas caseras y viandas vegetarianas.",
    )),
    ("servicios-rurales", "Mecánica rural", "mantenimiento de motores y herramientas de uso rural", (
        "También he reparado bombas de agua para viviendas y huertas.",
        "En otros encargos instalé equipos de aire acondicionado tipo split.",
        "Además he configurado cámaras de seguridad y redes inalámbricas.",
    )),
)

FIRST_NAMES = (
    "Agustina", "Bruno", "Camila", "Diego", "Elena", "Federico", "Gabriela", "Héctor", "Inés", "Joaquín",
    "Karina", "Leonardo", "Martina", "Nicolás", "Olivia", "Pablo", "Rocío", "Santiago", "Tamara", "Valentín",
    "Abril", "Benjamín", "Carolina", "Damián", "Emilia", "Felipe", "Lucía", "Marcos", "Natalia", "Sofía",
)
LAST_NAMES = ("Acosta", "Benítez", "Cabrera", "Duarte", "Fernández", "González", "Méndez", "Pereira", "Rodríguez", "Silva")

# One catalog locality per department, so a seed is stable across machines.
PLACES = (
    ("artigas", "artigas"), ("canelones", "pando"), ("cerro-largo", "melo"),
    ("colonia", "carmelo"), ("durazno", "durazno"), ("flores", "trinidad"),
    ("florida", "florida"), ("lavalleja", "minas"), ("maldonado", "maldonado"),
    ("montevideo", "montevideo"), ("paysandu", "paysandu"), ("rio-negro", "fray-bentos"),
    ("rivera", "rivera"), ("rocha", "rocha"), ("salto", "salto"),
    ("san-jose", "san-jose-de-mayo"), ("soriano", "mercedes"),
    ("tacuarembo", "tacuarembo"), ("treinta-y-tres", "treinta-y-tres"),
)


def expanded_rows():
    """Generate stable profile IDs, with secondary work only in the biography."""
    for profession_index, (category, profession, primary, extras) in enumerate(PROFESSIONS):
        for variant in range(PROFILES_PER_PROFESSION):
            position = profession_index * PROFILES_PER_PROFESSION + variant
            name = f"{FIRST_NAMES[position % len(FIRST_NAMES)]} {LAST_NAMES[position // len(FIRST_NAMES)]} Demo"
            department, locality = PLACES[position % len(PLACES)]
            description = f"Me dedico a {primary}."
            if variant < EXTRA_WORK_PER_PROFESSION:
                description += f" {extras[variant % len(extras)]}"
            description += " Perfil ficticio de demostración."
            number = position + 1
            yield {
                "id": f"expanded-demo-{number:03d}", "owner": f"expanded-demo-owner-{number:03d}",
                "slug": f"perfil-ficticio-ampliado-{number:03d}", "name": name,
                "category": category, "profession": profession, "primary": primary,
                "description": description, "department": department, "locality": locality,
                "has_extra": variant < EXTRA_WORK_PER_PROFESSION,
            }


def seed_expanded_profiles():
    """Add the curated demo population once, without replacing existing data."""
    if db.session.get(SeedState, SEED_KEY):
        return {"skipped": True, "profiles": 0, "with_extra": 0}

    rows = list(expanded_rows())
    categories = {item.id for item in db.session.scalars(select(Category)).all()}
    localities = {item.id: item.department_id for item in db.session.scalars(select(Locality)).all()}
    if any(row["category"] not in categories or localities.get(row["locality"]) != row["department"] for row in rows):
        raise RuntimeError("Faltan categorías o localidades necesarias para los perfiles ficticios ampliados.")

    # Never attach a fixture to an existing account or overwrite an existing profile.
    profile_ids = {row["id"] for row in rows}
    owner_ids = {row["owner"] for row in rows}
    slugs = {row["slug"] for row in rows}
    if (db.session.scalar(select(Profile.id).where(Profile.id.in_(profile_ids)).limit(1))
            or db.session.scalar(select(Profile.id).where(Profile.slug.in_(slugs)).limit(1))
            or db.session.scalar(select(Account.id).where(Account.id.in_(owner_ids)).limit(1))):
        raise RuntimeError("Ya existe un ID o slug reservado para esta semilla; no se modificaron perfiles.")

    created_at = datetime(2026, 9, 23)
    for row in rows:
        db.session.add(Account(id=row["owner"], display_name=row["name"]))
        profile = Profile(
            id=row["id"], slug=row["slug"], owner_id=row["owner"], display_name=row["name"],
            category_id=row["category"], profession=row["profession"],
            profession_normalized=normalize(row["profession"]),
            department_id=row["department"], locality_id=row["locality"],
            short_description=f"{row['profession']}: {row['primary']}.", description=row["description"],
            photo_url="", phone="", whatsapp="", contact_email="", website="", instagram="", address="",
            service_area=[], tags=[row["profession"]], availability="", years_experience=0,
            featured=False, verified=False, is_demo_fixture=True, status="active",
            created_at=created_at, updated_at=created_at,
        )
        update_search_text(profile)
        db.session.add(profile)
        sync_profile_search(profile)

    db.session.add(SeedState(key=SEED_KEY, value="applied"))
    db.session.commit()
    return {"skipped": False, "profiles": len(rows), "with_extra": sum(row["has_extra"] for row in rows)}
