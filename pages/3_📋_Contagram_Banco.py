"""
Pagina 3: Contagram → Banco
"¿Cada factura cobrada tiene reflejo en el banco?"
Perspectiva de Contagram: cada factura/venta y si fue encontrada en el banco.
"""
import streamlit as st
import pandas as pd
from src.ui.styles import load_css
from src.ui.components import (
    kpi_hero, kpi_card, section_div, page_header, format_money,
    build_column_config, render_data_table, no_data_warning,
    horizontal_bar_chart, donut_chart, alert_card,
)

load_css()

page_header(
    "Contagram → Banco",
    "Cada factura de Contagram y si tiene contraparte en el extracto bancario",
    "📋",
)

if "resultado" not in st.session_state:
    no_data_warning()
    st.stop()

resultado = st.session_state["resultado"]
stats = st.session_state["stats"]

# ═══════════════════════════════════════════════════════
# COBRANZAS CONCILIADAS — Tab principal
# ═══════════════════════════════════════════════════════
tab_cobr, tab_pag, tab_facturas = st.tabs(["📥 Cobranzas", "📤 Pagos a Proveedores", "🔍 Auditoría Facturas"])

with tab_cobr:
    section_div("Cobranzas — Para importar en Contagram", "📥")
    df_cob = resultado.get("cobranzas_csv", pd.DataFrame())
    if not df_cob.empty:
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            if "Status" in df_cob.columns:
                niveles = [n for n in df_cob["Status"].unique() if pd.notna(n)]
                filtro_nivel = st.multiselect("Filtrar por status", niveles, default=niveles, key="f_cob_status")
                df_f = df_cob[df_cob["Status"].isin(filtro_nivel)]
            elif "Nivel Match" in df_cob.columns:
                niveles = [n for n in df_cob["Nivel Match"].unique() if pd.notna(n)]
                filtro_nivel = st.multiselect("Filtrar por nivel", niveles, default=niveles, key="f_cob_nivel")
                df_f = df_cob[df_cob["Nivel Match"].isin(filtro_nivel)]
            else:
                df_f = df_cob
        with col2:
            banco_col = "Banco" if "Banco" in df_cob.columns else "Banco Origen"
            if banco_col in df_cob.columns:
                bancos = df_cob[banco_col].unique().tolist()
                filtro_banco = st.multiselect("Filtrar por banco", bancos, default=bancos, key="fb_cob")
                df_f = df_f[df_f[banco_col].isin(filtro_banco)]

        render_data_table(df_f, key="cobranzas_table")

        monto_col = "Monto Cobrado" if "Monto Cobrado" in df_f.columns else None
        total_txt = f"**Total: {len(df_f)} cobranzas"
        if monto_col:
            total_txt += f" | {format_money(df_f[monto_col].sum())}"
        total_txt += "**"
        st.markdown(total_txt)

        from src.ui.components import download_csv
        download_csv(df_f, "cobranzas_conciliadas.csv", "📥 Descargar Cobranzas Conciliadas")
    else:
        st.info("Sin cobranzas conciliadas.")


with tab_pag:
    section_div("Pagos a Proveedores — Para importar en Contagram", "📤")
    df_pag = resultado.get("pagos_csv", pd.DataFrame())
    if not df_pag.empty:
        render_data_table(df_pag, key="pagos_table")

        monto_col_p = "Monto Pagado" if "Monto Pagado" in df_pag.columns else None
        total_txt_p = f"**Total: {len(df_pag)} pagos"
        if monto_col_p:
            total_txt_p += f" | {format_money(df_pag[monto_col_p].sum())}"
        total_txt_p += "**"
        st.markdown(total_txt_p)

        from src.ui.components import download_csv
        download_csv(df_pag, "subir_pagos_contagram.csv", "📥 Descargar Pagos Conciliados")
    else:
        st.info("Sin pagos conciliados.")


