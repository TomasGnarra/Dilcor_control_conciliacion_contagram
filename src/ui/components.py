"""
Componentes UI reutilizables — Dilcor v4.0
Incluye: KPI cards, hero cards, charts Plotly, status badges, stepper, filtros.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go


# ═══════════════════════════════════════════════════════
# FORMATO
# ═══════════════════════════════════════════════════════

def format_money(val):
    """Formatea valores monetarios."""
    if pd.isna(val) or val == 0:
        return "$0"
    sign = "-" if val < 0 else ""
    return f"{sign}${abs(val):,.0f}".replace(",", ".")


def format_pct(val):
    """Formatea porcentaje."""
    if pd.isna(val):
        return "0%"
    return f"{val:.1f}%"


# ═══════════════════════════════════════════════════════
# KPI CARDS
# ═══════════════════════════════════════════════════════

def kpi_card(label, value, sub_value=None, status="neutral", col=None):
    """
    Renderiza una tarjeta KPI estilizada.
    """
    border_class = {
        "success": "border-top-green",
        "warning": "border-top-orange",
        "danger": "border-top-red",
        "neutral": "border-top-black"
    }.get(status, "border-top-black")

    delta_html = ""
    if sub_value:
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


def kpi_hero(icon, value, label, sub_value=None, status="neutral", col=None):
    """
    Tarjeta KPI hero (grande, con icono prominente).
    Para la landing page del dashboard.
    """
    colors = {
        "success": "#0D7C3D",
        "warning": "#D4760A",
        "danger": "#E30613",
        "neutral": "#1A1A1A",
    }
    accent = colors.get(status, "#1A1A1A")

    delta_html = ""
    if sub_value:
        delta_html = f'<div style="font-size:0.8rem; color:#888; margin-top:0.3rem;">{sub_value}</div>'

    html = f"""
    <div class="kpi-hero" style="border-left: 5px solid {accent};">
        <div class="kpi-hero-icon">{icon}</div>
        <div class="kpi-hero-body">
            <div class="kpi-hero-value">{value}</div>
            <div class="kpi-hero-label">{label}</div>
            {delta_html}
        </div>
    </div>
    """
    if col:
        col.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# STATUS & BADGES
# ═══════════════════════════════════════════════════════

def status_semaphore(pct_conciliado, excepciones_count):
    """
    Barra de estado tipo semaforo al tope de la pagina.
    Verde: >90% y pocas excepciones. Amarillo: 70-90%. Rojo: <70%.
    """
    if pct_conciliado >= 90 and excepciones_count < 10:
        color = "#0D7C3D"
        bg = "rgba(13, 124, 61, 0.08)"
        icon = "✅"
        msg = "Conciliación en excelente estado"
    elif pct_conciliado >= 70:
        color = "#D4760A"
        bg = "rgba(212, 118, 10, 0.08)"
        icon = "⚠️"
        msg = f"Hay {excepciones_count} excepciones pendientes de revisión"
    else:
        color = "#E30613"
        bg = "rgba(227, 6, 19, 0.08)"
        icon = "🔴"
        msg = f"Atención: solo {pct_conciliado:.0f}% conciliado — {excepciones_count} excepciones"

    st.markdown(f"""
    <div style="
        background: {bg};
        border: 1px solid {color};
        border-radius: 10px;
        padding: 0.8rem 1.2rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin-bottom: 1.5rem;
    ">
        <span style="font-size:1.3rem;">{icon}</span>
        <div>
            <span style="font-weight:700; color:{color}; font-size:0.95rem;">{msg}</span>
            <span style="color:#888; font-size:0.8rem; margin-left:1rem;">
                {format_pct(pct_conciliado)} conciliado
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def status_badge(text, status="neutral"):
    """Badge inline coloreado."""
    colors = {
        "success": ("#0D7C3D", "rgba(13,124,61,0.1)"),
        "warning": ("#D4760A", "rgba(212,118,10,0.1)"),
        "danger": ("#E30613", "rgba(227,6,19,0.1)"),
        "neutral": ("#666", "rgba(0,0,0,0.05)"),
    }
    fg, bg = colors.get(status, colors["neutral"])
    return f'<span style="background:{bg}; color:{fg}; padding:2px 10px; border-radius:12px; font-size:0.75rem; font-weight:700;">{text}</span>'


