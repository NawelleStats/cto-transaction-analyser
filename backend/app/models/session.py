"""Modèles internes utilisés pour conserver le résultat d'une analyse."""

from typing import TypedDict

import pandas as pd


class AnalysisSession(TypedDict):
    df: pd.DataFrame
    df_transactions: pd.DataFrame
    df_positions_closes: pd.DataFrame
    df_positions_ouvertes: pd.DataFrame
    df_stats: pd.DataFrame
    tresorerie: dict
    avertissements: list[str]
    df_autres: pd.DataFrame
