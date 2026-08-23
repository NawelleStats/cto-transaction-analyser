"""Interface Streamlit — upload d'export(s) Boursorama et visualisation.

Lancer en local (avec le backend déjà démarré sur le port 8000) :
    streamlit run app.py
"""

import os

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Analyse CTO Boursorama", page_icon="📈", layout="wide")
st.title("📈 Analyse des transactions CTO — Boursorama")

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "resume" not in st.session_state:
    st.session_state.resume = None

# --- 1. Import -------------------------------------------------------------
with st.sidebar:
    st.header("1. Import des données")
    st.caption("Tu peux importer plusieurs exports CSV (un par mois par exemple) : ils seront concaténés et les lignes en double automatiquement retirées.")
    fichiers = st.file_uploader(
        "Export(s) CSV Boursorama",
        type="csv",
        accept_multiple_files=True,
    )
    if st.button("Analyser", type="primary", disabled=not fichiers, use_container_width=True):
        files_payload = [("files", (f.name, f.getvalue(), "text/csv")) for f in fichiers]
        with st.spinner("Analyse en cours..."):
            try:
                resp = requests.post(f"{BACKEND_URL}/api/sessions", files=files_payload, timeout=60)
            except requests.exceptions.RequestException as e:
                st.error(f"Impossible de contacter le backend ({BACKEND_URL}). Est-il démarré ?\n\n{e}")
                st.stop()
        if resp.status_code != 200:
            st.error(f"Erreur : {resp.json().get('detail', resp.text)}")
            st.stop()
        data = resp.json()
        st.session_state.session_id = data["session_id"]
        st.session_state.resume = data
        st.success(f"{data['nb_fichiers']} fichier(s) chargé(s), {data['nb_lignes_totales']} lignes.")

    if st.session_state.session_id and st.button("Réinitialiser", use_container_width=True):
        st.session_state.session_id = None
        st.session_state.resume = None
        st.rerun()

if not st.session_state.session_id:
    st.info("⬅️ Importe un ou plusieurs exports CSV Boursorama dans la barre latérale pour commencer.")
    st.stop()

session_id = st.session_state.session_id
resume = st.session_state.resume

# --- 2. Résumé / avertissements --------------------------------------------
if resume.get("nb_doublons_retires"):
    st.caption(
        f"ℹ️ {resume['nb_doublons_retires']} ligne(s) en doublon (périodes se chevauchant entre fichiers) "
        "retirée(s) automatiquement."
    )
for w in resume.get("avertissements", []):
    st.warning(w)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Transactions (achat/vente)", resume["nb_transactions"])
col2.metric("Titres distincts", resume["nb_titres"])
if resume["periode"]["debut"]:
    col3.metric("Période couverte", f"{resume['periode']['debut']} → {resume['periode']['fin']}")
col4.metric("Lignes non catégorisées", resume["nb_lignes_non_categorisees"])

tab_perf, tab_titre, tab_treso = st.tabs(
    ["📊 Performance par titre", "🔍 Détail d'un titre", "💶 Trésorerie (virements & coupons)"]
)

