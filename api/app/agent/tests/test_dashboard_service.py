from app.agent.dashboard_service import _dashboard_charts


def test_dashboard_exposes_period_debit_credit_and_cumulative_balance_charts() -> None:
    charts = _dashboard_charts(
        metrics={},
        aggregation={
            "aggregations": {
                "period": {
                    "groups": [
                        {
                            "key": "1",
                            "entry_count": 3,
                            "amount_sum": 70.0,
                            "currency": "XOF",
                            "debit_total": 100.0,
                            "credit_total": 30.0,
                            "balance": 70.0,
                        },
                        {
                            "key": "2",
                            "entry_count": 2,
                            "amount_sum": -20.0,
                            "currency": "XOF",
                            "debit_total": 50.0,
                            "credit_total": 70.0,
                            "balance": -20.0,
                        },
                    ],
                },
            },
        },
        quality={},
        tax_candidates={},
    )

    by_id = {chart.chart_id: chart for chart in charts}

    assert by_id["debit_credit_by_period"].labels == [
        str(index) for index in range(1, 13)
    ]
    assert by_id["debit_credit_by_period"].series == [
        {"name": "Débit", "values": [100.0, 50.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]},
        {"name": "Crédit", "values": [30.0, 70.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]},
        {"name": "Solde", "values": [70.0, -20.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]},
    ]
    assert by_id["cumulative_balance_by_period"].values == [
        70.0,
        50.0,
        50.0,
        50.0,
        50.0,
        50.0,
        50.0,
        50.0,
        50.0,
        50.0,
        50.0,
        50.0,
    ]


def test_dashboard_exposes_account_class_currency_year_and_quality_charts() -> None:
    charts = _dashboard_charts(
        metrics={},
        aggregation={
            "aggregations": {
                "account_class": {
                    "groups": [
                        {
                            "key": "Classe 6",
                            "entry_count": 8,
                            "amount_sum": 1000.0,
                            "currency": "XOF",
                            "debit_total": 1200.0,
                            "credit_total": 200.0,
                            "balance": 1000.0,
                        },
                        {
                            "key": "Classe 7",
                            "entry_count": 3,
                            "amount_sum": -700.0,
                            "currency": "XOF",
                            "debit_total": 50.0,
                            "credit_total": 750.0,
                            "balance": -700.0,
                        },
                    ],
                },
                "currency": {
                    "groups": [
                        {"key": "XOF", "entry_count": 11, "amount_sum": 300.0},
                    ],
                },
                "fiscal_year": {
                    "groups": [
                        {"key": "2025", "entry_count": 7, "amount_sum": 200.0},
                    ],
                },
            },
        },
        quality={
            "issues": [
                {
                    "canonical_field": "account",
                    "affected_count": 4,
                },
                {
                    "canonical_field": "amount",
                    "affected_count": 2,
                },
            ],
        },
        tax_candidates={},
    )

    by_id = {chart.chart_id: chart for chart in charts}

    assert by_id["amount_by_account_class"].labels == ["Classe 6", "Classe 7"]
    assert by_id["entries_by_account_class"].values == [8, 3]
    assert by_id["debit_credit_by_account_class"].series == [
        {"name": "Débit", "values": [1200.0, 50.0]},
        {"name": "Crédit", "values": [200.0, 750.0]},
        {"name": "Solde", "values": [1000.0, -700.0]},
    ]
    assert by_id["amount_by_currency"].labels == ["XOF"]
    assert by_id["amount_by_fiscal_year"].labels == ["2025"]
    assert by_id["data_quality_by_field"].values == [4, 2]
