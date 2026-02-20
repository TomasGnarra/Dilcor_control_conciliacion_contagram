"""
Pagina 3: Resumen
Vista tecnica consolidada para el contador.

Keys usadas de session_state:
  resultado["resultados"]       → DataFrame completo
  stats["por_banco"]            → dict desglosado
  stats (global)                → KPIs generales
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.ui.styles import load_css
from src.ui.components import (
    kpi_hero, kpi_card, section_div, page_header, format_money,
    build_column_config, render_data_table, no_data_warning,
    horizontal_bar_chart, donut_chart, alert_card, download_csv,
)

st.set_page_config(page_title="Resumen - Dilcor", page_icon="📊", layout="wide")
load_css()

page_header("Resumen", "Vista técnica consolidada para auditoría", "📊")

if "resultado" not in st.session_state:
    no_data_warning()
    st.stop()

resultado = st.session_state["resultado"]
stats = st.session_state["stats"]
cb = stats.get("cobros", {})
pg = stats.get("pagos_prov", {})


# ═══════════════════════════════════════════════════════
# KPIs GENERALES — Foco Contagram → Banco
# ═══════════════════════════════════════════════════════
pct_conc = float(stats.get("tasa_conciliacion_total", 0))
n_exc = stats.get("no_match", 0)
df_det = resultado.get("detalle_facturas", pd.DataFrame())

# Fila 1 — Contagram (protagonista)
monto_ventas = df_det["Total Venta"].sum() if not df_det.empty and "Total Venta" in df_det.columns else stats.get("monto_ventas_contagram", 0)
monto_exacto = cb.get("match_exacto_monto", 0)
monto_ident = monto_exacto + cb.get("probable_duda_id_monto", 0)
cob_total_pct = (monto_ident / monto_ventas * 100) if monto_ventas > 0 else 0

if not df_det.empty and "Estado Conciliacion" in df_det.columns:
    n_conc = len(df_det[df_det["Estado Conciliacion"] == "Conciliada"])
    n_total_f = len(df_det)
else:
    n_conc = 0
    n_total_f = 0

c1, c2, c3, c4 = st.columns(4)
kpi_hero("📋", format_money(monto_ventas), "Total Facturado",
         f"{n_total_f} facturas emitidas", "neutral", c1)
kpi_hero("💰", format_money(monto_ident), "Cobrado Identificado",
         f"Exacto {format_money(monto_exacto)} + probable",
         "success" if cob_total_pct >= 80 else "warning", c2)
kpi_hero("✅", f"{n_conc}", "Facturas Conciliadas",
         f"{(n_conc/n_total_f*100):.1f}% por cantidad — de {n_total_f} totales" if n_total_f > 0 else "Sin datos",
         "success" if n_total_f > 0 and n_conc / n_total_f >= 0.8 else "warning", c3)
kpi_hero("🏦", f"{cob_total_pct:.1f}%", "% Cobertura del Monto",
         f"{format_money(monto_ident)} de {format_money(monto_ventas)} facturado",
         "success" if cob_total_pct >= 80 else "warning" if cob_total_pct >= 50 else "danger", c4)

# Nota: explicar diferencia count vs monto
if n_total_f > 0 and monto_ventas > 0:
    pct_cnt = round(n_conc / n_total_f * 100, 1)
    if abs(pct_cnt - cob_total_pct) > 2:
        n_pend = n_total_f - n_conc
        st.info(
            f"ℹ️ **¿Por qué {pct_cnt}% de facturas pero {cob_total_pct:.1f}% del monto?** "
            f"Las {n_conc} facturas conciliadas tienen mayor valor unitario que las {n_pend} pendientes. "
            f"El % de facturas cuenta unidades, el % de cobertura mide pesos. Ambos son correctos y complementarios."
        )

# Fila 2 — Banco (contexto)
st.caption("🏦 Banco")
c1, c2, c3 = st.columns(3)
kpi_card("Total Movimientos Banco", str(stats.get("total_movimientos", 0)),
         f"Cobros: {cb.get('total', 0)} | Pagos: {pg.get('total', 0)}", "neutral", c1)
kpi_card("Excepciones Pendientes", str(n_exc),
         format_money(stats.get("monto_no_conciliado", 0)),
         "success" if n_exc == 0 else "danger", c2)
kpi_card("Gastos Bancarios", format_money(stats.get("monto_gastos_bancarios", 0)),
         f"{stats.get('gastos_bancarios', 0)} movimientos", "neutral", c3)


# ═══════════════════════════════════════════════════════
# ANALISIS DE CALIDAD - TABLA Y GRAFICO
# ═══════════════════════════════════════════════════════
st.markdown("###")
section_div("Calidad de Conciliación por Banco", "🏛️")

por_banco = stats.get("por_banco", {})

if por_banco:
    col_metrics, col_chart = st.columns([1, 1])
    
    with col_metrics:
        rows = []
        for banco, data in por_banco.items():
            total = max(data.get("movimientos", 1), 1)
            me = data.get("match_exacto", 0)
            nm = data.get("no_match", 0)
            prob = data.get("probable_duda_id", 0) + data.get("probable_dif_cambio", 0)
            
            rows.append({
                "Banco": banco,
                "Movs": data.get("movimientos", 0),
                "% Exacto": f"{round(me / total * 100, 1)}%",
                "% Probable": f"{round(prob / total * 100, 1)}%",
                "% Sin Match": f"{round(nm / total * 100, 1)}%",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with col_chart:
        bancos_names = [r["Banco"] for r in rows]
        vals_exacto = [por_banco[b].get("match_exacto", 0) for b in bancos_names]
        vals_prob = [por_banco[b].get("probable_duda_id", 0) + por_banco[b].get("probable_dif_cambio", 0) for b in bancos_names]
        vals_no = [por_banco[b].get("no_match", 0) for b in bancos_names]

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Exacto", x=bancos_names, y=vals_exacto, marker_color="#0D7C3D"))
        fig.add_trace(go.Bar(name="Probable", x=bancos_names, y=vals_prob, marker_color="#F59E0B"))
        fig.add_trace(go.Bar(name="Sin Match", x=bancos_names, y=vals_no, marker_color="#E30613"))
        fig.update_layout(barmode="stack", height=250, margin=dict(l=10, r=10, t=30, b=10), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════
# TABS DE DETALLE
# ═══════════════════════════════════════════════════════
st.markdown("###")
tab_banco, tab_ctg, tab_por_banco = st.tabs(["🏦 Banco → Contagram", "📄 Contagram → Banco", "🏛️ Por Banco"])


# ── TAB 1: BANCO → CONTAGRAM ──
with tab_banco:
    df_full = resultado.get("resultados", pd.DataFrame())
    if not df_full.empty:
        # Filtros basicos
        c1, c2, c3 = st.columns(3)
        banco_sel = st.selectbox("Banco", ["Todos"] + list(df_full["banco"].unique()), key="res_banco")
        with c2: nivel_sel = st.multiselect("Nivel", df_full["match_nivel"].astype(str).unique(), key="res_nivel")
        with c3: search = st.text_input("Buscar...", key="res_search")
        
        df_show = df_full.copy()
        if banco_sel != "Todos": df_show = df_show[df_show["banco"] == banco_sel]
        if nivel_sel: df_show = df_show[df_show["match_nivel"].astype(str).isin(nivel_sel)]
        if search: df_show = df_show[df_show.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)]

        # Formatear
        num_cols = ["monto", "monto_factura", "diferencia_monto"]
        for c in num_cols:
            if c in df_show.columns:
                df_show[c] = df_show[c].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x)

        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.caption(f"{len(df_show)} registros encontrados.")


# ── TAB 2: CONTAGRAM → BANCO ──
with tab_ctg:
    t1, t2, t3 = st.tabs(["Cobranzas Imputadas", "Pagos Imputados", "Auditoría Facturas"])
    with t1:
        df_cob = resultado.get("cobranzas_csv", pd.DataFrame()).copy()
        if not df_cob.empty:
            for c in ["Importe", "Monto", "monto"]:
                if c in df_cob.columns:
                    df_cob[c] = df_cob[c].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x)
        st.dataframe(df_cob, use_container_width=True)
    with t2:
        df_pag = resultado.get("pagos_csv", pd.DataFrame()).copy()
        if not df_pag.empty:
            for c in ["Importe", "Monto", "monto"]:
                if c in df_pag.columns:
                    df_pag[c] = df_pag[c].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x)
        st.dataframe(df_pag, use_container_width=True)
    with t3:
        # Auditoria Facturas (si existe en Detalle)
        df_det = resultado.get("detalle_facturas", pd.DataFrame()).copy()
        if not df_det.empty:
            for c in ["Total Venta", "Cobrado", "Saldo"]:
                if c in df_det.columns:
                    df_det[c] = df_det[c].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x)
            st.dataframe(df_det, use_container_width=True)
        else:
            st.info("No hay detalle de facturas (modo demo o sin datos).")


# ── TAB 3: POR BANCO (Expanders) ──
with tab_por_banco:
    for banco, data in por_banco.items():
        with st.expander(f"{banco} — {data['movimientos']} movimientos"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Match Exacto", data.get("match_exacto", 0))
            c2.metric("Duda de ID", data.get("probable_duda_id", 0))
            c3.metric("Dif. Cambio", data.get("probable_dif_cambio", 0))
            c4.metric("Sin Match", data.get("no_match", 0))
            st.caption(f"Créditos: {format_money(data.get('monto_creditos', 0))} | Débitos: {format_money(data.get('monto_debitos', 0))}")
