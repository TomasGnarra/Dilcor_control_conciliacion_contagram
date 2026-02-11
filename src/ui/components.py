"""
Componentes UI reutilizables.
"""
import streamlit as st
import pandas as pd

def format_money(val):
    """Formatea valores monetarios."""
    if pd.isna(val) or val == 0:
        return "$0"
    sign = "-" if val < 0 else ""
    return f"{sign}${abs(val):,.0f}".replace(",", ".")

def kpi_card(label, value, sub_value=None, status="neutral", col=None):
    """
    Renderiza una tarjeta KPI estilizada.
    
    Args:
        label (str): Titulo del KPI
        value (str/float): Valor principal
        sub_value (str): Texto secundario o descripcion
        status (str): "success" (verde), "warning" (naranja), "danger" (rojo), "neutral" (negro)
        col (st.columns): Columna de Streamlit donde renderizar (opcional)
    """
    
    border_class = {
        "success": "border-top-green",
        "warning": "border-top-orange",
        "danger": "border-top-red",
        "neutral": "border-top-black"
    }.get(status, "border-top-black")
    
    delta_html = ""
    if sub_value:
        # Estilo simple para el delta/subtitulo
        delta_html = f'<div class="metric-delta">{sub_value}</div>'

    html = f"""
    <div class="metric-container {border_class}">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {delta_html}
    </div>
    """
    
    if col:
        col.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)

def section_div(title, icon=""):
    """Separador de secciones con estilo."""
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; margin: 2rem 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #EEE;">
        <span style="font-size:1.5rem;">{icon}</span>
        <h3 style="margin:0; font-weight:700; color:#1A1A1A;">{title}</h3>
    </div>
    """, unsafe_allow_html=True)


def build_column_config(df):
    """
    Genera un dict de st.column_config basado en los nombres de columnas del DataFrame.
    Detecta automaticamente columnas monetarias, de confianza, fechas, categorias y conteos.
    """
    config = {}
    if df is None or df.empty:
        return config

    # Patrones de columnas monetarias (case-insensitive)
    _money_patterns = [
        "monto", "cobrado", "pagado", "importe", "saldo",
        "diferencia", "debe", "haber",
    ]
    # Columnas de confianza / progreso (0-100)
    _confidence_cols = {
        "Confianza %", "Confianza", "confianza", "conciliation_confidence",
    }
    # Columnas categoricas
    _category_cols = {
        "Status", "Nivel Match", "Tipo Match", "Clasificacion",
        "clasificacion", "Tag", "conciliation_status", "conciliation_tag",
        "match_nivel", "tipo", "Tipo", "Accion Sugerida",
        "tipo_match_monto", "tipo_match_id",
        "Cliente/Nombre Extraido", "Cliente Contagram",
        "Nombre Banco Extraido",
    }
    # Columnas de conteo
    _count_cols = {
        "Cant Facturas", "facturas_count",
    }
    # Columnas de fecha (ya vienen como string dd/mm/yyyy)
    _date_cols = {
        "Fecha", "fecha", "fecha_vto",
    }

    for col in df.columns:
        col_lower = col.lower().strip()

        # Confianza → ProgressColumn (escala 0–100)
        if col in _confidence_cols:
            config[col] = st.column_config.ProgressColumn(
                col,
                help="Score de confianza del matching",
                format="%d%%",
                min_value=0,
                max_value=100,
            )
        # Monetarios → NumberColumn con formato $
        elif any(p in col_lower for p in _money_patterns):
            config[col] = st.column_config.NumberColumn(
                col,
                format="$ %.2f",
            )
        # Conteos → NumberColumn entero
        elif col in _count_cols:
            config[col] = st.column_config.NumberColumn(
                col,
                format="%d",
            )
        # Categorias → TextColumn
        elif col in _category_cols:
            config[col] = st.column_config.TextColumn(
                col,
            )
        # Fechas (string) → TextColumn con label explicito
        elif col in _date_cols:
            config[col] = st.column_config.TextColumn(
                col,
            )

    return config
