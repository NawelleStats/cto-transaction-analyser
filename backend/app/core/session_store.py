"""Stockage en mémoire des sessions d'analyse."""

from app.models.session import AnalysisSession

SESSIONS: dict[str, AnalysisSession] = {}
