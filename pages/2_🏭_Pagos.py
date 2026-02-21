"""
Pagina 2: Pagos a Proveedores
Conciliacion de egresos — movimientos DEBITO del banco vs compras Contagram.

Keys usadas de session_state:
  resultado["resultados"]       → DataFrame movimientos (filtrar DEBITO / pago_proveedor)
  stats["pagos_prov"]           → KPIs bancos
  stats["monto_compras_contagram"] → Total OCs
  datos_compras                 → DataFrame original de OCs (para alertas)
"""
import streamlit as st
import pandas as pd
from src.ui.styles import load_css
from src.ui.components import (
    kpi_card, kpi_hero, section_div, page_header, format_money,
    build_column_config, render_data_table, no_data_warning,
    alert_card,
)

st.set_page_config(page_title="Pagos - Dilcor", page_icon="🏭", layout="wide")
load_css()

page_header("Pagos a Proveedores", "Conciliación de egresos: débitos bancarios vs compras Contagram", "🏭")

if "resultado" not in st.session_state:
    no_data_warning()
    st.stop()

resultado = st.session_state["resultado"]
stats = st.session_state["stats"]
pg = stats.get("pagos_prov", {})
df_full = resultado.get("resultados", pd.DataFrame())

# DataFrame Pagos
df_pagos = pd.DataFrame()
if not df_full.empty:
    df_pagos = df_full.copy()
    if "tipo" in df_pagos.columns:
        df_pagos = df_pagos[df_pagos["tipo"] == "DEBITO"]
    elif "clasificacion" in df_pagos.columns:
        df_pagos = df_pagos[df_pagos["clasificacion"] == "pago_proveedor"]
    if "clasificacion" in df_pagos.columns:
        df_pagos = df_pagos[df_pagos["clasificacion"] != "gasto_bancario"]

# Datos Contagram (OCs)
df_compras = st.session_state.get("datos_compras", pd.DataFrame())


# ═══════════════════════════════════════════════════════
# SECCION A — KPIs (3 FILAS) — Foco Contagram → Banco
# ═══════════════════════════════════════════════════════
section_div("Panorama de Pagos", "📊")

# Cálculos compartidos
monto_ocs = stats.get("monto_compras_contagram", 0)
n_ocs = len(df_compras) if not df_compras.empty else (stats.get("cant_compras_contagram", 0))
monto_conciliado_pg = pg.get("match_exacto_monto", 0)
monto_pendiente_banco_pg = pg.get("monto_total", 0) - monto_conciliado_pg

# OCs pendientes
if "factura_match" in df_pagos.columns:
    ocs_pagadas = set(df_pagos[df_pagos["factura_match"].notna()]["factura_match"].unique())
else:
    ocs_pagadas = set()
col_id = None
if not df_compras.empty:
    col_id = "Nro OC" if "Nro OC" in df_compras.columns else "Nro Factura" if "Nro Factura" in df_compras.columns else None
    if col_id:
        pendientes_oc = df_compras[~df_compras[col_id].isin(ocs_pagadas)]
        n_pend = len(pendientes_oc)
        m_pend = pendientes_oc["Monto Total"].sum() if "Monto Total" in pendientes_oc.columns else 0
    else:
        n_pend = "N/D"
        m_pend = 0
else:
    gap = stats.get("payment_gap", 0)
    n_pend = "N/D"
    m_pend = gap

m_ocs_conciliado = monto_ocs - m_pend if isinstance(m_pend, (int, float)) else 0
n_ocs_conc = (n_ocs - n_pend) if isinstance(n_pend, (int, float)) and isinstance(n_ocs, (int, float)) else 0
cobertura_oc = (m_ocs_conciliado / monto_ocs * 100) if monto_ocs > 0 else 0

# --- FILA 1: Contagram (protagonista) | Banco (contexto) ---
col_ctg, col_sep, col_banco = st.columns([5, 1, 5])

