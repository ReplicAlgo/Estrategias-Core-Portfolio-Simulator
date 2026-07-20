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
    
# --- Load Summary Table (Código corregido con limpieza forzada) ---
@st.cache_data(ttl=1)
def load_summary_table():
    path = "SummaryTable.csv"
    try:
        summary_df = pd.read_csv(path)
        # Eliminar columnas que no tengan nombre (o Unnamed)
        summary_df = summary_df.loc[:, ~summary_df.columns.str.contains('^Unnamed')]
        # Eliminar filas vacías
        summary_df = summary_df.dropna(subset=['Estrategia'])
        return summary_df
    except Exception as e:
        st.error(f"No se pudo cargar la tabla de resumen: {e}")
        return None

historical_df, strategies = load_data()
summary_df = load_summary_table()

# --- Top Section: Summary Metrics Table ---
st.markdown("<h2 style='text-align: center; margin-bottom: 5px;'>Resultados Históricos por Estrategia</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666; margin-bottom: 20px;'>Utiliza estas métricas de rendimiento histórico (2007 - 2026) para guiar tu asignación en el menú lateral.</p>", unsafe_allow_html=True)

if summary_df is not None:
    st.dataframe(
        summary_df,
        hide_index=True,
        use_container_width=True,
        height=500
    )
    st.markdown("<hr style='margin-top:30px; margin-bottom:30px; border: 0; border-top: 1px solid #eee;'>", unsafe_allow_html=True)

# --- Description text box ---
st.markdown(
    """
    <div style='border:2px solid #ccc; border-radius:8px; padding:20px; margin-bottom:20px; font-size:16px; line-height:1.6;'>
        <strong style='font-size:18px;'>Uso:</strong><br>
        Esta app está diseñada para simular portafolios combinando diferentes estrategias de inversión núcleo. 
        El objetivo principal es combinar sistemas con baja correlación para mejorar el perfil riesgo-retorno general.
        <ul>
            <li>Maximizar el retorno esperado del portafolio combinado.</li>
            <li>Minimizar el Max Drawdown (pérdida máxima de la cartera).</li>
            <li><strong>Lo ideal:</strong> aumentar el retorno y reducir el riesgo mediante diversificación sistemática.</li>
        </ul>
        <strong style='font-size:18px;'>Inputs:</strong>
        <ul>
            <li><strong>Asset Allocation:</strong> los sliders indican el porcentaje (%) asignado a cada estrategia núcleo.</li>
        </ul>
    </div>
    """, 
    unsafe_allow_html=True
)

st.markdown("<h3 style='text-align: center; margin-top:10px;'>Simulador de Construcción de Portafolio</h3>", unsafe_allow_html=True)

# --- Sidebar: Portfolio Settings ---
st.sidebar.header("Portfolio Settings")
show_benchmarks = st.sidebar.checkbox("Show Benchmarks (SPY & 60/40)", value=True)
st.sidebar.subheader("Strategy Allocations (%)")

default_allocations = [0, 0, 20, 0, 0, 20, 0, 30, 20, 0, 20]
allocations = {}

for idx, strat in enumerate(strategies):
    default_val = default_allocations[idx] if idx < len(default_allocations) else 0
    allocations[strat] = st.sidebar.slider(f"{strat}", 0, 200, default_val, step=5)

total_alloc = sum(allocations.values())
st.sidebar.markdown(f"**Total Allocation: {total_alloc}%**")

if total_alloc > 100:
    st.sidebar.warning(f"⚠️ Leverage applied: {total_alloc - 100}% over 100%")

# --- Portfolio Performance Calculations ---
portfolio_equity = np.zeros(len(historical_df))
for strat in strategies:
    weight = allocations[strat] / 100.0
    strat_fluctuations = historical_df[strat].values - 100000
    portfolio_equity += strat_fluctuations * weight

final_portfolio_equity = portfolio_equity + 100000
cummax_equity = np.maximum.accumulate(final_portfolio_equity)
drawdown_pct = ((final_portfolio_equity - cummax_equity) / cummax_equity) * 100
total_return = final_portfolio_equity[-1] - 100000
max_drawdown_pct = drawdown_pct.min()
dates = historical_df['time'].values

# --- Display KPIs ---
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"<div style='border:2px solid #ccc; border-radius:8px; padding:12px; text-align:center;'><h5>Total Net Return</h5><p style='font-size:18px;'>${total_return:,.0f}</p></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div style='border:2px solid #ccc; border-radius:8px; padding:12px; text-align:center;'><h5>Max Drawdown (%)</h5><p style='font-size:18px; color:red;'>{max_drawdown_pct:.2f}%</p></div>", unsafe_allow_html=True)

# --- Plotly Charting Engine ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.65, 0.35])
fig.add_trace(go.Scatter(x=dates, y=final_portfolio_equity, name="My Portfolio", line=dict(color="green", width=2.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=dates, y=drawdown_pct, fill="tozeroy", name="Portfolio Drawdown", line=dict(color="red")), row=2, col=1)
fig.update_layout(height=650, showlegend=True, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# --- Footer ---
st.markdown("<div style='text-align: center; color: #666; margin-top: 20px;'>© 2026 ReplicAlgo</div>", unsafe_allow_html=True)
