import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

try:
    import yfinance as yf
except ImportError:
    yf = None


def render_security_detail(backend_url: str, session_id: str) -> None:
    session_url = f"{backend_url}/api/sessions/{session_id}"
    tickers = requests.get(f"{session_url}/titres").json()
    if not tickers:
        st.info("Aucun titre à afficher.")
        return

    ticker = st.selectbox("Choisis un titre", tickers)
    response = requests.get(f"{session_url}/graphique/{ticker}")
    if response.status_code != 200:
        st.info("Pas de données pour ce titre.")
        return

    data = response.json()
    buys = pd.DataFrame(data["achats"])
    sells = pd.DataFrame(data["ventes"])
    pairs = pd.DataFrame(data["paires"])
    open_positions = pd.DataFrame(data["positions_ouvertes"])
    transactions = pd.concat([buys, sells], ignore_index=True)

    historical_prices = _fetch_historical_prices(
        backend_url, session_id, transactions
    )
    figure = go.Figure()

    if historical_prices is not None and not historical_prices.empty:
        figure.add_trace(
            go.Scatter(
                x=historical_prices["Date"],
                y=historical_prices["Prix"],
                mode="lines",
                name=f"Cours ({_resolve_ticker(backend_url, session_id, transactions)})",
                line=dict(color="#2962ff", width=1.5),
                fill="tozeroy",
                fillcolor="rgba(41, 98, 255, 0.08)",
                hovertemplate="%{x|%d %b %Y}<br>Prix : %{y:.2f} €<extra></extra>",
            )
        )

    if not buys.empty:
        figure.add_trace(
            go.Scatter(
                x=buys["Date opération"],
                y=buys["Cours"],
                mode="markers",
                marker=dict(
                    symbol="triangle-up",
                    size=12,
                    color="#089981",
                    line=dict(color="#131722", width=1),
                ),
                name="Achat",
                text=[f"{quantity} titres" for quantity in buys["Quantité"]],
                hovertemplate="%{x}<br>Prix : %{y:.2f} €<br>Quantité : %{text}<extra>Achat</extra>",
            )
        )

    if not sells.empty:
        figure.add_trace(
            go.Scatter(
                x=sells["Date opération"],
                y=sells["Cours"],
                mode="markers",
                marker=dict(
                    symbol="triangle-down",
                    size=12,
                    color="#f23645",
                    line=dict(color="#131722", width=1),
                ),
                name="Vente",
                text=[f"{quantity} titres" for quantity in sells["Quantité"]],
                hovertemplate="%{x}<br>Prix : %{y:.2f} €<br>Quantité : %{text}<extra>Vente</extra>",
            )
        )

    for _, pair in pairs.iterrows():
        color = "#089981" if pair["Gain (€)"] >= 0 else "#f23645"
        figure.add_trace(
            go.Scatter(
                x=[pair["Date achat"], pair["Date vente"]],
                y=[pair["Prix achat"], pair["Prix vente"]],
                mode="lines",
                line=dict(color=color, dash="dot", width=1.5),
                opacity=0.75,
                showlegend=False,
                hoverinfo="skip",
            )
        )

    if not open_positions.empty:
        figure.add_trace(
            go.Scatter(
                x=open_positions["Date achat"],
                y=open_positions["Prix achat"],
                mode="markers",
                marker=dict(
                    symbol="diamond",
                    size=11,
                    color="#ff9800",
                    line=dict(color="#131722", width=1),
                ),
                name="Position ouverte",
                text=[
                    f"{quantity} titres restants"
                    for quantity in open_positions["Quantité restante"]
                ],
                hovertemplate="%{x}<br>Prix : %{y:.2f} €<br>%{text}<extra>Ouverte</extra>",
            )
        )

    figure.update_layout(
        title=dict(
            text=f" <b>{ticker}</b> — Historique des transactions",
            font=dict(color="#d1d4dc", size=16),
        ),
        paper_bgcolor="#131722",
        plot_bgcolor="#131722",
        height=550,
        xaxis=dict(
            title=dict(text="Date", font=dict(color="#787b86")),
            gridcolor="#2a2e39",
            zerolinecolor="#2a2e39",
            tickfont=dict(color="#787b86"),
        ),
        yaxis=dict(
            title=dict(text="Prix (€)", font=dict(color="#787b86")),
            gridcolor="#2a2e39",
            zerolinecolor="#2a2e39",
            tickfont=dict(color="#787b86"),
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
    st.plotly_chart(figure, use_container_width=True)

    if not pairs.empty:
        st.subheader(f"Trades clôturés sur {ticker}")
        st.dataframe(pairs, use_container_width=True, hide_index=True)


def _resolve_ticker(backend_url: str, session_id: str, transactions: pd.DataFrame):
    if transactions.empty or "Code ISIN" not in transactions.columns:
        return None

    isins = transactions["Code ISIN"].dropna()
    if isins.empty:
        return None

    response = requests.get(
        f"{backend_url}/api/sessions/{session_id}/isin-vers-ticker/{isins.iloc[0]}"
    )
    if response.status_code != 200:
        return None
    return response.json().get("ticker")


def _fetch_historical_prices(
    backend_url: str, session_id: str, transactions: pd.DataFrame
):
    ticker = _resolve_ticker(backend_url, session_id, transactions)
    if not ticker or yf is None or transactions.empty:
        return None

    dates = pd.to_datetime(transactions["Date opération"])
    prices = yf.download(
        ticker,
        start=dates.min() - pd.Timedelta(days=30),
        end=dates.max() + pd.Timedelta(days=30),
        progress=False,
    )
    if prices.empty:
        return None

    if isinstance(prices.columns, pd.MultiIndex):
        close_prices = (
            prices["Close"][ticker]
            if ticker in prices["Close"]
            else prices["Close"].iloc[:, 0]
        )
    else:
        close_prices = prices["Close"]

    return pd.DataFrame(
        {"Date": pd.to_datetime(close_prices.index), "Prix": close_prices.values}
    ).dropna()
