from app.agent.dashboard_service import _dashboard_charts


def test_dashboard_exposes_period_debit_credit_chart() -> None:
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
    ]
    assert "cumulative_balance_by_period" not in by_id


def test_dashboard_exposes_cumulative_resources_and_uses_by_period() -> None:
    charts = _dashboard_charts(
        metrics={},
        aggregation={"aggregations": {}},
        quality={},
        tax_candidates={},
        business_nature_by_dimension={
            "period": {
                "groups": [
                    {
                        "key": "1",
                        "resources_balance": 500.0,
                        "resources_entry_count": 2,
                        "uses_balance": 100.0,
                        "uses_entry_count": 1,
                        "unclassified_balance": 20.0,
                        "unclassified_entry_count": 1,
                    },
                    {
                        "key": "2",
                        "resources_balance": 300.0,
                        "resources_entry_count": 1,
                        "uses_balance": -40.0,
                        "uses_entry_count": 1,
                        "unclassified_balance": 0.0,
                        "unclassified_entry_count": 0,
                    },
                ],
            },
        },
    )

    by_id = {chart.chart_id: chart for chart in charts}

    assert by_id["cumulative_resources_by_period"].labels == [
        str(index) for index in range(1, 13)
    ]
    assert by_id["cumulative_resources_by_period"].values == [
        500.0,
        800.0,
        800.0,
        800.0,
        800.0,
        800.0,
        800.0,
        800.0,
        800.0,
        800.0,
        800.0,
        800.0,
    ]
    assert by_id["cumulative_uses_by_period"].values == [
        100.0,
        60.0,
        60.0,
        60.0,
        60.0,
        60.0,
        60.0,
        60.0,
        60.0,
        60.0,
        60.0,
        60.0,
    ]
    assert by_id["cumulative_resources_by_period"].metadata["currency"] == "XOF"
    assert "créditeurs" in by_id["cumulative_resources_by_period"].metadata["legend"]
    assert "débiteurs" in by_id["cumulative_uses_by_period"].metadata["legend"]


def test_dashboard_exposes_account_class_charts() -> None:
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
                            "business_balance": 1000.0,
                        },
                        {
                            "key": "Classe 7",
                            "entry_count": 3,
                            "amount_sum": -700.0,
                            "currency": "XOF",
                            "debit_total": 50.0,
                            "credit_total": 750.0,
                            "balance": -700.0,
                            "business_balance": 700.0,
                        },
                    ],
                },
            },
        },
        quality={},
        tax_candidates={},
    )

    by_id = {chart.chart_id: chart for chart in charts}

    assert by_id["amount_by_account_class"].labels == ["Classe 6", "Classe 7"]
    assert by_id["entries_by_account_class"].values == [8, 3]
    assert by_id["debit_credit_by_account_class"].series == [
        {"name": "Débit", "values": [1200.0, 50.0]},
        {"name": "Crédit", "values": [200.0, 750.0]},
        {"name": "Solde", "values": [1000.0, 700.0]},
    ]
    assert "amount_by_fiscal_year" not in by_id
    assert "amount_by_currency" not in by_id
    assert "data_quality_by_field" not in by_id


def test_dashboard_exposes_resources_and_uses_by_fiscal_year() -> None:
    charts = _dashboard_charts(
        metrics={},
        aggregation={"aggregations": {}},
        quality={},
        tax_candidates={},
        business_nature_by_dimension={
            "fiscal_year": {
                "groups": [
                    {
                        "key": "2024",
                        "resources_balance": 900.0,
                        "resources_entry_count": 3,
                        "uses_balance": 400.0,
                        "uses_entry_count": 2,
                        "unclassified_balance": 0.0,
                        "unclassified_entry_count": 0,
                    },
                    {
                        "key": "2025",
                        "resources_balance": 200.0,
                        "resources_entry_count": 1,
                        "uses_balance": 150.0,
                        "uses_entry_count": 1,
                        "unclassified_balance": 0.0,
                        "unclassified_entry_count": 0,
                    },
                ],
            },
        },
    )

    by_id = {chart.chart_id: chart for chart in charts}

    assert by_id["resources_by_fiscal_year"].labels == ["2024", "2025"]
    assert by_id["resources_by_fiscal_year"].values == [900.0, 200.0]
    assert by_id["uses_by_fiscal_year"].values == [400.0, 150.0]
    assert by_id["resources_by_fiscal_year"].metadata["currency"] == "XOF"
    assert "amount_by_fiscal_year" not in by_id


def test_dashboard_disambiguates_account_class_labels_and_uses_business_balance() -> (
    None
):
    charts = _dashboard_charts(
        metrics={},
        aggregation={
            "aggregations": {
                "account_class": {
                    "groups": [
                        {
                            "key": "Classe 4",
                            "entry_count": 5,
                            "amount_sum": -500.0,
                            "currency": "XOF",
                            "debit_total": 0.0,
                            "credit_total": 500.0,
                            "balance": -500.0,
                            "balance_side": "credit",
                            "normal_side": "credit",
                            "nature": "third_parties",
                            "business_balance": 500.0,
                        },
                        {
                            "key": "Classe 4",
                            "entry_count": 2,
                            "amount_sum": -100.0,
                            "currency": "EUR",
                            "debit_total": 0.0,
                            "credit_total": 100.0,
                            "balance": -100.0,
                            "balance_side": "credit",
                            "normal_side": "credit",
                            "nature": "third_parties",
                            "business_balance": 100.0,
                        },
                    ],
                },
            },
        },
        quality={},
        tax_candidates={},
    )

    by_id = {chart.chart_id: chart for chart in charts}

    assert by_id["amount_by_account_class"].labels == [
        "Classe 4 (XOF)",
        "Classe 4 (EUR)",
    ]
    assert by_id["amount_by_account_class"].values == [500.0, 100.0]
    assert by_id["entries_by_account_class"].labels == [
        "Classe 4 (XOF)",
        "Classe 4 (EUR)",
    ]
