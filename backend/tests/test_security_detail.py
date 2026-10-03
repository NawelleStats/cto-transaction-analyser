import pandas as pd

from frontend_streamlit.views.security_detail import _calculate_indicators


def test_calculate_indicators_sums_realized_gains_and_evaluates_open_position():
    buys = pd.DataFrame([{"Quantité": 4, "Cours": 10.0}])
    pairs = pd.DataFrame([{"Gain (€)": 5.0}, {"Gain (€)": -2.0}])
    open_positions = pd.DataFrame(
        [
            {"Quantité restante": 2, "Prix achat": 10.0},
            {"Quantité restante": 2, "Prix achat": 14.0},
        ]
    )

    result = _calculate_indicators(buys, pairs, open_positions, 13.0)

    assert result["gain_realise"] == 3.0
    assert "vente ou prise de bénéfices" in result["signal"]
    assert "+4.00 €" in result["signal"]


def test_calculate_indicators_suggests_considering_buy_when_below_historical_basis():
    buys = pd.DataFrame(
        [
            {"Quantité": 1, "Cours": 10.0},
            {"Quantité": 1, "Cours": 12.0},
        ]
    )

    result = _calculate_indicators(buys, pd.DataFrame(), pd.DataFrame(), 10.0)

    assert "achat à considérer" in result["signal"]
    assert "PRU historique (11.00 €)" in result["signal"]
