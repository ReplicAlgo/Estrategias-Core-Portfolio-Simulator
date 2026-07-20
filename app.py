import streamlit as st
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go
 
# --- Load Excel for historical data ---
@st.cache_data
def load_data():
    # header=3 lee la fila 4 de Excel como encabezados
    # SE HA MODIFICADO usecols="B:Q" PARA INCLUIR HASTA LA COLUMNA Q
    df = pd.read_excel(
       "DatosResultadosEstrategiasLTTotalAPP.xlsx", 
       engine='openpyxl', 
       header=3,
       usecols="B:Q"
    )
    
    # 1. Asegurar que todos los nombres de columnas sean texto string y limpiar espacios
    df.columns = df.columns.astype(str).str.strip()
    
    # 2. Eliminar cualquier columna residual sin nombre o vacía
    df = df.loc[:, ~df.columns.str.contains('^Unnamed|^Unnamed:')]
    
    # 3. Buscar dinámicamente la columna de fecha
    posibles_nombres_fecha = ['Date', 'Fecha', 'date', 'fecha']
    columna_fecha = None
    for col in posibles_nombres_fecha:
        if col in df.columns:
            columna_fecha = col
            break
            
    if columna_fecha is None:
        columna_fecha = df.columns[0]
    
    # 4. Procesar la columna de tiempo y eliminar filas vacías al final del archivo
    df['time'] = pd.to_datetime(df[columna_fecha], errors='coerce')
    df = df.dropna(subset=['time'])
    df['year'] = df['time'].dt.year
    
    # 5. Filtrar estrictamente: Benchmarks vs Estrategias reales
    benchmarks = ['BuyHold SPY', 'BuyHold 60/40']
    
    all_numeric_cols = []
    strategies = []
    
    for col in df.columns:
        # Ignorar columnas de control de fecha/tiempo
        if col in [columna_fecha, 'time', 'year']:
            continue
            
        # Validar si el nombre de la columna parece un número o porcentaje huérfano
        try:
           float(col.replace('%', ''))
           continue
        except ValueError:
           all_numeric_cols.append(col)
           if col not in benchmarks:
               strategies.append(col)
    
    # 6. Limpieza y conversión forzada a numérico de los datos históricos
    for col in all_numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').ffill().fillna(100000)
        
    return df, strategies
    