def alert_card(title, message, severity="warning"):
    """Card de alerta con icono."""
    icons = {"warning": "⚠️", "danger": "🚨", "info": "ℹ️", "success": "✅"}
    colors = {
        "warning": ("#D4760A", "rgba(212,118,10,0.06)"),
        "danger": ("#E30613", "rgba(227,6,19,0.06)"),
        "info": ("#1565C0", "rgba(21,101,192,0.06)"),
        "success": ("#0D7C3D", "rgba(13,124,61,0.06)"),
    }
    icon = icons.get(severity, "ℹ️")
    fg, bg = colors.get(severity, colors["info"])

    st.markdown(f"""
    <div style="background:{bg}; border-left:4px solid {fg}; border-radius:8px; padding:1rem 1.2rem; margin:0.5rem 0;">
        <div style="font-weight:700; color:{fg}; margin-bottom:0.3rem;">{icon} {title}</div>
        <div style="font-size:0.85rem; color:#555;">{message}</div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# SECTION DIVIDERS
# ═══════════════════════════════════════════════════════

def section_div(title, icon=""):
    """Separador de secciones con estilo."""
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:10px; margin: 2rem 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #EEE;">
        <span style="font-size:1.5rem;">{icon}</span>
        <h3 style="margin:0; font-weight:700; color:#1A1A1A;">{title}</h3>
    </div>
    """, unsafe_allow_html=True)


def page_header(title, subtitle="", icon=""):
    """Header de pagina con icono y descripcion."""
    sub_html = f'<div style="font-size:0.85rem; color:#888; margin-top:0.2rem;">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div style="margin-bottom:1.5rem; padding-bottom:1rem; border-bottom:2px solid #EEE;">
        <div style="display:flex; align-items:center; gap:0.7rem;">
            <span style="font-size:1.8rem;">{icon}</span>
            <div>
                <h2 style="margin:0; font-weight:800; color:#1A1A1A;">{title}</h2>
                {sub_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# CHARTS (Plotly wrappers)
# ═══════════════════════════════════════════════════════

BRAND_COLORS = ["#0D7C3D", "#D4760A", "#E30613", "#1A1A1A", "#666"]


def donut_chart(labels, values, title="", colors=None, height=320):
    """
    Grafico dona Plotly para distribucion de conciliacion.
    """
    if colors is None:
        colors = BRAND_COLORS[:len(labels)]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#FFF", width=2)),
        textinfo="label+percent",
        textfont=dict(size=12, family="Inter"),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percent}<extra></extra>",
    )])
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, family="Inter", color="#1A1A1A")),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=11)),
        margin=dict(l=20, r=20, t=40, b=20),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def horizontal_bar_chart(labels, values, title="", color="#E30613", height=300):
    """
    Grafico de barras horizontales para montos por banco/medio.
    """
    fig = go.Figure(data=[go.Bar(
        y=labels,
        x=values,
        orientation="h",
        marker=dict(color=color, line=dict(color=color, width=1)),
        texttemplate="$%{x:,.0f}",
        textposition="outside",
        textfont=dict(size=11, family="Inter"),
        hovertemplate="<b>%{y}</b><br>$%{x:,.0f}<extra></extra>",
    )])
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, family="Inter", color="#1A1A1A")),
        xaxis=dict(showgrid=True, gridcolor="#F0F0F0", showticklabels=False),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=80, t=40, b=20),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)


