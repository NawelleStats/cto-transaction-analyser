import requests
import streamlit as st


def render_import_panel(backend_url: str) -> None:
    with st.sidebar:
        st.header("1. Import des données")
        st.caption(
            "Tu peux importer plusieurs exports CSV (un par mois par exemple) : "
            "ils seront concaténés et les lignes en double automatiquement retirées."
        )
        files = st.file_uploader(
            "Export(s) CSV Boursorama",
            type="csv",
            accept_multiple_files=True,
        )
        if st.button(
            "Analyser",
            type="primary",
            disabled=not files,
            use_container_width=True,
        ):
            files_payload = [
                ("files", (file.name, file.getvalue(), "text/csv"))
                for file in files
            ]
            with st.spinner("Analyse en cours..."):
                try:
                    response = requests.post(
                        f"{backend_url}/api/sessions",
                        files=files_payload,
                        timeout=60,
                    )
                except requests.exceptions.RequestException as error:
                    st.error(
                        f"Impossible de contacter le backend ({backend_url}). "
                        f"Est-il démarré ?\n\n{error}"
                    )
                    st.stop()

            if response.status_code != 200:
                st.error(
                    f"Erreur : {response.json().get('detail', response.text)}"
                )
                st.stop()

            data = response.json()
            st.session_state.session_id = data["session_id"]
            st.session_state.resume = data
            st.success(
                f"{data['nb_fichiers']} fichier(s) chargé(s), "
                f"{data['nb_lignes_totales']} lignes."
            )

        if st.session_state.session_id and st.button(
            "Réinitialiser", use_container_width=True
        ):
            st.session_state.session_id = None
            st.session_state.resume = None
            st.rerun()