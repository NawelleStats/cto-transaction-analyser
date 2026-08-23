"""Services d'analyse des exports CSV Boursorama."""

from __future__ import annotations

from collections import deque
from typing import BinaryIO, Iterable

import numpy as np
import pandas as pd

from app.core.config import settings


def _nettoyer_cours(serie: pd.Series) -> pd.Series:
    """Convertit une série de cours au format Boursorama en nombres flottants."""
    return (
        serie.astype(str)
        .str.replace("€", "", regex=False)
        .str.replace("\xa0", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )


def _categoriser(op: pd.Series) -> np.ndarray:
    """Associe chaque libellé d'opération à une catégorie pour rassembler les opérations similaires.
    Exemples : ACHAT COMPTANT et ACHAT ETRANGER COMPTANT."""
    op_upper = op.str.upper()
    return np.select(
        [
            op_upper.str.contains("ACHAT"),
            op_upper.str.contains("VENTE"),
            op_upper.str.contains("COUPON") | op_upper.str.contains("DIVIDENDE"),
            op_upper.str.contains("VIR"),
        ],
        ["ACHAT", "VENTE", "COUPON", "VIREMENT"],
        default="AUTRE",
    )


def charger_un_fichier(source: BinaryIO | str) -> pd.DataFrame:
    """Charge et normalise un export CSV Boursorama.

    Args:
        source: Chemin du fichier ou flux binaire compatible avec pandas.

    Returns:
        DataFrame nettoyé avec dates converties, cours numériques et catégorie.

    Raises:
        ValueError: Si une colonne configurée est absente de l'export.
    """
    df = pd.read_csv(source, sep=";", encoding="utf-8-sig")
    colonnes_attendues = settings.csv_required_columns
    manquantes = set(colonnes_attendues) - set(df.columns)
    if manquantes:
        raise ValueError(
            f"Colonnes manquantes : {sorted(manquantes)}. "
            "Le fichier ne ressemble pas à un export Boursorama standard "
            "(Historique des opérations)."
        )
    df["Date opération"] = pd.to_datetime(df["Date opération"], format="%d/%m/%Y")
    df["Date valeur"] = pd.to_datetime(df["Date valeur"], format="%d/%m/%Y")
    df["Cours"] = _nettoyer_cours(df["Cours"])
    df["Catégorie"] = _categoriser(df["Opération"])
    return df


def charger_et_concatener(sources: Iterable[BinaryIO | str]) -> tuple[pd.DataFrame, int]:
    """Charge plusieurs exports, les dédoublonne et les trie par date.

    Args:
        sources: Chemins ou flux correspondant aux exports à fusionner.

    Returns:
        Un tuple contenant le DataFrame final et le nombre de doublons retirés.
    """
    dfs = [charger_un_fichier(source) for source in sources]
    df = pd.concat(dfs, ignore_index=True)
    n_avant = len(df)
    df = df.drop_duplicates(subset=settings.csv_required_columns)
    n_doublons = n_avant - len(df)
    return df.sort_values("Date opération").reset_index(drop=True), n_doublons


def extraire_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Extrait les achats et ventes d'un DataFrame d'opérations."""
    return (
        df[df["Catégorie"].isin(["ACHAT", "VENTE"])]
        .sort_values("Date opération")
        .reset_index(drop=True)
    )


def apparier_fifo(df_transactions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Apparie les ventes avec les achats les plus anciens, titre par titre.

    Args:
        df_transactions: DataFrame contenant uniquement les achats et ventes,
            idéalement trié chronologiquement.

    Returns:
        Les positions clôturées, les lots encore ouverts et les avertissements
        concernant les ventes sans achat correspondant.
    """
    files_achats: dict[str, deque] = {}
    positions_closes = []
    avertissements = []
    for _, row in df_transactions.iterrows():
        isin = row["Code ISIN"]
        nom = row["Valeur"]
        files_achats.setdefault(isin, deque())
        if row["Catégorie"] == "ACHAT":
            files_achats[isin].append(
                {"date": row["Date opération"], "prix": row["Cours"], "quantite": row["Quantité"]}
            )
        elif row["Catégorie"] == "VENTE":
            qte_a_vendre = row["Quantité"]
            while qte_a_vendre > 0 and files_achats[isin]:
                achat = files_achats[isin][0]
                qte_matched = min(qte_a_vendre, achat["quantite"])
                positions_closes.append(
                    {
                        "Valeur": nom,
                        "ISIN": isin,
                        "Date achat": achat["date"],
                        "Prix achat": achat["prix"],
                        "Date vente": row["Date opération"],
                        "Prix vente": row["Cours"],
                        "Quantité": qte_matched,
                        "Durée détention (j)": (row["Date opération"] - achat["date"]).days,
                    }
                )
                achat["quantite"] -= qte_matched
                qte_a_vendre -= qte_matched
                if achat["quantite"] == 0:
                    files_achats[isin].popleft()
            if qte_a_vendre > 0:
                avertissements.append(
                    f"{nom} ({isin}) : {qte_a_vendre} titre(s) vendu(s) sans achat correspondant "
                    "dans les fichiers fournis (probablement achetés avant la période exportée)."
                )

    df_positions_closes = pd.DataFrame(positions_closes)
    if not df_positions_closes.empty:
        df_positions_closes["Gain (€)"] = (
            df_positions_closes["Prix vente"] - df_positions_closes["Prix achat"]
        ) * df_positions_closes["Quantité"]
        df_positions_closes["Gain (%)"] = (
            df_positions_closes["Prix vente"] / df_positions_closes["Prix achat"] - 1
        ) * 100

    noms_par_isin = (
        df_transactions.drop_duplicates("Code ISIN").set_index("Code ISIN")["Valeur"]
        if not df_transactions.empty
        else pd.Series(dtype=str)
    )
    positions_ouvertes = [
        {
            "Valeur": noms_par_isin.get(isin, isin),
            "ISIN": isin,
            "Date achat": achat["date"],
            "Prix achat": achat["prix"],
            "Quantité restante": achat["quantite"],
        }
        for isin, file_achats in files_achats.items()
        for achat in file_achats
    ]
    return df_positions_closes, pd.DataFrame(positions_ouvertes), avertissements


def stats_par_titre(df_positions_closes: pd.DataFrame) -> pd.DataFrame:
    """Calcule les statistiques agrégées des positions clôturées par titre."""
    if df_positions_closes.empty:
        return pd.DataFrame()
    stats = df_positions_closes.groupby("Valeur").agg(
        Nb_trades=("Gain (€)", "count"),
        Gain_total_euros=("Gain (€)", "sum"),
        Gain_moyen_pct=("Gain (%)", "mean"),
        Duree_moyenne_jours=("Durée détention (j)", "mean"),
    )
    stats["Taux de réussite (%)"] = df_positions_closes.groupby("Valeur")["Gain (€)"].apply(
        lambda gains: (gains > 0).mean() * 100
    )
    return stats.reset_index().sort_values("Gain_total_euros", ascending=False).round(2)


def calculer_tresorerie(df: pd.DataFrame) -> dict:
    """Calcule les dépôts, retraits et coupons à partir des opérations."""
    virements = df[df["Catégorie"] == "VIREMENT"]
    coupons = df[df["Catégorie"] == "COUPON"]
    total_depots = virements.loc[virements["Montant"] > 0, "Montant"].sum()
    total_retraits = -virements.loc[virements["Montant"] < 0, "Montant"].sum()
    total_coupons = coupons["Montant"].sum()
    return {
        "total_depots": round(float(total_depots), 2),
        "total_retraits": round(float(total_retraits), 2),
        "net_versements": round(float(total_depots - total_retraits), 2),
        "total_coupons": round(float(total_coupons), 2),
        "nb_versements": int((virements["Montant"] > 0).sum()),
        "nb_retraits": int((virements["Montant"] < 0).sum()),
        "nb_coupons": int(len(coupons)),
        "coupons_par_titre": (
            coupons.groupby("Valeur")["Montant"].sum().round(2).sort_values(ascending=False).to_dict()
            if not coupons.empty
            else {}
        ),
    }


def lignes_non_categorisees(df: pd.DataFrame) -> pd.DataFrame:
    """Retourne les opérations classées dans la catégorie ``AUTRE``."""
    return df[df["Catégorie"] == "AUTRE"]