def stacked_bar_chart(categories, series_dict, title="", height=350):
    """
    Barras apiladas para comparar conciliado vs pendiente por banco.
    series_dict: {"Conciliado": [v1, v2], "Pendiente": [v1, v2]}
    """
    colors_map = {
        "Conciliado": "#0D7C3D",
        "Match Exacto": "#0D7C3D",
        "Probable": "#D4760A",
        "Sin Match": "#E30613",
        "Gastos": "#666",
    }
    fig = go.Figure()
    for name, values in series_dict.items():
        fig.add_trace(go.Bar(
            name=name,
            x=categories,
            y=values,
            marker_color=colors_map.get(name, "#1A1A1A"),
            texttemplate="$%{y:,.0f}",
            textposition="inside",
            textfont=dict(size=10, family="Inter", color="white"),
        ))
    fig.update_layout(
        barmode="stack",
        title=dict(text=title, font=dict(size=14, family="Inter", color="#1A1A1A")),
        yaxis=dict(showgrid=True, gridcolor="#F0F0F0"),
        margin=dict(l=10, r=10, t=40, b=20),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════
# STEPPER (para pagina de exportar)
# ═══════════════════════════════════════════════════════

def stepper(steps, current_step=0):
    """
    Componente stepper visual con pasos numerados.
    steps: list of dicts {"title": str, "desc": str, "done": bool}
    """
    items_html = ""
    for i, step in enumerate(steps):
        if step.get("done"):
            circle_style = "background:#0D7C3D; color:white;"
            text_color = "#0D7C3D"
            icon = "✓"
        elif i == current_step:
            circle_style = "background:#E30613; color:white;"
            text_color = "#1A1A1A"
            icon = str(i + 1)
        else:
            circle_style = "background:#E0E0E0; color:#999;"
            text_color = "#999"
            icon = str(i + 1)

        # HTML sin indentacion para evitar que st.markdown lo tome como codigo
        items_html += f"""
<div style="display:flex; align-items:flex-start; gap:0.8rem; margin-bottom:1rem;">
    <div style="min-width:32px; height:32px; border-radius:50%; {circle_style}
                display:flex; align-items:center; justify-content:center;
                font-weight:700; font-size:0.85rem;">{icon}</div>
    <div>
        <div style="font-weight:700; color:{text_color}; font-size:0.9rem;">{step['title']}</div>
        <div style="font-size:0.8rem; color:#888;">{step.get('desc', '')}</div>
    </div>
</div>
"""

    st.markdown(f"""
<div style="background:white; border:1px solid #E0E0E0; border-radius:12px; padding:1.5rem; margin:1rem 0;">
    {items_html}
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════
# DATAFRAME HELPERS
# ═══════════════════════════════════════════════════════

def build_column_config(df):
    """
    Genera un dict de st.column_config basado en los nombres de columnas del DataFrame.
    Detecta automaticamente columnas monetarias, de confianza, fechas, categorias y conteos.
    """
    config = {}
    if df is None or df.empty:
        return config

    _money_patterns = [
        "monto", "cobrado", "pagado", "importe", "saldo",
        "diferencia", "debe", "haber",
    ]
    _confidence_cols = {
        "Confianza %", "Confianza", "confianza", "conciliation_confidence",
    }
    _category_cols = {
        "Status", "Nivel Match", "Tipo Match", "Clasificacion",
        "clasificacion", "Tag", "conciliation_status", "conciliation_tag",
        "match_nivel", "tipo", "Tipo", "Accion Sugerida",
        "tipo_match_monto", "tipo_match_id",
        "Cliente/Nombre Extraido", "Cliente Contagram",
        "Nombre Banco Extraido",
    }
    _count_cols = {
        "Cant Facturas", "facturas_count",
    }
    _date_cols = {
        "Fecha", "fecha", "fecha_vto",
    }

    for col in df.columns:
        col_lower = col.lower().strip()

        if col in _confidence_cols:
            config[col] = st.column_config.ProgressColumn(
                col,
                help="Score de confianza del matching",
                format="%d%%",
                min_value=0,
                max_value=100,
            )
        elif any(p in col_lower for p in _money_patterns):
            config[col] = st.column_config.NumberColumn(
                col,
                format="$ %.2f",
            )
        elif col in _count_cols:
            config[col] = st.column_config.NumberColumn(
                col,
                format="%d",
            )
        elif col in _category_cols:
            config[col] = st.column_config.TextColumn(col)
        elif col in _date_cols:
            config[col] = st.column_config.TextColumn(col)

    return config


def render_data_table(df, key=None):
    """Renderiza dataframe con column_config automatico."""
    if df is None or df.empty:
        st.info("Sin datos para mostrar.")
        return
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config=build_column_config(df),
        key=key,
    )


def download_csv(df, filename, label="📥 Descargar CSV"):
    """Boton de descarga CSV con encoding utf-8-sig."""
    st.download_button(
        label,
        df.to_csv(index=False).encode("utf-8-sig"),
        filename, "text/csv",
        use_container_width=True,
        type="primary",
    )


def download_excel(df, filename, sheet_name="Datos", label="📥 Descargar Excel"):
    """Boton de descarga Excel con formato Dilcor."""
    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        wb = writer.book
        ws = writer.sheets[sheet_name]
        hfmt = wb.add_format({"bold": True, "bg_color": "#E30613", "font_color": "white", "border": 1})
        for i, col in enumerate(df.columns):
            ws.write(0, i, col, hfmt)
            ws.set_column(i, i, max(15, len(str(col)) + 5))

    st.download_button(
        label, buffer.getvalue(),
        filename,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
    )


def no_data_warning():
    """Mensaje cuando no hay datos de conciliacion cargados."""
    st.markdown("""
    <div style="text-align:center; padding:3rem 2rem; color:#888;">
        <div style="font-size:3rem; margin-bottom:1rem;">📊</div>
        <h3 style="color:#1A1A1A; margin-bottom:0.5rem;">Sin datos de conciliación</h3>
        <p>Ejecutá la conciliación desde la página principal para ver los resultados aquí.</p>
    </div>
    """, unsafe_allow_html=True)
