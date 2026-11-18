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


def number_forms(word):
    """Simple singular/plural alternatives for checking literal evidence."""
    forms = {word}
    if len(word) > 4 and word.endswith("s"):
        forms.add(word[:-1])
    if len(word) > 5 and word.endswith("es"):
        forms.add(word[:-2])
    return forms


def contains_number_variant(haystack, phrase):
    if contains_phrase(haystack, phrase):
        return True
    source = [number_forms(word) for word in tokens(haystack)]
    target = [number_forms(word) for word in tokens(phrase)]
    return bool(target) and any(
        all(available & wanted for available, wanted in zip(source[start:], target))
        for start in range(len(source) - len(target) + 1)
    )


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