with col_ctg:
    st.markdown("#### 📋 Contagram (Compras)")
    c1, c2, c3 = st.columns(3)
    kpi_card("Total en OCs", format_money(monto_ocs),
             f"{n_ocs} OCs registradas", "neutral", c1)
    kpi_card("OCs Pendientes", f"{n_pend}",
             f"Monto: {format_money(m_pend)}", "warning", c2)
    kpi_card("OCs Conciliadas", f"{n_ocs_conc}",
             f"de {n_ocs} totales ({(n_ocs_conc/n_ocs*100):.1f}%)" if isinstance(n_ocs, (int, float)) and n_ocs > 0 else "Sin datos",
             "success" if isinstance(n_ocs, (int, float)) and n_ocs > 0 and n_ocs_conc / n_ocs >= 0.8 else "warning", c3)

with col_sep:
    st.markdown("<div style='border-left: 2px solid #0D7C3D; height: 160px; margin: 20px auto; width: 0;'></div>", unsafe_allow_html=True)

with col_banco:
    st.markdown("#### 🏦 Banco (Egresos)")
    c1, c2 = st.columns(2)
    kpi_card("Débitos Bancarios", format_money(pg.get("monto_total", 0)),
             f"{pg.get('total', 0)} movimientos", "neutral", c1)
    kpi_card("Conciliado $", format_money(monto_conciliado_pg),
             f"Pendiente: {format_money(monto_pendiente_banco_pg)}", "success", c2)


# --- FILA 2: Métricas Contagram ---
st.markdown("###")
st.markdown("#### 📋 Contagram")
c1, c2, c3, c4 = st.columns(4)

kpi_card("Monto OCs Conciliado $", format_money(m_ocs_conciliado),
         "Pagos confirmados", "success", c1)

oc_prom = monto_ocs / n_ocs if isinstance(n_ocs, (int, float)) and n_ocs > 0 else 0
kpi_card("OC Promedio", format_money(oc_prom),
         f"{n_ocs} OCs", "neutral", c2)

color_cob = "success" if cobertura_oc >= 80 else "warning" if cobertura_oc >= 50 else "danger"
kpi_card("% Cobertura OCs", f"{cobertura_oc:.1f}%",
         "Del total de OCs registradas", color_cob, c3)
# c4 libre — se puede agregar metric futura
c4.empty()


# --- FILA 3: Banco — Desglose por nivel de match ---
st.markdown("###")
st.markdown("#### 🏦 Banco — Desglose por nivel de match")
c1, c2, c3, c4 = st.columns(4)
kpi_card("Match Exacto", f"{pg.get('match_exacto', 0)} mov.",
         f"({pg.get('match_directo', 0)} dir + {pg.get('match_suma', 0)} suma)",
         "success", c1)
kpi_card("Duda de ID", f"{pg.get('probable_duda_id', 0)} mov.",
         format_money(pg.get("probable_duda_id_monto", 0)), "warning", c2)
kpi_card("Dif. de Cambio", f"{pg.get('probable_dif_cambio', 0)} mov.",
         format_money(pg.get("probable_dif_cambio_monto", 0)), "warning", c3)
kpi_card("Sin Identificar", f"{pg.get('no_match', 0)} mov.",
         format_money(pg.get("no_match_monto", 0)), "danger", c4)


# ═══════════════════════════════════════════════════════
# SECCION B — ALERTAS PRIORITARIAS
# ═══════════════════════════════════════════════════════
st.markdown("###")
section_div("Alertas Prioritarias", "🚨")

# Columna de proveedor (definida aquí para reusar en Sección C)
prov_col = "Proveedor" if (not df_compras.empty and "Proveedor" in df_compras.columns) else "Cliente"

# ── ALERTA 1: Top Proveedores con OCs Sin Match ──
# Proveedores con OCs pero sin pagos
if not df_compras.empty and col_id:
    # df_compras tiene proveedor, monto, fecha?
    # Agrupar compras por Proveedor
    if prov_col in df_compras.columns:
        compras_pend = df_compras[~df_compras[col_id].isin(ocs_pagadas)]
        
        if not compras_pend.empty:
            grp = compras_pend.groupby(prov_col).agg({
                "Monto Total": "sum",
                col_id: "count",
                "Fecha": "max"
            }).reset_index().rename(columns={col_id: "Cantidad OCs", "Monto Total": "Deuda Pendiente", "Fecha": "Última OC"})
            
            top_deuda = grp.sort_values("Deuda Pendiente", ascending=False).head(10)
            total_risk = grp["Deuda Pendiente"].sum()
            
            # Formatear
            top_deuda["Deuda Pendiente"] = top_deuda["Deuda Pendiente"].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) else x)
            
            with st.expander(f"🔴 Top Proveedores con OCs Sin Match — {len(grp)} proveedores | {format_money(total_risk)}", expanded=True):
                st.caption("Proveedores con OCs registradas pero **ningún pago identificado**.")
                st.dataframe(
                    top_deuda[[prov_col, "Cantidad OCs", "Deuda Pendiente", "Última OC"]],
                    use_container_width=True, hide_index=True
                )
                st.info("💡 Acción: Verificar si el pago salió bajo otro alias → revisar Excepciones.")
        else:
            st.success("✅ Todas las OCs tienen pagos identificados.")
