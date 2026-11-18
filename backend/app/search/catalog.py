from difflib import SequenceMatcher

from sqlalchemy import exists, or_, select

from app.extensions import db
from app.models import Department, Locality, Profile, ProfileCoverage

from .text import normalize_text


def resolve_coverage_values(profile_id, service_area):
    """Resolve only unambiguous, exact catalog mentions; free text grants no geography."""
    db.session.execute(db.delete(ProfileCoverage).where(ProfileCoverage.profile_id == profile_id))
    values = service_area if isinstance(service_area, list) else []
    departments = db.session.scalars(select(Department)).all()
    localities = db.session.scalars(select(Locality)).all()
    seen = set()
    for raw in values:
        phrase = normalize_text(raw)
        if not phrase:
            continue
        dept_matches = [d for d in departments if phrase in {normalize_text(d.name), normalize_text(d.slug), normalize_text(d.id)}]
        locality_matches = [loc for loc in localities if phrase in {normalize_text(loc.name), normalize_text(loc.slug), normalize_text(loc.id)}]
        # A city name shared between departments is ambiguous unless its value has a scoped slug/id.
        if len(dept_matches) + len(locality_matches) != 1:
            continue
        if dept_matches:
            dep = dept_matches[0]
            key = ("department", dep.id)
            if key not in seen:
                db.session.add(ProfileCoverage(profile_id=profile_id, scope_key=f"department:{dep.id}", department_id=dep.id))
                seen.add(key)
        else:
            locality = locality_matches[0]
            key = ("locality", locality.id)
            if key not in seen:
                db.session.add(ProfileCoverage(profile_id=profile_id, scope_key=f"locality:{locality.id}", locality_id=locality.id))
                seen.add(key)


def _contains_normalized_phrase(normalized_query, phrase):
    return bool(phrase) and f" {phrase} " in f" {normalized_query} "


def detect_location_mentions(query):
    normalized = normalize_text(query)
    departments = db.session.scalars(select(Department).order_by(Department.name)).all()
    localities = db.session.scalars(select(Locality).order_by(Locality.name)).all()
    found_departments = [d for d in departments if _contains_normalized_phrase(normalized, normalize_text(d.name))]
    found_localities = [loc for loc in localities if _contains_normalized_phrase(normalized, normalize_text(loc.name))]
    return found_departments, found_localities


def fuzzy_location_suggestions(value, limit=5):
    query = normalize_text(value)
    if len(query) < 3:
        return []
    choices = []
    for dep in db.session.scalars(select(Department).order_by(Department.name)).all():
        ratio = SequenceMatcher(None, query, normalize_text(dep.name)).ratio()
        if ratio >= 0.66:
            choices.append({"kind": "department", "id": dep.id, "name": dep.name, "departmentId": dep.id, "localityId": None, "score": ratio})
    for loc in db.session.scalars(select(Locality).order_by(Locality.name)).all():
        ratio = SequenceMatcher(None, query, normalize_text(loc.name)).ratio()
        if ratio >= 0.70:
            choices.append({"kind": "locality", "id": loc.id, "name": loc.name, "department": loc.department.name, "departmentId": loc.department_id, "localityId": loc.id, "score": ratio})
    choices.sort(key=lambda item: (-item["score"], item["kind"] != "locality", item["name"]))
    return [{key: value for key, value in item.items() if key != "score"} for item in choices[:limit]]


def _mentioned_scopes(query):
    departments, localities = detect_location_mentions(query)
    normalized = normalize_text(query)
    explicit_department_names = {
        normalize_text(department.name) for department in departments
        if _contains_normalized_phrase(normalized, f"departamento de {normalize_text(department.name)}")
    }
    localities = [locality for locality in localities if normalize_text(locality.name) not in explicit_department_names]
    locality_department_ids = {locality.department_id for locality in localities}
    return [(locality.department, locality) for locality in localities] + [
        (department, None) for department in departments if department.id not in locality_department_ids
    ]


def _scope_option(department, locality):
    if locality:
        return {
            "kind": "locality", "id": locality.id, "name": locality.name, "department": department.name,
            "departmentId": department.id, "localityId": locality.id,
        }
    return {"kind": "department", "id": department.id, "name": department.name, "departmentId": department.id, "localityId": None}


