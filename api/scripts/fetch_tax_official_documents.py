from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen

from app.rag_source.official_document_manifest import (
    OfficialDocumentManifestEntry,
    load_official_document_manifest,
)


def main() -> int:
    arguments = _arguments()
    repository_root = Path(__file__).parents[2]
    manifest_path = repository_root / arguments.manifest
    entries = load_official_document_manifest(manifest_path)
    failures: list[str] = []
    for entry in entries:
        destination = repository_root / entry.local_path
        if not destination.exists() and arguments.download_missing:
            _download(entry, destination)
        error = _verification_error(entry, destination)
        if error is not None:
            failures.append(error)
        else:
            print(f"verified {entry.source_id}: {entry.local_path}")
    for failure in failures:
        print(f"ERROR {failure}")
    return 1 if failures else 0


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download and verify official Burkina Faso tax documents.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/reference/bf-tax-official-document-manifest.csv"),
    )
    parser.add_argument("--download-missing", action="store_true")
    return parser.parse_args()


def _download(entry: OfficialDocumentManifestEntry, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.part")
    request = Request(
        entry.official_url,
        headers={"User-Agent": "fiscal-control-engine-source-audit/1.0"},
    )
    try:
        with urlopen(request, timeout=60) as response:  # noqa: S310
            content = response.read()
        if not content.startswith(b"%PDF-"):
            raise ValueError(f"{entry.source_id}: downloaded content is not a PDF")
        temporary.write_bytes(content)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _verification_error(
    entry: OfficialDocumentManifestEntry,
    destination: Path,
) -> str | None:
    if not destination.is_file():
        return f"{entry.source_id}: missing {entry.local_path}"
    content = destination.read_bytes()
    if len(content) != entry.byte_size:
        return f"{entry.source_id}: unexpected byte size"
    if sha256(content).hexdigest() != entry.sha256:
        return f"{entry.source_id}: SHA-256 mismatch"
    return None


if __name__ == "__main__":
    raise SystemExit(main())