else:
    st.info("⚠️ Alerta no disponible (faltan datos compras)")


# ── ALERTA 2: Pagos en Banco sin OC en Contagram ──
# Débito clasificado 'pago_proveedor' (o matched nivel exacto/probable) 
# pero 'factura_match' está vacía o no cruza con df_compras?
# Si el motor hace match, asigna 'nombre_contagram' y 'factura_match'.
# Si 'match_detalle' dice "Match proveedor..." pero no factura?
# Buscamos pagos donde 'nombre_contagram' existe, pero 'factura_match' es NULL?
# O donde 'clasificacion' == 'pago_proveedor' y 'match_nivel' == 'no_match' (provider unknown)?
# El prompt dice: clasificados pago pero sin OC.
# Interpretamos: Pagos identificados (nombre_contagram OK) pero factura_match NULL.
match_col = "match_nivel" if "match_nivel" in df_pagos.columns else "conciliation_status"
if "nombre_contagram" in df_pagos.columns:
    pagos_con_prov = df_pagos[(df_pagos["nombre_contagram"].notna()) & (df_pagos["nombre_contagram"] != "")]
else:
    pagos_con_prov = pd.DataFrame()
if not pagos_con_prov.empty and "factura_match" in pagos_con_prov.columns:
    pagos_sin_oc = pagos_con_prov[pagos_con_prov["factura_match"].isna() | (pagos_con_prov["factura_match"] == "")]
    if not pagos_sin_oc.empty:
         with st.expander(f"🔴 Pagos en Banco sin OC en Contagram — {len(pagos_sin_oc)} pagos", expanded=False):
            st.caption("Pagos donde se identificó el proveedor, pero **no se encontró la OC específica**.")
            
            # Formatear
            pagos_sin_oc["monto"] = pagos_sin_oc["monto"].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) else x)
            
            st.dataframe(
                pagos_sin_oc[["nombre_contagram", "banco", "fecha", "monto", "descripcion"]],
                use_container_width=True, hide_index=True
            )
            st.warning("Verificar si es un anticipo o la OC no fue cargada.")
    else:
        st.success("✅ Todos los pagos identificados tienen OC asociada.")
else:
    # Fallback si no hay columna nombre_contagram o factura_match
    pass


# ── ALERTA 3: Top 5 Débitos Sin Identificar ──
df_no_match = df_pagos[df_pagos[match_col] == "no_match"]
if not df_no_match.empty:
    top5 = df_no_match.nlargest(5, "monto").copy()
    top5["monto"] = top5["monto"].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) else x)
    
    with st.expander(f"🔴 Top 5 Débitos Sin Identificar — Total: {format_money(df_no_match['monto'].sum())}", expanded=True):
        st.dataframe(
            top5[["descripcion", "banco", "fecha", "monto"]],
            use_container_width=True, hide_index=True
        )
        st.info("💡 Acción: Verificar si corresponde a proveedor no registrado o agregar alias.")
else:
    st.success("✅ No hay débitos sin identificar.")


