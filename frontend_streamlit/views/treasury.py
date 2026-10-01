import pandas as pd
import requests
import streamlit as st


def render_treasury(backend_url: str, session_id: str) -> None:
    treasury = requests.get(
        f"{backend_url}/api/sessions/{session_id}/tresorerie"
    ).json()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        "Total versé sur le compte",
        f"{treasury['total_depots']:.2f} €",
        f"{treasury['nb_versements']} virement(s)",
    )
    col2.metric(
        "Total retiré du compte",
        f"{treasury['total_retraits']:.2f} €",
        f"{treasury['nb_retraits']} retrait(s)",
    )
    col3.metric("Solde net versé", f"{treasury['net_versements']:.2f} €")
    col4.metric(
        "Coupons / dividendes perçus",
        f"{treasury['total_coupons']:.2f} €",
        f"{treasury['nb_coupons']} versement(s)",
    )

    if treasury["coupons_par_titre"]:
        st.subheader("Coupons perçus par titre")
        coupons = pd.DataFrame(
            list(treasury["coupons_par_titre"].items()),
            columns=["Titre", "Total coupons (€)"],
        ).sort_values("Total coupons (€)", ascending=False)
        st.dataframe(coupons, use_container_width=True, hide_index=True)
    