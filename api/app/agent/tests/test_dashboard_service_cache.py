from pathlib import Path

from app.agent.dashboard_service import (
    _business_balances_by_nature,
    _create_tax_rag_query_service,
)
from app.ledger_analysis.account_balance_rules import AccountBalanceRule


def test_tax_rag_index_is_reused_between_agent_executor_builds() -> None:
    source_root = str(Path("../docs/source-corpus/fiscal").resolve())
    _create_tax_rag_query_service.cache_clear()

    first = _create_tax_rag_query_service(source_root, "disabled", "unused")
    second = _create_tax_rag_query_service(source_root, "disabled", "unused")

    assert first is second
    assert _create_tax_rag_query_service.cache_info().hits == 1


def test_business_balances_by_nature_use_account_normal_side() -> None:
    balances = _business_balances_by_nature(
        aggregation={
            "aggregations": {
                "account": {
                    "groups": [
                        _account_group(
                            "61365000", "XOF", balance=80, debit=100, credit=20
                        ),
                        _account_group(
                            "70100000", "XOF", balance=-60, debit=10, credit=70
                        ),
                        _account_group(
                            "40100000", "XOF", balance=-100, debit=0, credit=100
                        ),
                        _account_group(
                            "42100000", "XOF", balance=50, debit=50, credit=0
                        ),
                    ],
                },
            },
        },
        account_balance_rules=(
            AccountBalanceRule("6", "debit", "expenses", "", ""),
            AccountBalanceRule("7", "credit", "revenue", "", ""),
            AccountBalanceRule("40", "credit", "suppliers", "", ""),
            AccountBalanceRule("42", "variable", "personnel", "", ""),
        ),
    )

    by_nature = {item["nature"]: item for item in balances}
    assert by_nature["expenses"]["business_balance"] == 80
    assert by_nature["revenue"]["business_balance"] == 60
    assert by_nature["suppliers"]["business_balance"] == 100
    assert by_nature["personnel"]["business_balance"] is None
    assert by_nature["personnel"]["business_excluded_entry_count"] == 1


def _account_group(
    account: str,
    currency: str,
    *,
    balance: float,
    debit: float,
    credit: float,
) -> dict[str, object]:
    return {
        "key": account,
        "currency": currency,
        "entry_count": 1,
        "used_entry_count": 1,
        "excluded_entry_count": 0,
        "raw_amount_sum": debit + credit,
        "debit_total": debit,
        "credit_total": credit,
        "balance": balance,
    }
