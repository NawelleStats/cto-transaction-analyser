from fastapi import APIRouter, HTTPException, File, UploadFile
import io
import uuid
from pathlib import Path
from typing import List

import pandas as pd

from app.services.transactions import (
    collecter_exports_telechargements,
    charger_et_concatener,
    extraire_transactions,
    apparier_fifo,
    stats_par_titre,
    calculer_tresorerie,
    lignes_non_categorisees,
)           
from app.core.session_store import SESSIONS
from app.core.config import settings
from app.models.session import AnalysisSession

router = APIRouter()

def _df_to_records(df: pd.DataFrame) -> list[dict]:
    """Convertit un DataFrame en liste de dicts sérialisables en JSON (dates -> ISO)."""
    if df is None or df.empty:
        return []
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")


def _get_session(session_id: str) -> AnalysisSession:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session introuvable ou expirée. Ré-importe tes fichiers.",
        )
    return session


@router.post("/api/imports/telechargements")
def collecter_telechargements():
    try:
        fichiers = collecter_exports_telechargements(
            Path.home() / "Downloads", settings.transactions_data_dir
        )
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Impossible de copier les exports téléchargés : {exc}",
        ) from exc

    return {
        "nb_fichiers": len(fichiers),
        "fichiers": [fichier.name for fichier in fichiers],
        "destination": str(settings.transactions_data_dir),
    }


@router.post("/api/sessions")
async def creer_session(files: List[UploadFile] = File(...)):
    """Upload d'un ou plusieurs exports CSV Boursorama (mois différents),
    concaténation, dédoublonnage et calcul complet (FIFO, stats, trésorerie).
    """
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier fourni.")

    try:
        sources = [io.BytesIO(await f.read()) for f in files]
        df, nb_doublons = charger_et_concatener(sources)
    except Exception as exc:  # noqa: BLE001 - on remonte un message clair au front
        raise HTTPException(status_code=400, detail=f"Erreur de lecture des fichiers : {exc}") from exc

    df_transactions = extraire_transactions(df)
    df_positions_closes, df_positions_ouvertes, avertissements = apparier_fifo(df_transactions)
    df_stats = stats_par_titre(df_positions_closes)
    tresorerie = calculer_tresorerie(df)
    df_autres = lignes_non_categorisees(df)

    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "df": df,
        "df_transactions": df_transactions,
        "df_positions_closes": df_positions_closes,
        "df_positions_ouvertes": df_positions_ouvertes,
        "df_stats": df_stats,
        "tresorerie": tresorerie,
        "avertissements": avertissements,
        "df_autres": df_autres,
    }

    return {
        "session_id": session_id,
        "nb_fichiers": len(files),
        "nb_lignes_totales": len(df),
        "nb_doublons_retires": nb_doublons,
        "nb_transactions": len(df_transactions),
        "nb_titres": int(df_transactions["Valeur"].nunique()) if not df_transactions.empty else 0,
        "periode": {
            "debut": df["Date opération"].min().strftime("%Y-%m-%d") if not df.empty else None,
            "fin": df["Date opération"].max().strftime("%Y-%m-%d") if not df.empty else None,
        },
        "avertissements": avertissements,
        "nb_lignes_non_categorisees": len(df_autres),
    }


@router.get("/api/sessions/{session_id}/titres")
def get_titres(session_id: str):
    df_t = _get_session(session_id)["df_transactions"]
    return sorted(df_t["Valeur"].unique().tolist()) if not df_t.empty else []


@router.get("/api/sessions/{session_id}/transactions")
def get_transactions(session_id: str):
    return _df_to_records(_get_session(session_id)["df_transactions"])


@router.get("/api/sessions/{session_id}/positions/fermees")
def get_positions_fermees(session_id: str):
    return _df_to_records(_get_session(session_id)["df_positions_closes"])


@router.get("/api/sessions/{session_id}/positions/ouvertes")
def get_positions_ouvertes(session_id: str):
    return _df_to_records(_get_session(session_id)["df_positions_ouvertes"])


@router.get("/api/sessions/{session_id}/stats-titres")
def get_stats_titres(session_id: str):
    return _df_to_records(_get_session(session_id)["df_stats"])


@router.get("/api/sessions/{session_id}/tresorerie")
def get_tresorerie(session_id: str):
    return _get_session(session_id)["tresorerie"]


@router.get("/api/sessions/{session_id}/lignes-non-categorisees")
def get_lignes_non_categorisees(session_id: str):
    return _df_to_records(_get_session(session_id)["df_autres"])


@router.get("/api/sessions/{session_id}/graphique/{titre}")
def get_graphique(session_id: str, titre: str):
    session = _get_session(session_id)
    df_t = session["df_transactions"]
    df_pc = session["df_positions_closes"]
    df_po = session["df_positions_ouvertes"]

    achats = df_t[(df_t["Valeur"] == titre) & (df_t["Catégorie"] == "ACHAT")]
    ventes = df_t[(df_t["Valeur"] == titre) & (df_t["Catégorie"] == "VENTE")]
    paires = df_pc[df_pc["Valeur"] == titre] if not df_pc.empty else pd.DataFrame()
    ouvertes = df_po[df_po["Valeur"] == titre] if not df_po.empty else pd.DataFrame()

    if achats.empty and ventes.empty:
        raise HTTPException(status_code=404, detail=f"Aucune transaction pour « {titre} ».")

    return {
        "titre": titre,
        "achats": _df_to_records(achats[["Date opération", "Cours", "Quantité"]]),
        "ventes": _df_to_records(ventes[["Date opération", "Cours", "Quantité"]]),
        "paires": _df_to_records(paires),
        "positions_ouvertes": _df_to_records(ouvertes),
    }

@router.get("/api/sessions/{session_id}/isin-vers-ticker/{isin}")
def resolve_isin(isin: str):
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    headers = {"User-Agent": "Mozilla/5.0"}
    params = {"q": isin, "quotesCount": 1, "newsCount": 0}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        data = resp.json()
        if "quotes" in data and len(data["quotes"]) > 0:
            return {"ticker": data["quotes"][0]["symbol"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ticker": None}