# --- Load Summary Table ---
@st.cache_data
def load_summary_table():
    path = "SummaryTable.csv"
    try:
        summary_df = pd.read_csv(path)
        summary_df = summary_df.loc[:, ~summary_df.columns.str.contains('^Unnamed')]
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
       column_config={
           "Estrategia": st.column_config.TextColumn("Estrategia", help="Nombre del sistema cuantitativo"),
           "Fecha": st.column_config.TextColumn("Periodo", help="Rango de fechas evaluado"),
           "Ganancia": st.column_config.TextColumn("Ganancia Total"), 
           "CAGR": st.column_config.TextColumn("CAGR", help="Tasa de Crecimiento Anual Compuesto"),
           "Max Caída": st.column_config.TextColumn("Max Caída", help="Peor Drawdown histórico de la estrategia"),
           "Volatilidad": st.column_config.TextColumn("Volatilidad"),
           "# Trades": st.column_config.NumberColumn("# Trades", format="%d"),
           "% Ganadoras": st.column_config.TextColumn("% Ganado"),
           "Gan. Promedio": st.column_config.TextColumn("Gan. Prom"),
           "Perdida Promedio": st.column_config.TextColumn("Perdida Pr"),
           "Profit Fact": st.column_config.NumberColumn("Profit Fact", format="%.1f"),
          "Sharpe": st.column_config.ProgressColumn(
               "Sharpe Ratio",
               help="Relación Retorno / Riesgo",
               format="%.1f",
               min_value=0.0,
               max_value=2.0
           ),
           "Perfil Riesgo": st.column_config.TextColumn("Perfil Riesgo")
       }
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
            <li>Si elegimos <strong>Rotacion Defensiva D4</strong>, podemos tener asignaciones que lleguen hasta 110-120% sin que el apalancamiento sea real. Esto porque la estrategia de Rotación Defensiva entra cuando muchas de las otras no están activas y están en efectivo.</li>
        </ul>
    </div>
    """, 
    unsafe_allow_html=True
)
 
st.markdown("<h3 style='text-align: center; margin-top:10px;'>Simulador de Construcción de Portafolio</h3>", unsafe_allow_html=True)
 
# --- Sidebar: Portfolio Settings ---
st.sidebar.header("Portfolio Settings")
 
show_benchmarks = st.sidebar.checkbox("Show Benchmarks (SPY & 60/40)", value=True, help="Toggle to show/hide standard comparison benchmarks on the charts and summary metric blocks.")
 
st.sidebar.subheader("Strategy Allocations (%)")
 
default_allocations = [0, 0, 20, 0, 0, 20, 0, 30, 20, 0, 20]
allocations = {}
 
for idx, strat in enumerate(strategies):
    default_val = default_allocations[idx] if idx < len(default_allocations) else 0
            
    allocations[strat] = st.sidebar.slider(f"{strat}", 0, 200, default_val, step=5,
                                           help="0 = off, 100 = full size, >100 = leverage")
 
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
 
# --- Pre-calculate Benchmarks Baseline For KPIs ---
spy_return, spy_max_dd = 0.0, 0.0
if "BuyHold SPY" in historical_df.columns:
    spy_eq = historical_df["BuyHold SPY"].values
    spy_return = spy_eq[-1] - 100000
    spy_cm = np.maximum.accumulate(spy_eq)
    spy_max_dd = (((spy_eq - spy_cm) / spy_cm) * 100).min()
 
yf_return, yf_max_dd = 0.0, 0.0
if "BuyHold 60/40" in historical_df.columns:
    yf_eq = historical_df["BuyHold 60/40"].values
    yf_return = yf_eq[-1] - 100000
    yf_cm = np.maximum.accumulate(yf_eq)
    yf_max_dd = (((yf_eq - yf_cm) / yf_cm) * 100).min()
 
historical_df['portfolio_val'] = final_portfolio_equity
yearly_data = []
for year, group in historical_df.groupby('year'):
    p_start = group['portfolio_val'].iloc[0]
    p_end = group['portfolio_val'].iloc[-1]
    p_return = ((p_end / p_start) - 1) * 100
    
    row_dict = {"Year": int(year), "Return": p_return}
    
    if "BuyHold SPY" in historical_df.columns:
        spy_start = group["BuyHold SPY"].iloc[0]
        spy_end = group["BuyHold SPY"].iloc[-1]
        row_dict["BuyHold SPY"] = ((spy_end / spy_start) - 1) * 100
        
    if "BuyHold 60/40" in historical_df.columns:
        yf_start = group["BuyHold 60/40"].iloc[0]
        yf_end = group["BuyHold 60/40"].iloc[-1]
        row_dict["BuyHold 60/40"] = ((yf_end / yf_start) - 1) * 100
        
    yearly_data.append(row_dict)
 
yearly_df = pd.DataFrame(yearly_data)
 
# --- Metric Display Cards ---
col1, col2 = st.columns(2)
 
spy_ret_str = f"<div style='font-size:13px; color:#888; margin-top:4px;'>SPY: ${spy_return:,.0f}</div>" if show_benchmarks and "BuyHold SPY" in historical_df.columns else ""
yf_ret_str = f"<div style='font-size:13px; color:#888;'>60/40: ${yf_return:,.0f}</div>" if show_benchmarks and "BuyHold 60/40" in historical_df.columns else ""
 
spy_dd_str = f"<div style='font-size:13px; color:#888; margin-top:4px;'>SPY: {spy_max_dd:.2f}%</div>" if show_benchmarks and "BuyHold SPY" in historical_df.columns else ""
yf_dd_str = f"<div style='font-size:13px; color:#888;'>60/40: {yf_max_dd:.2f}%</div>" if show_benchmarks and "BuyHold 60/40" in historical_df.columns else ""
 
with col1:
    st.markdown(
        f"""
        <div style='border:2px solid #ccc; border-radius:8px; padding:12px; text-align:center;'>
            <h5 style='margin:0;'>Total Net Return</h5>
            <p style='font-size:18px; color:{"green" if total_return >= 0 else "red"}; margin:4px 0 0 0;'>${total_return:,.0f}</p>
           {spy_ret_str}
           {yf_ret_str}
        </div>
        """, unsafe_allow_html=True
    )
with col2:
    st.markdown(
        f"""
        <div style='border:2px solid #ccc; border-radius:8px; padding:12px; text-align:center;'>
            <h5 style='margin:0;'>Max Drawdown (%)</h5>
            <p style='font-size:18px; color:red; margin:4px 0 0 0;'>{max_drawdown_pct:.2f}%</p>
           {spy_dd_str}
           {yf_dd_str}
        </div>
        """, unsafe_allow_html=True
    )
 
# --- Plotly Charting Engine ---
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.04,
    subplot_titles=("Portfolio Equity Curve ($)", "Drawdown (%)"),
    row_heights=[0.65, 0.35]
)
 
fig.add_trace(go.Scatter(x=dates, y=final_portfolio_equity, mode="lines", name="My Portfolio", line=dict(color="#00CC96", width=2.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=dates, y=drawdown_pct, fill="tozeroy", name="Portfolio Drawdown", line=dict(color="#EF553B"), fillcolor="rgba(239, 85, 59, 0.15)"), row=2, col=1)
 
if show_benchmarks:
    if "BuyHold SPY" in historical_df.columns:
        spy_equity = historical_df["BuyHold SPY"].values
        spy_cummax = np.maximum.accumulate(spy_equity)
        spy_dd_pct = ((spy_equity - spy_cummax) / spy_cummax) * 100
        
        fig.add_trace(go.Scatter(x=dates, y=spy_equity, mode="lines", name="BuyHold SPY", line=dict(color="#FFA15A", dash="dash", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=dates, y=spy_dd_pct, mode="lines", name="BuyHold SPY", line=dict(color="#FFA15A", dash="dash", width=1.5), showlegend=False), row=2, col=1)
 
    if "BuyHold 60/40" in historical_df.columns:
        yf_equity = historical_df["BuyHold 60/40"].values
        yf_cummax = np.maximum.accumulate(yf_equity)
        yf_dd_pct = ((yf_equity - yf_cummax) / yf_cummax) * 100
        
        fig.add_trace(go.Scatter(x=dates, y=yf_equity, mode="lines", name="BuyHold 60/40", line=dict(color="#19D3F3", dash="dot", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=dates, y=yf_dd_pct, mode="lines", name="BuyHold 60/40", line=dict(color="#19D3F3", dash="dot", width=1.5), showlegend=False), row=2, col=1)
 
fig.update_layout(height=650, showlegend=True, hovermode="x unified", dragmode="zoom")
fig.update_xaxes(
    rangeselector=dict(
        buttons=list([
           dict(count=1, label="1y", step="year", stepmode="backward"),
           dict(count=5, label="5y", step="year", stepmode="backward"),
           dict(count=10, label="10y", step="year", stepmode="backward"),
           dict(step="all", label="All")
        ])
    ),
    type="date", row=1, col=1
)
 
fig.update_yaxes(ticksuffix="%", row=2, col=1)
fig.update_traces(hovertemplate="$%{y:,.0f}", row=1, col=1)
fig.update_traces(hovertemplate="%{y:.2f}%", row=2, col=1)
 
st.plotly_chart(fig, use_container_width=True)
 
# --- Yearly Returns Table ---
st.subheader("Yearly Returns")
if not yearly_df.empty:
    format_dict = {"Year": "{:d}", "Return": "{:+.2f}%"}
    style_target_cols = ['Return']
    
    if show_benchmarks:
        if "BuyHold SPY" in yearly_df.columns:
            format_dict["BuyHold SPY"] = "{:+.2f}%"
            style_target_cols.append("BuyHold SPY")
        if "BuyHold 60/40" in yearly_df.columns:
            format_dict["BuyHold 60/40"] = "{:+.2f}%"
            style_target_cols.append("BuyHold 60/40")
    else:
        columns_to_keep = ['Year', 'Return']
        yearly_df = yearly_df[columns_to_keep]
 
    def color_returns(val):
        return 'color: red' if val < 0 else 'color: green'
    
    inverted_yearly_df = yearly_df.iloc[::-1]
    
    styled_yearly_df = inverted_yearly_df.style.map(color_returns, subset=style_target_cols)\
                                             .format(format_dict)
    
    st.dataframe(
       styled_yearly_df, 
       hide_index=True, 
       use_container_width=True,
       column_config={
           "Return": st.column_config.TextColumn("Portafolio")
       }
    )
else:
    st.write("No data available.")
 
# --- Footer & Disclaimer ---
st.markdown("<br><br>", unsafe_allow_html=True)
 
st.markdown(
    """
    <div style="
       background-color: #111425; 
        border: 1px solid #ffcc00; 
        border-radius: 20px; 
        padding: 30px;
        text-align: center; 
        margin-bottom: 30px;
    ">
        <h4 style="
            color: #ffcc00; 
           text-transform: uppercase; 
           letter-spacing: 2px; 
           margin-bottom: 15px; 
            font-size: 16px; 
           font-weight: bold;
        ">
            Aviso de Riesgo
        </h4>
        <p style="
            color: #ffffff; 
            font-size: 14px; 
           line-height: 1.6; 
            margin: 0 auto; 
            max-width: 900px;
        ">
            Toda la información presente en esta web debe considerarse como una opinión y en ningún caso como un asesoramiento 
            financiero o de inversión. Las rentabilidades pasadas no garantizan resultados futuros. Tú eres el único responsable de tus 
            decisiones financieras. Consulta a tu asesor tributario y financiero antes de invertir.
        </p>
    </div>
    """,
   unsafe_allow_html=True
)
 
st.markdown(
    """
    <div style="text-align: center; color: #666e8d; font-size: 14px; margin-top: 20px;">
        <p>© 2026 ReplicAlgo &nbsp;&bull;&nbsp; 🤖 Actualizado por Master Bot</p>
    </div>
    """,
   unsafe_allow_html=True
)
