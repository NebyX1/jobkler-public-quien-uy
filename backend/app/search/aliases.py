"""Small, reviewed Uruguayan Spanish retrieval vocabulary; versioned in source."""

ALIAS_VERSION = "uy-service-terms-v2"

OBJECT_GROUPS = {
    "termofon": ("termofon", "termofones", "calefon", "calefones", "calentador de agua", "calentadores de agua"),
    "mueble a medida": ("mueble a medida", "muebles a medida", "mobiliario a medida"),
    "puerta de madera": ("puerta de madera", "puertas de madera"),
}

ACTION_GROUPS = {
    "reparar": (
        "reparar", "reparo", "repara", "reparan", "repare", "reparacion", "reparado",
        "arreglar", "arreglo", "arregla", "arreglan", "arregle", "arreglado",
        "solucionar", "soluciona", "componer",
    ),
    "instalar": (
        "instalar", "instalo", "instala", "instalan", "instale", "instalacion", "instalado",
        "colocar", "coloco", "coloca", "colocacion", "montar", "monto", "monta", "montaje",
    ),
    "fabricar": ("fabricar", "fabrico", "fabrica", "hacer", "hago", "construir", "construyo"),
}

PROFESSION_GROUPS = {
    "carpintero": ("carpintero", "carpintera", "carpinteria", "ebanista"),
    "electricista": ("electricista", "electricistas"),
    "mecanico": (
        "mecanico", "mecanica", "mecanicos", "mecanicas", "mecanico automotor",
        "mecanica automotriz", "mecanica automotor", "mecanico automotriz",
    ),
    "sanitario": ("sanitario", "sanitaria", "fontanero", "fontanera", "plomero", "plomera"),
}

SPANISH_STOP_WORDS = frozenset({
    "a", "al", "alguien", "algun", "alguna", "con", "de", "del", "el", "en", "hay",
    "la", "las", "lo", "los", "me", "necesito", "para", "por", "que", "quien", "se",
    "un", "una", "unas", "unos", "y",
})


def aliases_for(value, groups):
    from .text import normalize_text

    normalized = normalize_text(value)
    for canonical, aliases in groups.items():
        if normalized in {normalize_text(item) for item in aliases}:
            return canonical, tuple(aliases)
    return normalized, (normalized,) if normalized else ()


def object_aliases(value):
    return aliases_for(value, OBJECT_GROUPS)[1]


def action_aliases(value):
    return aliases_for(value, ACTION_GROUPS)[1]


def profession_aliases(value):
    return aliases_for(value, PROFESSION_GROUPS)[1]
