import re
import unicodedata

_CANONICAL_KINDS = {
    "ifu": "IFU",
    "numero ifu": "IFU",
    "n ifu": "IFU",
    "nif": "NIF",
    "numero nif": "NIF",
    "tin": "TIN",
    "tax identification number": "TIN",
    "tax id": "TAX_ID",
    "taxpayer identifier": "TAX_ID",
    "identifiant fiscal": "TAX_ID",
    "numero fiscal": "TAX_ID",
}


def infer_identifier_kind(source_label: str) -> str | None:
    """Return a kind derived from the source label, never from the value shape."""
    normalized = _normalize_label(source_label)
    canonical = _CANONICAL_KINDS.get(normalized)
    if canonical is not None:
        return canonical
    markers = ("identifiant", "identification", "identifier", "taxpayer")
    if not any(marker in normalized for marker in markers):
        return None
    return normalized.replace(" ", "_").upper()


def normalize_explicit_identifier_kind(value: str) -> str | None:
    normalized = _normalize_label(value)
    if not normalized:
        return None
    return _CANONICAL_KINDS.get(normalized, normalized.replace(" ", "_").upper())


def _normalize_label(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()