# ── ALERTA 4: Proveedores Pagados Diferente a la OC ──
if "diferencia_monto" in df_pagos.columns:
    df_dif = df_pagos[
        (df_pagos["diferencia_monto"].abs() > 0.01) & 
        (df_pagos[match_col] != "no_match")
    ]
    if not df_dif.empty:
        pag_mas = df_dif[df_dif["diferencia_monto"] > 0]
        pag_menos = df_dif[df_dif["diferencia_monto"] < 0]
        
        # Columnas disponibles para la tabla de diferencias
        dif_cols = [c for c in ["nombre_contagram", "monto", "monto_factura", "diferencia_monto", "diferencia_pct"] if c in df_dif.columns]

        # Formatear columnas numericas
        cols_to_fmt = [c for c in ["monto", "monto_factura", "diferencia_monto"] if c in df_dif.columns]
        
        with st.expander(f"🟡 Proveedores Pagados Diferente — {len(df_dif)} casos", expanded=False):
            st.markdown(f"**📈 Pagado de MÁS: {len(pag_mas)}**")
            if not pag_mas.empty:
                disp_mas = pag_mas[dif_cols].copy()
                for c in cols_to_fmt:
                    disp_mas[c] = disp_mas[c].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) else x)
                st.dataframe(disp_mas.reset_index(drop=True), hide_index=True, use_container_width=True)
            
            st.markdown(f"**📉 Pagado de MENOS: {len(pag_menos)}**")
            if not pag_menos.empty:
                disp_menos = pag_menos[dif_cols].copy()
                for c in cols_to_fmt:
                    disp_menos[c] = disp_menos[c].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) else x)
                st.dataframe(disp_menos.reset_index(drop=True), hide_index=True, use_container_width=True)


# ═══════════════════════════════════════════════════════
# SECCION C — TABLA (doble tab: Contagram → Banco)
# ═══════════════════════════════════════════════════════
st.markdown("###")
section_div("Detalle de Pagos", "📄")

# Tabs: OCs Contagram como default, Banco como secundaria
tab_ctg_p, tab_banco_p = st.tabs(["📋 OCs Contagram", "🏦 Movimientos Banco"])

# ── Tab 1: OCs Contagram ──
with tab_ctg_p:
    st.info("ℹ️ **Detalle de OCs con estado de conciliación pendiente de implementar en motor.** "
            "Se muestran los datos crudos de compras/OCs cargados desde Contagram.")

    if not df_compras.empty:
        # Filtros básicos
        c1, c2, c3 = st.columns(3)
        with c1:
            if prov_col in df_compras.columns:
                provs = sorted(df_compras[prov_col].dropna().unique())
                prov_sel = st.multiselect("Proveedor", provs, key="oc_prov")
            else:
                prov_sel = []
        with c2:
            if "Fecha" in df_compras.columns:
                try:
                    _fechas_p = pd.to_datetime(df_compras["Fecha"], errors="coerce")
                    _min_fp = _fechas_p.dropna().min()
                    _max_fp = _fechas_p.dropna().max()
                    if pd.notna(_min_fp) and pd.notna(_max_fp) and _min_fp < _max_fp:
                        rango_fecha_oc = st.date_input(
                            "Rango Fecha OC",
                            value=(_min_fp.date(), _max_fp.date()),
                            min_value=_min_fp.date(),
                            max_value=_max_fp.date(),
                            key="oc_fecha_rango",
                        )
                    else:
                        rango_fecha_oc = None
                except Exception:
                    rango_fecha_oc = None
            else:
                rango_fecha_oc = None
        with c3:
            search_oc = st.text_input("Buscar proveedor / nro OC", key="oc_search")

        df_oc_show = df_compras.copy()
        if prov_sel and prov_col in df_oc_show.columns:
            df_oc_show = df_oc_show[df_oc_show[prov_col].isin(prov_sel)]
        if rango_fecha_oc and isinstance(rango_fecha_oc, tuple) and len(rango_fecha_oc) == 2:
            try:
                _fp_oc = pd.to_datetime(df_oc_show["Fecha"], errors="coerce")
                df_oc_show = df_oc_show[
                    (_fp_oc >= pd.Timestamp(rango_fecha_oc[0])) & (_fp_oc <= pd.Timestamp(rango_fecha_oc[1]))
                ]
            except Exception:
                pass
        if search_oc:
            mask = df_oc_show.astype(str).apply(
                lambda x: x.str.contains(search_oc, case=False, na=False)
            ).any(axis=1)
            df_oc_show = df_oc_show[mask]

        # Formatear montos
        df_oc_disp = df_oc_show.copy()
        for mc in ["Monto Total", "monto"]:
            if mc in df_oc_disp.columns:
                df_oc_disp[mc] = df_oc_disp[mc].apply(
                    lambda x: f"$ {x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x
                )

        st.dataframe(df_oc_disp.reset_index(drop=True), use_container_width=True, hide_index=True)

        # Totales
        total_ocs_vis = df_oc_show["Monto Total"].sum() if "Monto Total" in df_oc_show.columns else 0
        st.markdown(f"**Total OCs visible: {format_money(total_ocs_vis)} — {len(df_oc_show)} OCs**")
    else:
        st.warning("Sin datos de compras/OCs de Contagram.")

