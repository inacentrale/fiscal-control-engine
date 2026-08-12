from app.agent.orchestrator import _balance_reconciliation_answer
from app.excel_agent.domain import ToolExecutionResult


def _result(
    *,
    entry_count: int,
    used_entry_count: int,
    excluded_entry_count: int,
    balance: float = 0.0,
) -> tuple[ToolExecutionResult, ...]:
    return (
        ToolExecutionResult(
            tool_name="calculate_ledger_metrics",
            ok=True,
            output={
                "amount_field": "Montant devise document",
                "filters": {"account": "99999999"},
                "balance_reconciliation": {
                    "entry_count": entry_count,
                    "used_entry_count": used_entry_count,
                    "excluded_entry_count": excluded_entry_count,
                    "raw_amount_sum": 0.0,
                    "debit_total": 0.0,
                    "credit_total": 0.0,
                    "balance": balance,
                    "by_currency": {},
                    "by_posting_key": [],
                },
            },
        ),
    )


def test_no_matching_entry_is_not_presented_as_a_zero_balance() -> None:
    answer = _balance_reconciliation_answer(
        _result(entry_count=0, used_entry_count=0, excluded_entry_count=0)
    )

    assert answer is not None
    assert "Aucune écriture ne correspond" in answer
    assert "n'est pas un solde nul" in answer
    assert "Solde (débit" not in answer


def test_matching_but_unusable_entries_are_not_presented_as_zero_balance() -> None:
    answer = _balance_reconciliation_answer(
        _result(entry_count=2, used_entry_count=0, excluded_entry_count=2)
    )

    assert answer is not None
    assert "aucune n'est interprétable" in answer
    assert "Solde (débit" not in answer


def test_an_actual_calculated_zero_balance_remains_visible() -> None:
    answer = _balance_reconciliation_answer(
        _result(entry_count=2, used_entry_count=2, excluded_entry_count=0)
    )

    assert answer is not None
    assert "Solde comptable" in answer
    assert "0.00" in answer


def test_credit_balance_is_presented_without_technical_negative_sign() -> None:
    answer = _balance_reconciliation_answer(
        _result(
            entry_count=98,
            used_entry_count=98,
            excluded_entry_count=0,
            balance=-2_754_681_740,
        )
    )

    assert answer is not None
    assert "2 754 681 740.00 (créditeur)" in answer
    assert "-2 754 681 740" not in answer
    assert "Solde technique" not in answer
