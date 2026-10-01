import streamlit as st


def render_summary(resume: dict) -> None:
    if resume.get("nb_doublons_retires"):
        st.caption(
            f"ℹ️ {resume['nb_doublons_retires']} ligne(s) en doublon "
            "(périodes se chevauchant entre fichiers) retirée(s) automatiquement."
        )
    for warning in resume.get("avertissements", []):
        st.warning(warning)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Transactions (achat/vente)", resume["nb_transactions"])
    col2.metric("Titres distincts", resume["nb_titres"])
    if resume["periode"]["debut"]:
        col3.metric(
            "Période couverte",
            f"{resume['periode']['debut']} → {resume['periode']['fin']}",
        )
    col4.metric("Lignes non catégorisées", resume["nb_lignes_non_categorisees"])
