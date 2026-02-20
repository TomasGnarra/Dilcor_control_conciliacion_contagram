"""
Pagina 4: Centro de Excepciones
Workbench para resolver todo lo pendiente sin abrir Excel.
"""
import streamlit as st
import pandas as pd
from src.ui.styles import load_css
from src.ui.components import (
    kpi_hero, kpi_card, section_div, page_header, format_money,
    build_column_config, render_data_table, no_data_warning,
    alert_card, download_excel, download_csv,
)

load_css()

page_header(
    "Centro de Excepciones",
    "Workbench para investigar y resolver movimientos pendientes",
    "⚠️",
)

if "resultado" not in st.session_state:
    no_data_warning()
    st.stop()

resultado = st.session_state["resultado"]
stats = st.session_state["stats"]

df_exc = resultado.get("excepciones", pd.DataFrame())
df_ctg = resultado.get("detalle_facturas", pd.DataFrame())

# Filtrar excepciones de Contagram (Cobradas pero Sin Match)
df_exc_ctg = pd.DataFrame()
if not df_ctg.empty and "Estado Conciliacion" in df_ctg.columns:
    df_exc_ctg = df_ctg[df_ctg["Estado Conciliacion"] == "Sin Match"]

# ═══════════════════════════════════════════════════════
# RESUMEN DE EXCEPCIONES
# ═══════════════════════════════════════════════════════
if df_exc.empty and df_exc_ctg.empty:
    st.markdown("""
    <div style="text-align:center; padding:3rem 2rem;">
        <div style="font-size:3rem; margin-bottom:1rem;">🎉</div>
        <h3 style="color:#0D7C3D;">Sin excepciones</h3>
        <p style="color:#888;">Todos los movimientos fueron conciliados exitosamente en ambos lados.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

monto_col = "Monto" if "Monto" in df_exc.columns else "monto" if "monto" in df_exc.columns else None
total_monto_banco = df_exc[monto_col].sum() if monto_col else 0
total_monto_ctg = df_exc_ctg["Cobrado"].sum() if not df_exc_ctg.empty and "Cobrado" in df_exc_ctg.columns else 0

# Hero KPIs
n_duda = stats.get("probable_duda_id", 0)
n_dif = stats.get("probable_dif_cambio", 0)

c1, c2, c3, c4, c5 = st.columns(5)
kpi_card("Mov. Banco", f"{len(df_exc)}", "movimientos sin match", "danger", c1)
kpi_card("Monto Banco", format_money(total_monto_banco), f"{len(df_exc)} movimientos", "danger", c2)
kpi_card("Fact. Contagram", f"{len(df_exc_ctg)}", "facturas sin match", "danger", c3)
kpi_card("Monto Contagram", format_money(total_monto_ctg), f"{len(df_exc_ctg)} facturas", "danger", c4)
kpi_card("Sugerencias", f"{n_duda + n_dif}", f"{n_duda} duda ID + {n_dif} dif. cambio", "warning", c5)


# ═══════════════════════════════════════════════════════
# TABS PRINCIPALES: BANCO vs CONTAGRAM
# ═══════════════════════════════════════════════════════
st.markdown("###")

col_t, _ = st.columns([1, 3])
mostrar_todo = col_t.toggle("Mostrar todos los movimientos (incluidos conciliados)", value=False)

# Redefinir datasets para las tablas segun toggle
if mostrar_todo:
    df_exc = resultado.get("resultados", pd.DataFrame())
    df_exc_ctg = resultado.get("detalle_facturas", pd.DataFrame())

# Recalcular monto_col para el dataset activo (puede cambiar de Monto a monto)
monto_col = "Monto" if "Monto" in df_exc.columns else "monto" if "monto" in df_exc.columns else None

tab_banco, tab_ctg = st.tabs(["🏛️ Excepciones Banco", "📄 Excepciones Contagram"])

with tab_banco:
    if not df_exc.empty:
        title_banco = "Todos los movimientos Bancarios" if mostrar_todo else "Pendientes en Banco (Sobran o faltan identificar)"
        section_div(title_banco, "🏛️")

        col_search, col_monto_filter = st.columns([2, 1])
        with col_search:
            busqueda = st.text_input(
                "Buscar en Banco...",
                placeholder="Ej: PRITTY, 30-50012345-6, transferencia...",
                key="exc_search",
            )
        with col_monto_filter:
            if monto_col:
                monto_min = float(df_exc[monto_col].min())
                monto_max = float(df_exc[monto_col].max())
                if monto_min < monto_max:
                    rango_monto = st.slider(
                        "Rango de monto",
                        min_value=monto_min,
                        max_value=monto_max,
                        value=(monto_min, monto_max),
                        key="exc_monto_range",
                    )
                else:
                    rango_monto = (monto_min, monto_max)
            else:
                rango_monto = None

        df_view = df_exc.copy()

        # Aplicar busqueda
        if busqueda.strip():
            term = busqueda.strip().lower()
            mask = pd.Series(False, index=df_view.index)
            for col in df_view.columns:
                if df_view[col].dtype == object:
                    mask = mask | df_view[col].fillna("").str.lower().str.contains(term, na=False)
            df_view = df_view[mask]

        # Aplicar filtro de monto
        if rango_monto and monto_col:
            df_view = df_view[
                (df_view[monto_col] >= rango_monto[0]) &
                (df_view[monto_col] <= rango_monto[1])
            ]

        # Tabs internas por categoria
        nivel_col = None
        for c_name in ["Nivel Match", "Clasificacion", "clasificacion", "match_nivel", "conciliation_tag", "Tipo"]:
            if c_name in df_view.columns:
                nivel_col = c_name
                break

        if nivel_col:
            categorias = sorted([str(c) for c in df_view[nivel_col].dropna().unique()])
            tab_cats = st.tabs(["📋 Todas"] + [f"🏷️ {c}" for c in categorias])

            with tab_cats[0]:
                render_data_table(df_view, key="exc_all")

            for i, cat in enumerate(categorias):
                with tab_cats[i + 1]:
                    df_cat = df_view[df_view[nivel_col].astype(str) == cat]
                    if monto_col:
                        st.caption(f"Monto total: {format_money(df_cat[monto_col].sum())}")
                    render_data_table(df_cat, key=f"exc_{i}")
        else:
            render_data_table(df_view, key="exc_all_flat")

        # Descarga
        st.markdown("###")
        c1, c2 = st.columns(2)
        with c1:
            download_excel(df_view, "excepciones_banco.xlsx", "Excepciones", "📥 Descargar Excel Banco")
        with c2:
            download_csv(df_view, "excepciones_banco.csv", "📥 Descargar CSV Banco")

    else:
        st.success("✅ No hay excepciones bancarias pendientes.")


with tab_ctg:
    if not df_exc_ctg.empty:
        title_ctg = "Todas las facturas de Contagram" if mostrar_todo else "Pendientes en Contagram (No aparecen en Banco)"
        section_div(title_ctg, "📄")
        
        col_s_ctg, col_m_ctg = st.columns([2, 1])
        with col_s_ctg:
            search_ctg = st.text_input("Buscar en Contagram...", placeholder="Cliente, CUIT...", key="search_ctg")
        
        df_view_ctg = df_exc_ctg.copy()
        
        if search_ctg.strip():
            term = search_ctg.strip().lower()
            mask = pd.Series(False, index=df_view_ctg.index)
            for col in df_view_ctg.columns:
                if df_view_ctg[col].dtype == object:
                    mask = mask | df_view_ctg[col].fillna("").str.lower().str.contains(term, na=False)
            df_view_ctg = df_view_ctg[mask]
            
        render_data_table(df_view_ctg, key="exc_ctg_table")
        
        alert_card(
            "Posibles causas",
            "1. El cliente pagó por otro medio no bancario (Echeq, efectivo) y figura 'Transferencia' por error.\n"
            "2. La fecha de cobro en Contagram está muy alejada de la fecha real del banco.\n"
            "3. El monto cobrado difiere significativamente del real.",
            "info"
        )
        
        st.markdown("###")
        c1, c2 = st.columns(2)
        with c1:
            download_excel(df_view_ctg, "excepciones_contagram.xlsx", "Excepciones", "📥 Excel Contagram")
        with c2:
            download_csv(df_view_ctg, "excepciones_contagram.csv", "📥 CSV Contagram")
            
    else:
        st.success("✅ No hay facturas pendientes en Contagram.")

from src.chatbot import render_chatbot_flotante
render_chatbot_flotante()