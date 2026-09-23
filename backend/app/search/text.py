import re
import unicodedata


def normalize_text(value):
    folded = unicodedata.normalize("NFKD", str(value or "").casefold())
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain).split())


def tokens(value):
    return normalize_text(value).split()


def contains_phrase(haystack, phrase):
    source = f" {normalize_text(haystack)} "
    target = normalize_text(phrase)
    return bool(target) and f" {target} " in source


def unique_terms(values, limit=24):
    output = []
    seen = set()
    for value in values:
        for word in tokens(value):
            if len(word) < 2 or word in seen:
                continue
            seen.add(word)
            output.append(word)
            if len(output) >= limit:
                return output
    return output