with tab_facturas:
    # ═══════════════════════════════════════════════════════
    # AUDITORIA DE FACTURAS
    # ═══════════════════════════════════════════════════════
    if not st.session_state.get("modo_real") or "detalle_facturas" not in resultado:
        st.info("La auditoría de facturas solo está disponible en modo real (datos de Contagram con CUIT/Medio de Cobro).")
    else:
        df_det = resultado.get("detalle_facturas", pd.DataFrame())
        if not df_det.empty:
            section_div("Análisis de Contagram", "📈")

            # KPIs detallados como en la solapa Bancos
            total_facturado = df_det["Total Venta"].sum() if "Total Venta" in df_det.columns else 0
            total_cobrado = df_det["Cobrado"].sum() if "Cobrado" in df_det.columns else 0
            pendiente = total_facturado - total_cobrado
            
            conciliada = df_det[df_det["Estado Conciliacion"] == "Conciliada"]
            sin_match = df_det[df_det["Estado Conciliacion"] == "Sin Match"]

            c1, c2, c3, c4 = st.columns(4)
            n_total = len(df_det)
            
            pct_conciliacion = (len(conciliada) / n_total * 100) if n_total > 0 else 0
            
            kpi_card("Total Facturado", format_money(total_facturado), f"{n_total} facturas", "neutral", c1)
            kpi_card("Cobrado Total", format_money(total_cobrado), f"Pendiente: {format_money(pendiente)}", "neutral", c2)
            kpi_card("Conciliadas", f"{len(conciliada)} ({pct_conciliacion:.1f}%)", "Match en Banco", "success", c3)
            kpi_card("Sin Match", f"{len(sin_match)}", "No halladas en Banco", "danger", c4)

            # Grafico por Medio de Cobro + Dona
            col_graph1, col_graph2 = st.columns([2, 1])
            
            with col_graph1:
                 # Grafico por Medio de Cobro
                if "Medio de Cobro" in df_det.columns and "Cobrado" in df_det.columns:
                    chart_data = df_det.groupby("Medio de Cobro")["Cobrado"].sum().sort_values(ascending=True)
                    if not chart_data.empty:
                        horizontal_bar_chart(
                            chart_data.index.tolist(),
                            chart_data.values.tolist(),
                            "Cobros por Medio de Pago",
                            "#E30613",
                        )
            
            with col_graph2:
                # Dona: Conciliada vs Sin Match
                donut_chart(
                    ["Conciliada", "Sin Match"],
                    [len(conciliada), len(sin_match)],
                    "Estado Conciliación",
                    ["#0D7C3D", "#E30613"],
                    280,
                )

            # Top Clientes Deudores (si existe columna Cliente)
            if "Cliente" in sin_match.columns and "Cobrado" in sin_match.columns:
                top_deudores = sin_match.groupby("Cliente")["Cobrado"].sum().nlargest(5).reset_index()
                st.markdown("##### 🚨 Top Clientes con Facturas Sin Match")
                st.dataframe(
                    top_deudores, 
                    column_config={"Cobrado": st.column_config.NumberColumn(format="$ %.2f")},
                    hide_index=True,
                    use_container_width=True
                )


            # Filtros para tabla de detalle
            st.markdown("###")
            section_div("Detalle de Facturas", "📋")
            c1, c2, c3 = st.columns(3)
            df_view = df_det.copy()

            with c1:
                opciones_estado_con = sorted([str(e) for e in df_det["Estado Conciliacion"].dropna().unique()])
                filtro_est = st.multiselect(
                    "Estado Conciliación", opciones_estado_con,
                    default=["Sin Match"] if "Sin Match" in opciones_estado_con else opciones_estado_con,
                    key="f_est_ctg",
                )
                if filtro_est:
                    df_view = df_view[df_view["Estado Conciliacion"].isin(filtro_est)]

            with c2:
                if "Estado" in df_view.columns:
                    estados = sorted([e for e in df_det["Estado"].unique() if pd.notna(e) and e != ""])
                    filtro_estado = st.multiselect("Estado Factura", estados, default=estados, key="f_estado_ctg")
                    df_view = df_view[df_view["Estado"].isin(filtro_estado)]

            with c3:
                if "Medio de Cobro" in df_view.columns:
                    medios = sorted([m for m in df_det["Medio de Cobro"].unique() if pd.notna(m) and m != ""])
                    filtro_medio = st.multiselect("Medio de Cobro", medios, default=[], key="f_medio_ctg")
                    if filtro_medio:
                        df_view = df_view[df_view["Medio de Cobro"].isin(filtro_medio)]

            render_data_table(df_view, key="facturas_table")

            # Resumen
            resumen = f"**{len(df_view)} facturas listadas**"
            if "Total Venta" in df_view.columns:
                resumen += f" | Total Venta: **{format_money(df_view['Total Venta'].sum())}**"
            if "Cobrado" in df_view.columns:
                resumen += f" | Cobrado: **{format_money(df_view['Cobrado'].sum())}**"
            st.markdown(resumen)

            from src.ui.components import download_csv
            download_csv(df_view, "auditoria_facturas.csv", "📥 Descargar Auditoría Facturas")

        else:
            st.info("No hay detalle de facturas disponible.")
