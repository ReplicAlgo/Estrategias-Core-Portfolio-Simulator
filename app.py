import streamlit as st
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# --- Load Excel for historical data ---
@st.cache_data
def load_data():
    df = pd.read_excel(
        "DatosResultadosEstrategiasLTTotalAPP.xlsx", 
        engine='openpyxl', 
        header=3,
        usecols="B:S"
    )
    df.columns = df.columns.astype(str).str.strip()
    df = df.loc[:, ~df.columns.str.contains('^Unnamed|^Unnamed:')]
    
    posibles_nombres_fecha = ['Date', 'Fecha', 'date', 'fecha']
    columna_fecha = None
    for col in posibles_nombres_fecha:
        if col in df.columns:
            columna_fecha = col
            break
            
    if columna_fecha is None:
        columna_fecha = df.columns[0]
    
    df['time'] = pd.to_datetime(df[columna_fecha], errors='coerce')
    df = df.dropna(subset=['time'])
    df['year'] = df['time'].dt.year
    
    benchmarks = ['BuyHold SPY', 'BuyHold 60/40']
    all_numeric_cols = []
    strategies = []
    
    for col in df.columns:
        if col in [columna_fecha, 'time', 'year']:
            continue
        try:
            float(col.replace('%', ''))
            continue
        except ValueError:
            all_numeric_cols.append(col)
            if col not in benchmarks:
                strategies.append(col)
    
    for col in all_numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').ffill().fillna(100000)
        
    return df, strategies
    
# --- Load Summary Table (Corregido y estricto) ---
@st.cache_data(ttl=1)
def load_summary_table():
    path = "SummaryTable.csv"
    try:
        summary_df = pd.read_csv(path)
        summary_df = summary_df.loc[:, ~summary_df.columns.str.contains('^Unnamed')]
        summary_df = summary_df.dropna(subset=['Estrategia'])
        return summary_df
    except Exception as e:
        st.error(f"Error: {e}")
        return None

historical_df, strategies = load_data()
summary_df = load_summary_table()

# --- Top Section: Summary Metrics Table ---
st.markdown("<h2 style='text-align: center; margin-bottom: 5px;'>Resultados Históricos por Estrategia</h2>", unsafe_allow_html=True)
if summary_df is not None:
    st.dataframe(summary_df, hide_index=True, use_container_width=True, height=500, column_config={
        "Estrategia": st.column_config.TextColumn("Estrategia"),
        "Fecha": st.column_config.TextColumn("Periodo"),
        "Ganancia": st.column_config.TextColumn("Ganancia"),
        "CAGR": st.column_config.TextColumn("CAGR"),
        "Max Caída": st.column_config.TextColumn("Max Caída"),
        "Volatilidad": st.column_config.TextColumn("Volatilidad"),
        "# Trades": st.column_config.NumberColumn("# Trades"),
        "% Ganador": st.column_config.TextColumn("% Ganador"),
        "Gan. Promedio": st.column_config.TextColumn("Gan. Prom"),
        "Perdida Prom": st.column_config.TextColumn("Perdida Prom"),
        "Duración Ganador": st.column_config.NumberColumn("Duración Gan"),
        "Duración Perdedor": st.column_config.NumberColumn("Duración Per"),
        "Profit Factor": st.column_config.NumberColumn("Profit Factor"),
        "Sharpe": st.column_config.NumberColumn("Sharpe"),
        "Perfil Riesgo": st.column_config.TextColumn("Perfil Riesgo"),
        "Posiciones Simultaneas": st.column_config.NumberColumn("Pos. Sim."),
        "Min Inversion (USD)": st.column_config.NumberColumn("Min Inv")
    })
    st.markdown("<hr>", unsafe_allow_html=True)

# --- Sidebar & Portfolio ---
st.sidebar.header("Portfolio Settings")
show_benchmarks = st.sidebar.checkbox("Show Benchmarks (SPY & 60/40)", value=True)
st.sidebar.subheader("Strategy Allocations (%)")
default_allocations = [0, 0, 20, 0, 0, 20, 0, 30, 20, 0, 20]
allocations = {}
for idx, strat in enumerate(strategies):
    default_val = default_allocations[idx] if idx < len(default_allocations) else 0
    allocations[strat] = st.sidebar.slider(f"{strat}", 0, 200, default_val, step=5)

# --- Calculations & Charts (Restaurados totalmente) ---
portfolio_equity = np.zeros(len(historical_df))
for strat in strategies:
    weight = allocations[strat] / 100.0
    portfolio_equity += (historical_df[strat].values - 100000) * weight
final_portfolio_equity = portfolio_equity + 100000
drawdown_pct = ((final_portfolio_equity - np.maximum.accumulate(final_portfolio_equity)) / np.maximum.accumulate(final_portfolio_equity)) * 100

# Charting
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Portfolio Equity Curve ($)", "Drawdown (%)"))
fig.add_trace(go.Scatter(x=historical_df['time'], y=final_portfolio_equity, name="My Portfolio", line=dict(color="green", width=2.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=historical_df['time'], y=drawdown_pct, fill="tozeroy", name="Portfolio Drawdown", line=dict(color="red")), row=2, col=1)

if show_benchmarks:
    for name in ['BuyHold SPY', 'BuyHold 60/40']:
        if name in historical_df.columns:
            eq = historical_df[name].values
            dd = ((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)) * 100
            fig.add_trace(go.Scatter(x=historical_df['time'], y=eq, name=name, line=dict(dash="dash")), row=1, col=1)
            fig.add_trace(go.Scatter(x=historical_df['time'], y=dd, name=name, line=dict(dash="dash"), showlegend=False), row=2, col=1)

fig.update_layout(height=650, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)
