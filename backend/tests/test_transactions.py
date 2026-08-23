from io import StringIO

import pandas as pd
import pytest

from app.core.config import Settings
from app.services.transactions import (
    apparier_fifo,
    calculer_tresorerie,
    charger_et_concatener,
    charger_un_fichier,
    extraire_transactions,
    lignes_non_categorisees,
    stats_par_titre,
)

CSV_HEADER = "Date opération;Date valeur;Opération;Valeur;Code ISIN;Montant;Quantité;Cours\n"


def make_transactions(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_charger_un_fichier_parse_dates_prices_and_categories():
    csv = CSV_HEADER + (
        "01/01/2026;01/01/2026;ACHAT;Action A;FR0001;-10;1;1 234,50 €\n"
        "02/01/2026;02/01/2026;COUPON;Action A;FR0001;2;0;0,00 €\n"
        "03/01/2026;03/01/2026;FRAIS;Action A;FR0001;-1;0;0,00 €\n"
    )

    result = charger_un_fichier(StringIO(csv))

    assert result["Date opération"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
    ]
    assert result["Cours"].tolist() == [1234.5, 0.0, 0.0]
    assert result["Catégorie"].tolist() == ["ACHAT", "COUPON", "AUTRE"]


def test_charger_et_concatener_removes_exact_duplicates_and_sorts():
    row = "02/01/2026;02/01/2026;ACHAT;Action A;FR0001;-10;1;10,00 €\n"
    earlier_row = "01/01/2026;01/01/2026;VENTE;Action A;FR0001;12;1;12,00 €\n"

    result, duplicate_count = charger_et_concatener(
        [StringIO(CSV_HEADER + row), StringIO(CSV_HEADER + row + earlier_row)]
    )

    assert duplicate_count == 1
    assert len(result) == 2
    assert result["Date opération"].is_monotonic_increasing


def test_apparier_fifo_matches_oldest_lots_and_keeps_remainder_open():
    transactions = make_transactions(
        [
            {"Date opération": pd.Timestamp("2026-01-01"), "Code ISIN": "FR0001", "Valeur": "Action A", "Catégorie": "ACHAT", "Cours": 10.0, "Quantité": 2},
            {"Date opération": pd.Timestamp("2026-01-02"), "Code ISIN": "FR0001", "Valeur": "Action A", "Catégorie": "ACHAT", "Cours": 12.0, "Quantité": 3},
            {"Date opération": pd.Timestamp("2026-01-03"), "Code ISIN": "FR0001", "Valeur": "Action A", "Catégorie": "VENTE", "Cours": 15.0, "Quantité": 4},
        ]
    )

    closed, opened, warnings = apparier_fifo(transactions)

    assert warnings == []
    assert closed["Quantité"].tolist() == [2, 2]
    assert closed["Prix achat"].tolist() == [10.0, 12.0]
    assert closed["Gain (€)"].tolist() == [10.0, 6.0]
    assert opened["Quantité restante"].tolist() == [1]


def test_apparier_fifo_warns_when_sale_exceeds_available_purchases():
    transactions = make_transactions(
        [
            {"Date opération": pd.Timestamp("2026-01-01"), "Code ISIN": "FR0001", "Valeur": "Action A", "Catégorie": "VENTE", "Cours": 15.0, "Quantité": 1},
        ]
    )

    closed, opened, warnings = apparier_fifo(transactions)

    assert closed.empty
    assert opened.empty
    assert len(warnings) == 1
    assert "sans achat correspondant" in warnings[0]


def test_calculer_tresorerie_and_stats_group_results():
    data = pd.DataFrame(
        [
            {"Catégorie": "VIREMENT", "Montant": 100.0, "Valeur": "Cash"},
            {"Catégorie": "VIREMENT", "Montant": -25.0, "Valeur": "Cash"},
            {"Catégorie": "COUPON", "Montant": 4.5, "Valeur": "Action A"},
        ]
    )
    cash = calculer_tresorerie(data)
    closed = pd.DataFrame(
        [
            {"Valeur": "Action A", "Gain (€)": 10.0, "Gain (%)": 20.0, "Durée détention (j)": 5},
            {"Valeur": "Action A", "Gain (€)": -2.0, "Gain (%)": -4.0, "Durée détention (j)": 3},
        ]
    )

    stats = stats_par_titre(closed)

    assert cash == {
        "total_depots": 100.0,
        "total_retraits": 25.0,
        "net_versements": 75.0,
        "total_coupons": 4.5,
        "nb_versements": 1,
        "nb_retraits": 1,
        "nb_coupons": 1,
        "coupons_par_titre": {"Action A": 4.5},
    }
    assert stats.loc[0, "Nb_trades"] == 2
    assert stats.loc[0, "Gain_total_euros"] == 8.0
    assert stats.loc[0, "Taux de réussite (%)"] == 50.0


def test_missing_csv_columns_raise_a_clear_error():
    with pytest.raises(ValueError, match="Colonnes manquantes"):
        charger_un_fichier(StringIO("Date opération;Valeur\n01/01/2026;Action A\n"))


def test_lignes_non_categorisees_filters_other_operations():
    data = pd.DataFrame({"Catégorie": ["ACHAT", "AUTRE"], "Valeur": ["A", "B"]})

    result = lignes_non_categorisees(data)

    assert result["Valeur"].tolist() == ["B"]


def test_settings_parse_configured_csv_columns():
    settings = Settings(
        CSV_REQUIRED_COLUMNS=(
            "Date opération,Date valeur,Opération,Valeur,Code ISIN,Montant,Quantité,Cours,Compte"
        )
    )

    assert settings.csv_required_columns[-1] == "Compte"


def test_settings_reject_incomplete_csv_columns():
    settings = Settings(CSV_REQUIRED_COLUMNS="Valeur, Code ISIN, Montant")

    with pytest.raises(ValueError, match="colonnes métier obligatoires"):
        settings.csv_required_columns