def resolve_filters(query, location_text, department_id, locality_id):
    department = db.session.get(Department, department_id) if department_id else None
    locality = db.session.get(Locality, locality_id) if locality_id else None
    if department_id and not department:
        return None, {"code": "unknown_department", "message": "El departamento elegido ya no está en el catálogo.", "options": []}
    if locality_id and not locality:
        return None, {"code": "unknown_locality", "message": "La localidad elegida ya no está en el catálogo.", "options": []}
    if department and locality and locality.department_id != department.id:
        return None, {"code": "filter_conflict", "message": "La localidad no pertenece al departamento seleccionado.", "options": []}
    if locality:
        department = locality.department

    scopes = _mentioned_scopes(query)
    if location_text and not scopes and normalize_text(location_text) not in {"uruguay", "todo uruguay", "todo el uruguay", "todo el pais"}:
        suggestions = fuzzy_location_suggestions(location_text)
        confirmed = any(
            option["departmentId"] == (department.id if department else None)
            and option["localityId"] == (locality.id if locality else None)
            for option in suggestions
        )
        if confirmed:
            return {"department": department, "locality": locality, "source": "selected"}, None
        if suggestions:
            return None, {
                "code": "location_spelling", "message": f"¿Quisiste decir {suggestions[0]['name']}? Elegí una ubicación para filtrar.",
                "options": suggestions, "requestedText": location_text,
            }
        return None, {
            "code": "unknown_location", "message": "No encontré esa ubicación en el catálogo. Probá con otro nombre de ciudad o departamento.",
            "options": [], "requestedText": location_text,
        }

    if department and scopes:
        matching = [
            (candidate_department, candidate_locality)
            for candidate_department, candidate_locality in scopes
            if candidate_department.id == department.id
            and (not locality or not candidate_locality or candidate_locality.id == locality.id)
        ]
        if not matching:
            return None, {
                "code": "filter_conflict", "message": "La ubicación elegida no coincide con lo que escribiste. ¿Dónde querés buscar?",
                "options": [_scope_option(*scope) for scope in scopes],
            }
        scopes = matching
    if len(scopes) > 1:
        return None, {
            "code": "ambiguous_location", "message": "Encontré más de una ubicación. ¿Dónde querés buscar?",
            "options": [_scope_option(*scope) for scope in scopes],
        }
    if scopes:
        text_department, text_locality = scopes[0]
        department = department or text_department
        locality = locality or text_locality
    source = "selected" if department_id or locality_id else ("query" if department else "national")
    return {"department": department, "locality": locality, "source": source}, None


def eligible_profiles(statement, geo):
    if geo["locality"]:
        loc = geo["locality"]
        return statement.where(or_(
            Profile.locality_id == loc.id,
            exists(select(1).where(ProfileCoverage.profile_id == Profile.id, ProfileCoverage.locality_id == loc.id)),
            exists(select(1).where(ProfileCoverage.profile_id == Profile.id, ProfileCoverage.department_id == loc.department_id)),
        ))
    if geo["department"]:
        dep = geo["department"]
        return statement.where(or_(
            Profile.department_id == dep.id,
            exists(select(1).where(ProfileCoverage.profile_id == Profile.id, ProfileCoverage.department_id == dep.id)),
            exists(select(1).where(
                ProfileCoverage.profile_id == Profile.id,
                ProfileCoverage.locality_id.in_(select(Locality.id).where(Locality.department_id == dep.id)),
            )),
        ))
    return statement


def eligible_profile_ids(geo, profession_text=None):
    from .aliases import profession_aliases

    statement = select(Profile.id).where(Profile.status == "active")
    if profession_text:
        aliases = {normalize_text(alias) for alias in profession_aliases(profession_text)}
        statement = statement.where(Profile.profession_normalized.in_(aliases))
    statement = eligible_profiles(statement, geo)
    # Coverage is an optional one-to-many relation; EXISTS avoids duplicate profile IDs.
    return set(db.session.scalars(statement.distinct()).all())
