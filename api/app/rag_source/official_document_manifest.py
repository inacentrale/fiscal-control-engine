import csv
import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class DocumentStorageStatus(StrEnum):
    VERSIONED = "versioned"
    LOCAL_CACHE = "local_cache"


@dataclass(frozen=True)
class OfficialDocumentManifestEntry:
    source_id: str
    official_url: str
    local_path: Path
    sha256: str
    byte_size: int
    verified_on: date
    storage_status: DocumentStorageStatus

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.official_url.startswith("https://"):
            raise ValueError("official_url must use HTTPS")
        if self.local_path.is_absolute() or ".." in self.local_path.parts:
            raise ValueError("local_path must stay relative to the repository")
        if _SHA256_PATTERN.fullmatch(self.sha256) is None:
            raise ValueError("sha256 must contain 64 lowercase hexadecimal characters")
        if self.byte_size <= 0:
            raise ValueError("byte_size must be positive")


def load_official_document_manifest(
    source_path: Path,
) -> tuple[OfficialDocumentManifestEntry, ...]:
    with source_path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        required = {
            "source_id",
            "official_url",
            "local_path",
            "sha256",
            "byte_size",
            "verified_on",
            "storage_status",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("invalid official document manifest columns")
        entries = tuple(_entry(row) for row in reader)
    if len({entry.source_id for entry in entries}) != len(entries):
        raise ValueError("manifest source_id values must be unique")
    if len({entry.local_path for entry in entries}) != len(entries):
        raise ValueError("manifest local_path values must be unique")
    return entries


def _entry(row: dict[str, str | None]) -> OfficialDocumentManifestEntry:
    values = {key: (value or "").strip() for key, value in row.items()}
    try:
        return OfficialDocumentManifestEntry(
            source_id=values["source_id"],
            official_url=values["official_url"],
            local_path=Path(values["local_path"]),
            sha256=values["sha256"],
            byte_size=int(values["byte_size"]),
            verified_on=date.fromisoformat(values["verified_on"]),
            storage_status=DocumentStorageStatus(values["storage_status"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid official document manifest row") from exc
