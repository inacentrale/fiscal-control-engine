from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

SKIPPED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "__pycache__",
    "node_modules",
}
SKIPPED_SUFFIXES = {
    ".jpeg",
    ".jpg",
    ".png",
    ".pyc",
    ".xlsx",
    ".xlsm",
    ".zip",
}
MAX_FILE_BYTES = 1_000_000

SECRET_PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("openai_api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "non_empty_secret_env",
        re.compile(r"^\s*([A-Z0-9_]+)\s*=\s*['\"]?([^'\"\s#]+)"),
    ),
)
PLACEHOLDER_VALUES = {
    "",
    "changeme",
    "change-me",
    "example",
    "placeholder",
    "replace-me",
    "secret",
    "todo",
    "your-api-key",
    "your-secret",
}


@dataclass(frozen=True)
class SecretFinding:
    path: Path
    line_number: int
    rule_name: str


def scan_paths(paths: Iterable[Path]) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for path in _iter_files(paths):
        findings.extend(_scan_file(path))
    return findings


def main(argv: list[str] | None = None) -> int:
    raw_args = argv if argv is not None else sys.argv[1:]
    roots = [Path(arg) for arg in raw_args] if raw_args else [Path(".")]
    findings = scan_paths(roots)
    if findings:
        for finding in findings:
            print(f"{finding.path}:{finding.line_number}: {finding.rule_name}")
        return 1
    print("No secrets detected.")
    return 0


def _iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        resolved_path = path.resolve()
        if resolved_path.is_file() and _should_scan_file(resolved_path):
            yield resolved_path
            continue
        if not resolved_path.is_dir():
            continue
        for child in resolved_path.rglob("*"):
            if child.is_file() and _should_scan_file(child):
                yield child


def _should_scan_file(path: Path) -> bool:
    if any(part in SKIPPED_DIRECTORIES for part in path.parts):
        return False
    if path.suffix.lower() in SKIPPED_SUFFIXES:
        return False
    try:
        return path.stat().st_size <= MAX_FILE_BYTES
    except OSError:
        return False


def _scan_file(path: Path) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return findings

    for line_number, line in enumerate(lines, start=1):
        for rule_name, pattern in SECRET_PATTERNS:
            match = pattern.search(line)
            if match is None:
                continue
            if rule_name == "non_empty_secret_env":
                if not _should_check_env_assignment(path):
                    continue
                if not _is_sensitive_env_name(match.group(1)):
                    continue
                if _is_placeholder(match.group(2)):
                    continue
            findings.append(
                SecretFinding(
                    path=path,
                    line_number=line_number,
                    rule_name=rule_name,
                ),
            )
    return findings


def _should_check_env_assignment(path: Path) -> bool:
    return path.name.startswith(".env") or path.suffix.lower() in {
        ".cfg",
        ".conf",
        ".env",
        ".ini",
        ".properties",
        ".toml",
    }


def _is_sensitive_env_name(name: str) -> bool:
    normalized_name = name.upper()
    return (
        normalized_name.endswith("_API_KEY")
        or normalized_name.endswith("_PRIVATE_KEY")
        or any(
            part in {"PASSWORD", "SECRET", "TOKEN"}
            for part in normalized_name.split("_")
        )
    )


def _is_placeholder(value: str) -> bool:
    normalized_value = value.strip().strip("'\"").lower()
    return (
        normalized_value in PLACEHOLDER_VALUES
        or normalized_value.startswith("<")
        or normalized_value.startswith("${")
    )


if __name__ == "__main__":
    raise SystemExit(main())