# ── Tab 2: Movimientos Banco (tabla original) ──
with tab_banco_p:
    if not df_pagos.empty:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            banco_sel_p = st.multiselect("Banco", df_pagos["banco"].unique(), key="banco_sel_pag")
        with c2:
            niveles_p = df_pagos[match_col].astype(str).unique()
            nivel_sel_p = st.multiselect("Nivel Match", niveles_p, key="nivel_sel_pag")
        with c3:
            pass
        with c4:
            search_p = st.text_input("Buscar proveedor/importe", key="search_pag")

        df_show_p = df_pagos.copy()
        if banco_sel_p:
            df_show_p = df_show_p[df_show_p["banco"].isin(banco_sel_p)]
        if nivel_sel_p:
            df_show_p = df_show_p[df_show_p[match_col].astype(str).isin(nivel_sel_p)]
        if search_p:
            df_show_p = df_show_p[df_show_p.astype(str).apply(
                lambda x: x.str.contains(search_p, case=False, na=False)
            ).any(axis=1)]

        cols = ["fecha", "banco", "descripcion", "nombre_contagram", "monto", "monto_factura", "diferencia_monto", match_col]
        cols = [c for c in cols if c in df_show_p.columns]

        df_disp = df_show_p[cols].copy()
        num_cols = ["monto", "monto_factura", "diferencia_monto"]
        for c in num_cols:
            if c in df_disp.columns:
                df_disp[c] = df_disp[c].apply(
                    lambda x: f"$ {x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x
                )

        st.dataframe(df_disp, use_container_width=True, hide_index=True)
        st.markdown(f"**Total visible: {format_money(df_show_p['monto'].sum())}**")
    else:
        st.info("Sin movimientos bancarios de tipo débito.")


# ═══════════════════════════════════════════════════════
# SECCION D — Excepciones Banco (débitos sin identificar)
# ═══════════════════════════════════════════════════════
if not df_pagos.empty:
    # Filtrar débitos no_match / EXCLUDED
    _exc_mask_p = pd.Series(False, index=df_pagos.index)
    if "conciliation_status" in df_pagos.columns:
        _exc_mask_p = _exc_mask_p | (df_pagos["conciliation_status"] == "EXCLUDED")
    if match_col in df_pagos.columns:
        _exc_mask_p = _exc_mask_p | (df_pagos[match_col] == "no_match")

    df_exc_pagos = df_pagos[_exc_mask_p].copy()

    if not df_exc_pagos.empty:
        n_exc_p = len(df_exc_pagos)
        monto_exc_p = df_exc_pagos["monto"].sum()

        with st.expander(
            f"🔴 Débitos Bancarios Sin Identificar — {n_exc_p} movimientos | {format_money(monto_exc_p)}",
            expanded=False,
        ):
            exc_cols_p = ["fecha", "banco", "descripcion", "cuit_banco", "nombre_contagram", "monto", "conciliation_tag", "match_detalle"]
            exc_cols_p = [c for c in exc_cols_p if c in df_exc_pagos.columns]

            df_exc_disp_p = df_exc_pagos[exc_cols_p].copy()
            if "monto" in df_exc_disp_p.columns:
                df_exc_disp_p["monto"] = df_exc_disp_p["monto"].apply(
                    lambda x: f"$ {x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x
                )

            st.dataframe(df_exc_disp_p.reset_index(drop=True), use_container_width=True, hide_index=True)

            st.info(
                "💡 Estos movimientos pueden ser pagos a proveedores no registrados en Contagram, "
                "transferencias internas, o pagos de períodos anteriores. Revisarlos en "
                "Excepciones para agregar alias a la tabla paramétrica."
            )

from src.chatbot import render_chatbot_flotante
render_chatbot_flotante()