# --- Onglet performance ------------------------------------------------------
with tab_perf:
    st.subheader("Statistiques par titre (trades clôturés)")
    df_stats = pd.DataFrame(requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/stats-titres").json())
    if df_stats.empty:
        st.info("Aucun trade clôturé (achat + vente appariés) pour l'instant.")
    else:
        st.dataframe(df_stats, use_container_width=True, hide_index=True)

    st.subheader("Positions clôturées — détail")
    df_closes = pd.DataFrame(requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/positions/fermees").json())
    st.dataframe(df_closes, use_container_width=True, hide_index=True)

    st.subheader("Positions encore ouvertes")
    df_open = pd.DataFrame(requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/positions/ouvertes").json())
    st.dataframe(df_open, use_container_width=True, hide_index=True)

# --- Onglet détail d'un titre -------------------------------------------------
# with tab_titre:
#     titres = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/titres").json()
#     if not titres:
#         st.info("Aucun titre à afficher.")
#     else:
#         titre = st.selectbox("Choisis un titre", titres)
#         r = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/graphique/{titre}")
#         if r.status_code == 200:
#             d = r.json()
#             achats = pd.DataFrame(d["achats"])
#             ventes = pd.DataFrame(d["ventes"])
#             paires = pd.DataFrame(d["paires"])
#             ouvertes = pd.DataFrame(d["positions_ouvertes"])

#             fig = go.Figure()
#             if not achats.empty:
#                 fig.add_trace(
#                     go.Scatter(
#                         x=achats["Date opération"],
#                         y=achats["Cours"],
#                         mode="markers",
#                         marker=dict(symbol="triangle-up", size=13, color="#2ca02c"),
#                         name="Achat",
#                         text=[f"{q} titres" for q in achats["Quantité"]],
#                         hovertemplate="%{x}<br>%{y} €<br>%{text}<extra>Achat</extra>",
#                     )
#                 )
#             if not ventes.empty:
#                 fig.add_trace(
#                     go.Scatter(
#                         x=ventes["Date opération"],
#                         y=ventes["Cours"],
#                         mode="markers",
#                         marker=dict(symbol="triangle-down", size=13, color="#d62728"),
#                         name="Vente",
#                         text=[f"{q} titres" for q in ventes["Quantité"]],
#                         hovertemplate="%{x}<br>%{y} €<br>%{text}<extra>Vente</extra>",
#                     )
#                 )
#             for _, p in paires.iterrows():
#                 couleur = "#2ca02c" if p["Gain (€)"] >= 0 else "#d62728"
#                 fig.add_trace(
#                     go.Scatter(
#                         x=[p["Date achat"], p["Date vente"]],
#                         y=[p["Prix achat"], p["Prix vente"]],
#                         mode="lines",
#                         line=dict(color=couleur, dash="dash", width=1.5),
#                         opacity=0.45,
#                         showlegend=False,
#                         hoverinfo="skip",
#                     )
#                 )
#             if not ouvertes.empty:
#                 fig.add_trace(
#                     go.Scatter(
#                         x=ouvertes["Date achat"],
#                         y=ouvertes["Prix achat"],
#                         mode="markers",
#                         marker=dict(symbol="diamond", size=12, color="#ff7f0e"),
#                         name="Position ouverte",
#                         text=[f"{q} titres restants" for q in ouvertes["Quantité restante"]],
#                         hovertemplate="%{x}<br>%{y} €<br>%{text}<extra>Ouverte</extra>",
#                     )
#                 )

#             fig.update_layout(
#                 title=f"Historique des transactions — {titre}",
#                 xaxis_title="Date",
#                 yaxis_title="Cours (€)",
#                 height=550,
#                 legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
#             )
#             st.plotly_chart(fig, use_container_width=True)

#             if not paires.empty:
#                 st.subheader(f"Trades clôturés sur {titre}")
#                 st.dataframe(paires, use_container_width=True, hide_index=True)
#         else:
#             st.info("Pas de données pour ce titre.")

# import matplotlib.dates as mdates
# import matplotlib.pyplot as plt
# import matplotlib.ticker as ticker
# import pandas as pd
# import requests
# import streamlit as st

# try:
#     import yfinance as yf
# except ImportError:
#     yf = None

# with tab_titre:
#     titres = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/titres").json()
#     if not titres:
#         st.info("Aucun titre à afficher.")
#     else:
#         titre = st.selectbox("Choisis un titre", titres)
#         r = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/graphique/{titre}")
        
#         if r.status_code == 200:
#             d = r.json()
#             achats = pd.DataFrame(d["achats"])
#             ventes = pd.DataFrame(d["ventes"])
#             paires = pd.DataFrame(d["paires"])
#             ouvertes = pd.DataFrame(d["positions_ouvertes"])

#             # Unification des transactions (achats + ventes)
#             df_trans = pd.concat([achats, ventes], ignore_index=True)
            
#             df_h = None
#             ticker_symbol = None

#             # -------------------------------------------------------------
#             # 1. RÉSOLUTIONS DU TICKER VIA LE BACKEND
#             # -------------------------------------------------------------
#             if not df_trans.empty and "Code ISIN" in df_trans.columns:
#                 isin_series = df_trans["Code ISIN"].dropna()
#                 if not isin_series.empty:
#                     isin_val = isin_series.iloc[0]
#                     r_isin = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/isin-vers-ticker/{isin_val}")
#                     if r_isin.status_code == 200:
#                         ticker_symbol = r_isin.json().get("ticker")

#             # -------------------------------------------------------------
#             # 2. RÉCUPÉRATION DU COURS HISTORIQUE (YFINANCE)
#             # -------------------------------------------------------------
#             if ticker_symbol and yf is not None and not df_trans.empty:
#                 dates = pd.to_datetime(df_trans["Date opération"])
#                 min_d = dates.min() - pd.Timedelta(days=30)
#                 max_d = dates.max() + pd.Timedelta(days=30)
                
#                 data = yf.download(ticker_symbol, start=min_d, end=max_d, progress=False)
#                 if not data.empty:
#                     if isinstance(data.columns, pd.MultiIndex):
#                         close_series = data["Close"][ticker_symbol] if ticker_symbol in data["Close"] else data["Close"].iloc[:, 0]
#                     else:
#                         close_series = data["Close"]
                    
#                     df_h = pd.DataFrame({
#                         "Date_clean": pd.to_datetime(close_series.index),
#                         "Prix_clean": close_series.values
#                     }).dropna()

#             # -------------------------------------------------------------
#             # 3. CONSTRUCTIONS DU GRAPHIQUE MATPLOTLIB (STYLE DARK)
#             # -------------------------------------------------------------
#             COLOR_BG = "#131722"
#             COLOR_PANEL = "#1e222d"
#             COLOR_GRID = "#2a2e39"
#             COLOR_BULL = "#089981"
#             COLOR_BEAR = "#f23645"
#             COLOR_OPEN = "#ff9800"
#             COLOR_LINE = "#2962ff"
#             COLOR_TEXT = "#d1d4dc"

#             fig, ax = plt.subplots(figsize=(12, 6), dpi=120)
#             fig.patch.set_facecolor(COLOR_BG)
#             ax.set_facecolor(COLOR_BG)

#             # Ligne du cours historique
#             if df_h is not None and not df_h.empty:
#                 ax.plot(
#                     df_h["Date_clean"], df_h["Prix_clean"],
#                     color=COLOR_LINE, linewidth=1.5, alpha=0.85,
#                     label=f"Cours ({titre})", zorder=1
#                 )
#                 ax.fill_between(
#                     df_h["Date_clean"], df_h["Prix_clean"], df_h["Prix_clean"].min() * 0.98,
#                     color=COLOR_LINE, alpha=0.08, zorder=1
#                 )

#             # Traitillés des positions clôturées (paires)
#             if not paires.empty:
#                 for _, p in paires.iterrows():
#                     d_achat, d_vente = pd.to_datetime(p["Date achat"]), pd.to_datetime(p["Date vente"])
#                     p_achat, p_vente = p["Prix achat"], p["Prix vente"]
#                     c_pnl = COLOR_BULL if p["Gain (€)"] >= 0 else COLOR_BEAR

#                     ax.plot(
#                         [d_achat, d_vente], [p_achat, p_vente],
#                         color=c_pnl, linestyle=":", linewidth=1.5, alpha=0.75, zorder=2
#                     )

#             # Marqueurs Achats / Ventes
#             if not achats.empty:
#                 ax.scatter(
#                     pd.to_datetime(achats["Date opération"]), achats["Cours"],
#                     color=COLOR_BULL, marker="^", s=130, label="Buy",
#                     zorder=5, edgecolor=COLOR_BG, linewidth=1
#                 )
#             if not ventes.empty:
#                 ax.scatter(
#                     pd.to_datetime(ventes["Date opération"]), ventes["Cours"],
#                     color=COLOR_BEAR, marker="v", s=130, label="Sell",
#                     zorder=5, edgecolor=COLOR_BG, linewidth=1
#                 )

#             # Marqueurs Positions ouvertes
#             if not ouvertes.empty:
#                 ax.scatter(
#                     pd.to_datetime(ouvertes["Date achat"]), ouvertes["Prix achat"],
#                     color=COLOR_OPEN, marker="D", s=100, label="Open Position",
#                     zorder=5, edgecolor=COLOR_BG, linewidth=1
#                 )

#             # Formatage des axes et titres
#             ax.set_title(f" {titre}  —  Transaction History", fontsize=12, fontweight="bold", color=COLOR_TEXT, pad=15, loc="left")
#             ax.set_ylabel("Price (€)", fontsize=9, color="#787b86", labelpad=8)
#             ax.tick_params(colors="#787b86", labelsize=9)
#             ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f €"))
#             ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

#             for spine in ax.spines.values():
#                 spine.set_visible(False)
#             ax.grid(True, linestyle="-", linewidth=0.5, color=COLOR_GRID, alpha=0.7)

#             leg = ax.legend(frameon=True, facecolor=COLOR_PANEL, edgecolor=COLOR_GRID, loc="upper left", fontsize=8)
#             for text in leg.get_texts():
#                 text.set_color(COLOR_TEXT)

#             fig.autofmt_xdate()
#             plt.tight_layout()

#             # Affichage dans Streamlit
#             st.pyplot(fig)

#             if not paires.empty:
#                 st.subheader(f"Trades clôturés sur {titre}")
#                 st.dataframe(paires, use_container_width=True, hide_index=True)
#         else:
#             st.info("Pas de données pour ce titre.")

import plotly.graph_objects as go
import pandas as pd
import requests
import streamlit as st

try:
    import yfinance as yf
except ImportError:
    yf = None

with tab_titre:
    titres = requests.get(
        f"{BACKEND_URL}/api/sessions/{session_id}/titres"
    ).json()
    if not titres:
        st.info("Aucun titre à afficher.")
    else:
        titre = st.selectbox("Choisis un titre", titres)
        r = requests.get(
            f"{BACKEND_URL}/api/sessions/{session_id}/graphique/{titre}"
        )

        if r.status_code == 200:
            d = r.json()
            achats = pd.DataFrame(d["achats"])
            ventes = pd.DataFrame(d["ventes"])
            paires = pd.DataFrame(d["paires"])
            ouvertes = pd.DataFrame(d["positions_ouvertes"])

            # Unification des transactions pour extraire les dates et l'ISIN
            df_trans = pd.concat([achats, ventes], ignore_index=True)

            df_h = None
            ticker_symbol = None

            # -------------------------------------------------------------
            # 1. RÉSOLUTION DU TICKER VIA LE BACKEND
            # -------------------------------------------------------------
            if not df_trans.empty and "Code ISIN" in df_trans.columns:
                isin_series = df_trans["Code ISIN"].dropna()
                if not isin_series.empty:
                    isin_val = isin_series.iloc[0]
                    r_isin = requests.get(
                        f"{BACKEND_URL}/api/sessions/{session_id}/isin-vers-ticker/{isin_val}"
                    )
                    if r_isin.status_code == 200:
                        ticker_symbol = r_isin.json().get("ticker")

            # -------------------------------------------------------------
            # 2. RÉCUPÉRATION DU COURS HISTORIQUE (YFINANCE)
            # -------------------------------------------------------------
            if ticker_symbol and yf is not None and not df_trans.empty:
                dates = pd.to_datetime(df_trans["Date opération"])
                min_d = dates.min() - pd.Timedelta(days=30)
                max_d = dates.max() + pd.Timedelta(days=30)

                data = yf.download(
                    ticker_symbol, start=min_d, end=max_d, progress=False
                )
                if not data.empty:
                    if isinstance(data.columns, pd.MultiIndex):
                        close_series = (
                            data["Close"][ticker_symbol]
                            if ticker_symbol in data["Close"]
                            else data["Close"].iloc[:, 0]
                        )
                    else:
                        close_series = data["Close"]

                    df_h = pd.DataFrame({
                        "Date": pd.to_datetime(close_series.index),
                        "Prix": close_series.values,
                    }).dropna()

            # -------------------------------------------------------------
            # 3. CONSTRUIRE LE GRAPHIQUE INTERACTIF PLOTLY (STYLE DARK)
            # -------------------------------------------------------------
            fig = go.Figure()

            # Ligne du cours historique avec dégradé/remplissage sous la courbe
            if df_h is not None and not df_h.empty:
                fig.add_trace(
                    go.Scatter(
                        x=df_h["Date"],
                        y=df_h["Prix"],
                        mode="lines",
                        name=f"Cours ({ticker_symbol})",
                        line=dict(color="#2962ff", width=1.5),
                        fill="tozeroy",
                        fillcolor="rgba(41, 98, 255, 0.08)",
                        hovertemplate="%{x|%d %b %Y}<br>Prix : %{y:.2f} €<extra></extra>",
                    )
                )

            # Trace des Achats (Trigones verts)
            if not achats.empty:
                fig.add_trace(
                    go.Scatter(
                        x=achats["Date opération"],
                        y=achats["Cours"],
                        mode="markers",
                        marker=dict(
                            symbol="triangle-up",
                            size=12,
                            color="#089981",
                            line=dict(color="#131722", width=1),
                        ),
                        name="Achat",
                        text=[f"{q} titres" for q in achats["Quantité"]],
                        hovertemplate="%{x}<br>Prix : %{y:.2f} €<br>Quantité : %{text}<extra>Achat</extra>",
                    )
                )

            # Trace des Ventes (Trigones rouges)
            if not ventes.empty:
                fig.add_trace(
                    go.Scatter(
                        x=ventes["Date opération"],
                        y=ventes["Cours"],
                        mode="markers",
                        marker=dict(
                            symbol="triangle-down",
                            size=12,
                            color="#f23645",
                            line=dict(color="#131722", width=1),
                        ),
                        name="Vente",
                        text=[f"{q} titres" for q in ventes["Quantité"]],
                        hovertemplate="%{x}<br>Prix : %{y:.2f} €<br>Quantité : %{text}<extra>Vente</extra>",
                    )
                )

            # Lignes pointillées raccordant les achats/ventes clôturés
            if not paires.empty:
                for _, p in paires.iterrows():
                    couleur = "#089981" if p["Gain (€)"] >= 0 else "#f23645"
                    fig.add_trace(
                        go.Scatter(
                            x=[p["Date achat"], p["Date vente"]],
                            y=[p["Prix achat"], p["Prix vente"]],
                            mode="lines",
                            line=dict(color=couleur, dash="dot", width=1.5),
                            opacity=0.75,
                            showlegend=False,
                            hoverinfo="skip",
                        )
                    )

            # Positions ouvertes (Losanges orange)
            if not ouvertes.empty:
                fig.add_trace(
                    go.Scatter(
                        x=ouvertes["Date achat"],
                        y=ouvertes["Prix achat"],
                        mode="markers",
                        marker=dict(
                            symbol="diamond",
                            size=11,
                            color="#ff9800",
                            line=dict(color="#131722", width=1),
                        ),
                        name="Position ouverte",
                        text=[
                            f"{q} titres restants"
                            for q in ouvertes["Quantité restante"]
                        ],
                        hovertemplate="%{x}<br>Prix : %{y:.2f} €<br>%{text}<extra>Ouverte</extra>",
                    )
                )

            # Mise en page Trading Dark
            fig.update_layout(
                title=dict(
                    text=f" <b>{titre}</b> — Historique des transactions",
                    font=dict(color="#d1d4dc", size=16),
                ),
                paper_bgcolor="#131722",
                plot_bgcolor="#131722",
                height=550,
                xaxis=dict(
                    title="Date",
                    gridcolor="#2a2e39",
                    zerolinecolor="#2a2e39",
                    tickfont=dict(color="#787b86"),
                    titlefont=dict(color="#787b86"),
                ),
                yaxis=dict(
                    title="Prix (€)",
                    gridcolor="#2a2e39",
                    zerolinecolor="#2a2e39",
                    tickfont=dict(color="#787b86"),
                    titlefont=dict(color="#787b86"),
                    ticksuffix=" €",
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(color="#d1d4dc"),
                    bgcolor="#1e222d",
                    bordercolor="#2a2e39",
                    borderwidth=1,
                ),
                hovermode="x unified",
            )

            st.plotly_chart(fig, use_container_width=True)

            if not paires.empty:
                st.subheader(f"Trades clôturés sur {titre}")
                st.dataframe(paires, use_container_width=True, hide_index=True)
        else:
            st.info("Pas de données pour ce titre.")

# --- Onglet trésorerie --------------------------------------------------------
with tab_treso:
    t = requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/tresorerie").json()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total versé sur le compte", f"{t['total_depots']:.2f} €", f"{t['nb_versements']} virement(s)")
    c2.metric("Total retiré du compte", f"{t['total_retraits']:.2f} €", f"{t['nb_retraits']} retrait(s)")
    c3.metric("Solde net versé", f"{t['net_versements']:.2f} €")
    c4.metric("Coupons / dividendes perçus", f"{t['total_coupons']:.2f} €", f"{t['nb_coupons']} versement(s)")

    if t["coupons_par_titre"]:
        st.subheader("Coupons perçus par titre")
        df_coupons = pd.DataFrame(
            list(t["coupons_par_titre"].items()), columns=["Titre", "Total coupons (€)"]
        ).sort_values("Total coupons (€)", ascending=False)
        st.dataframe(df_coupons, use_container_width=True, hide_index=True)

    # df_autres = pd.DataFrame(requests.get(f"{BACKEND_URL}/api/sessions/{session_id}/lignes-non-categorisees").json())
    # if not df_autres.empty:
    #     with st.expander(f"⚠️ {len(df_autres)} ligne(s) non catégorisée(s) — à vérifier manuellement"):
    #         st.caption("Ces lignes (frais, régularisations...) ne sont comptées dans aucun total ci-dessus.")
    #         st.dataframe(df_autres, use_container_width=True, hide_index=True)
