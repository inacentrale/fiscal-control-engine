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
