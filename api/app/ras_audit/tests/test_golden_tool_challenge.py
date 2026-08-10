from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import cast

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, create_session_factory
from app.excel_agent.excel_tools import ExcelAgentTools
from app.excel_agent.tool_executor import ExcelToolExecutor
from app.excel_agent.tool_registry import create_excel_tool_registry
from app.llm.domain import ToolCall
from app.ras_audit.account_mapping import load_ras_ledger_account_mappings
from app.ras_audit.fact_context import (
    RasFactContextAttestor,
    RasFactExtraction,
)
from app.ras_audit.golden_dataset import load_golden_dataset
from app.ras_audit.persistence import SqlAlchemyRasAuditRepository

FIXTURES = Path(__file__).parent / "fixtures"


def test_accounting_tools_reconcile_to_golden_workbook() -> None:
    dataset = load_golden_dataset(FIXTURES / "golden")
    expected_candidate_count = sum(
        scenario.expected_candidate_signal for scenario in dataset.scenarios
    )
    workbook_path = _write_golden_workbook()
    repository = SqlAlchemyRasAuditRepository(_session_factory())
    attestor = RasFactContextAttestor("golden-signing-key-with-at-least-32-bytes")
    executor = ExcelToolExecutor(
        tools=ExcelAgentTools(allowed_root=workbook_path.parent),
        registry=create_excel_tool_registry(),
        ras_ledger_account_mappings=load_ras_ledger_account_mappings(
            FIXTURES / "account-mapping/valid.csv"
        ),
        ras_fact_context_attestor=attestor,
        ras_audit_repository=repository,
    )

    try:
        normalized = _execute(executor, "normalize_gl", workbook_path)
        readiness = _execute(executor, "assess_gl_readiness", workbook_path)
        reconstructed = _execute(
            executor,
            "reconstruct_accounting_entry",
            workbook_path,
        )
        candidates = _execute(executor, "detect_ras_candidates", workbook_path)
        counterparts = _execute(executor, "find_ras_counterpart", workbook_path)
        token = attestor.issue(
            message="Audit RAS du jeu d'or synthetique.",
            extraction=RasFactExtraction((), (), ()),
            session_id="golden-session",
            file_id="golden-file",
        )
        batch = _execute(
            executor,
            "run_ras_audit_batch",
            workbook_path,
            fact_token=token,
        )
        report = executor.execute(
            ToolCall(
                name="generate_ras_audit_report",
                arguments={"audit_id": cast(str, batch["audit_id"])},
            ),
            ras_fact_context_token=token,
        )
    finally:
        workbook_path.unlink(missing_ok=True)

    assert normalized["row_count"] == 26
    assert normalized["normalized_count"] == 26
    assert normalized["issue_counts"] == {"unknown_posting_key": 1}
    readiness_by_capability = {
        item["capability"]: item
        for item in cast(list[dict[str, object]], readiness["readiness"])
    }
    assert readiness_by_capability["candidate_detection"]["status"] == "degraded"
    assert readiness_by_capability["counterpart_reconciliation"]["status"] == (
        "blocked"
    )
    assert reconstructed["entry_count"] == 11
    assert reconstructed["grouped_line_count"] == 26
    assert reconstructed["ungrouped_line_count"] == 0
    assert reconstructed["issue_counts"] == {
        "unbalanced_accounting_entry": 2,
        "unknown_posting_key": 1,
    }
    assert candidates["candidate_piece_count"] == expected_candidate_count == 7
    assert counterparts["candidate_piece_count"] == 6
    assert counterparts["status_counts"] == {
        "found_in_same_entry": 3,
        "potential_related_entry": 1,
        "not_found_in_scope": 0,
        "indeterminate": 2,
    }
    assert counterparts["source_scope_complete"] is False
    assert "missing_or_unknown_posting_keys" in cast(
        list[object],
        counterparts["source_scope_blockers"],
    )
    assert batch["candidate_count"] == expected_candidate_count
    assert batch["source_scope_complete"] is False
    assert report.ok is True
    assert report.output["case_count"] == expected_candidate_count
    persisted = repository.get(str(batch["audit_id"]))
    assert persisted is not None
    assert len(persisted.cases) == expected_candidate_count
    assert Counter(case.certainty for case in persisted.cases) == {
        "potential": 5,
        "indeterminate": 2,
    }


def _execute(
    executor: ExcelToolExecutor,
    tool_name: str,
    workbook_path: Path,
    *,
    fact_token: str | None = None,
) -> dict[str, object]:
    result = executor.execute(
        ToolCall(
            name=tool_name,
            arguments={"file_path": str(workbook_path), "sheet_name": "GL"},
        ),
        ras_fact_context_token=fact_token,
    )
    assert result.ok is True, result.error_message
    return result.output


def _write_golden_workbook() -> Path:
    dataset = load_golden_dataset(FIXTURES / "golden")
    rows = []
    for scenario in dataset.scenarios:
        for entry in scenario.entries:
            rows.append(
                {
                    "Societe": entry.company_code,
                    "Exercice": entry.fiscal_year,
                    "Periode": entry.period,
                    "Journal": entry.journal,
                    "Numero piece": entry.document_number,
                    "Numero ligne": entry.line_number,
                    "Date comptable": entry.posting_date,
                    "Compte": entry.account_number,
                    "Tiers": entry.partner_id,
                    "Libelle": entry.label,
                    "Cle de comptabilisation": entry.posting_key,
                    "Montant devise document": entry.amount,
                    "Devise du document": entry.currency,
                }
            )
    with NamedTemporaryFile(
        suffix="-golden-ras-audit.xlsx",
        dir=Path.cwd(),
        delete=False,
    ) as temporary_file:
        workbook_path = Path(temporary_file.name)
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name="GL", index=False)
    return workbook_path


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return create_session_factory(engine)
