import pandas as pd
import requests
import streamlit as st


def render_performance(backend_url: str, session_id: str) -> None:
    session_url = f"{backend_url}/api/sessions/{session_id}"

    st.subheader("Statistiques par titre (trades clôturés)")
    stats = pd.DataFrame(
        requests.get(f"{session_url}/stats-titres").json()
    )
    if stats.empty:
        st.info("Aucun trade clôturé (achat + vente appariés) pour l'instant.")
    else:
        st.dataframe(stats, use_container_width=True, hide_index=True)

    st.subheader("Positions clôturées — détail")
    closed_positions = pd.DataFrame(
        requests.get(f"{session_url}/positions/fermees").json()
    )
    st.dataframe(closed_positions, use_container_width=True, hide_index=True)

    st.subheader("Positions encore ouvertes")
    open_positions = pd.DataFrame(
        requests.get(f"{session_url}/positions/ouvertes").json()
    )
    st.dataframe(open_positions, use_container_width=True, hide_index=True)
