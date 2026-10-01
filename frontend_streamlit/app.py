"""Streamlit entry point for the CTO transaction analyzer."""

import os

import streamlit as st

from import_panel import render_import_panel
from views import (
    render_performance,
    render_security_detail,
    render_summary,
    render_treasury,
)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def main() -> None:
    st.set_page_config(
        page_title="Analyse CTO Boursorama", page_icon="📈", layout="wide"
    )
    st.title("📈 Analyse des transactions CTO — Boursorama")

    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "resume" not in st.session_state:
        st.session_state.resume = None

    render_import_panel(BACKEND_URL)

    if not st.session_state.session_id:
        st.info(
            "⬅️ Importe un ou plusieurs exports CSV Boursorama "
            "dans la barre latérale pour commencer."
        )
        st.stop()

    session_id = st.session_state.session_id
    render_summary(st.session_state.resume)

    performance_tab, detail_tab, treasury_tab = st.tabs(
        [
            "📊 Performance par titre",
            "🔍 Détail d'un titre",
            "💶 Trésorerie (virements & coupons)",
        ]
    )

    with performance_tab:
        render_performance(BACKEND_URL, session_id)
    with detail_tab:
        render_security_detail(BACKEND_URL, session_id)
    with treasury_tab:
        render_treasury(BACKEND_URL, session_id)


main()
