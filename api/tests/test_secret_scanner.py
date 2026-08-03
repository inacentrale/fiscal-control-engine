from pathlib import Path

import pytest

from scripts.secret_scanner import main, scan_paths


def test_secret_scanner_detects_secret_without_storing_value(tmp_path: Path) -> None:
    source_path = tmp_path / ".env"
    secret_value = "sk-" + "testsecretvalue1234567890"
    source_path.write_text(
        f"OPENAI_API_KEY={secret_value}\n",
        encoding="utf-8",
    )

    findings = scan_paths([source_path])

    assert len(findings) == 2
    assert {finding.rule_name for finding in findings} == {
        "non_empty_secret_env",
        "openai_api_key",
    }
    assert secret_value not in repr(findings)


def test_secret_scanner_allows_empty_and_placeholder_env_values(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / ".env.example"
    source_path.write_text(
        "OPENAI_API_KEY=\n"
        "GITHUB_TOKEN=your-secret\n"
        "PASSWORD=<set-locally>\n",
        encoding="utf-8",
    )

    assert scan_paths([source_path]) == []


def test_secret_scanner_main_returns_failure_when_secret_is_found(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = tmp_path / ".env"
    token = "ghp_" + "123456789012345678901234"
    source_path.write_text(
        f"GITHUB_TOKEN={token}\n",
        encoding="utf-8",
    )

    exit_code = main([str(source_path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "github_token" in output
    assert token not in output
