"""
Pagina 1: Cobros
Conciliacion de ingresos — movimientos CREDITO del banco vs ventas Contagram.

Keys usadas de session_state:
  resultado["resultados"]       → DataFrame movimientos (filtrar CREDITO)
  stats["cobros"]               → KPIs bancos
  stats["monto_ventas_contagram"] → Total facturado
  datos_ventas                  → DataFrame original de ventas (para alertas)
  detalle_facturas              → Resultado procesado de facturas (modo real)
"""
import streamlit as st
import pandas as pd
from src.ui.styles import load_css
from src.ui.components import (
    kpi_card, kpi_hero, section_div, page_header, format_money,
    build_column_config, render_data_table, no_data_warning,
    donut_chart, alert_card,
)

st.set_page_config(page_title="Cobros - Dilcor", page_icon="💰", layout="wide")
load_css()

page_header("Cobros", "Conciliación de ingresos: créditos bancarios vs ventas Contagram", "💰")

if "resultado" not in st.session_state:
    no_data_warning()
    st.stop()

resultado = st.session_state["resultado"]
stats = st.session_state["stats"]
cb = stats.get("cobros", {})
df_full = resultado.get("resultados", pd.DataFrame())

# DataFrame Cobros
df_cobros = pd.DataFrame()
if not df_full.empty:
    df_cobros = df_full.copy()
    if "tipo" in df_cobros.columns:
        df_cobros = df_cobros[df_cobros["tipo"] == "CREDITO"]
    elif "clasificacion" in df_cobros.columns:
        df_cobros = df_cobros[df_cobros["clasificacion"] == "cobranza"]

# Datos Contagram
df_ventas = st.session_state.get("datos_ventas", pd.DataFrame())
df_det = resultado.get("detalle_facturas", pd.DataFrame())  # Processed invoice status


# ═══════════════════════════════════════════════════════
# SECCION A — KPIs (3 FILAS) — Foco Contagram → Banco
# ═══════════════════════════════════════════════════════
section_div("Panorama de Cobros", "📊")

# Cálculos compartidos (usados en varias filas)
monto_ventas = stats.get("monto_ventas_contagram", 0)
n_facturas = len(df_det) if not df_det.empty else (len(df_ventas) if not df_ventas.empty else 0)
monto_exacto = cb.get("match_exacto_monto", 0)
monto_identificado = monto_exacto + cb.get("probable_duda_id_monto", 0)
monto_conciliado = cb.get("match_exacto_monto", 0)
monto_pendiente_banco = cb.get("monto_total", 0) - monto_conciliado

if not df_det.empty and "Estado Conciliacion" in df_det.columns:
    pendientes = df_det[df_det["Estado Conciliacion"] != "Conciliada"]
    n_pend = len(pendientes)
    m_pend = pendientes["Total Venta"].sum() if "Total Venta" in pendientes.columns else 0
    conciliadas = df_det[df_det["Estado Conciliacion"] == "Conciliada"]
    n_conc = len(conciliadas)
else:
    n_pend = "N/D"
    m_pend = 0
    n_conc = 0

cobertura_exacto = (monto_exacto / monto_ventas * 100) if monto_ventas > 0 else 0
cobertura_total = (monto_identificado / monto_ventas * 100) if monto_ventas > 0 else 0

# --- FILA 1: Contagram (protagonista) | Banco (contexto) ---
col_ctg, col_sep, col_banco = st.columns([5, 1, 5])

with col_ctg:
    st.markdown("#### 📋 Contagram (Ventas)")
    c1, c2, c3 = st.columns(3)
    kpi_card("Total Facturado", format_money(monto_ventas),
             f"{n_facturas} facturas emitidas", "neutral", c1)
    kpi_card("Facturas Pendientes", f"{n_pend}",
             f"Monto: {format_money(m_pend)}", "warning", c2)
    kpi_card("Facturas Conciliadas", f"{n_conc}",
             f"de {n_facturas} totales ({(n_conc/n_facturas*100):.1f}%) — match exacto" if n_facturas > 0 else "Sin datos",
             "success" if n_facturas > 0 and n_conc / n_facturas >= 0.8 else "warning", c3)

with col_sep:
    st.markdown("<div style='border-left: 2px solid #E30613; height: 160px; margin: 20px auto; width: 0;'></div>", unsafe_allow_html=True)

with col_banco:
    st.markdown("#### 🏦 Banco (Ingresos)")
    c1, c2 = st.columns(2)
    kpi_card("Créditos Bancarios", format_money(cb.get("monto_total", 0)),
             f"{cb.get('total', 0)} movimientos", "neutral", c1)
    kpi_card("Conciliado $", format_money(monto_conciliado),
             f"Pendiente: {format_money(monto_pendiente_banco)}", "success", c2)


# --- FILA 2: Métricas Contagram ---
st.markdown("###")
st.markdown("#### 📋 Contagram")
c1, c2, c3, c4 = st.columns(4)

kpi_card("Conciliado Exacto $", format_money(monto_exacto),
         f"{n_conc} facturas — solo match exacto", "success", c1)

# Facturas identificadas (exacto + probable)
n_ident = n_conc + (len(df_det[df_det["Estado Conciliacion"].str.contains("Probable", case=False, na=False)]) if not df_det.empty and "Estado Conciliacion" in df_det.columns else 0)
kpi_card("Identificado Total $", format_money(monto_identificado),
         f"{n_conc} exactas + {cb.get('probable_duda_id', 0)} probables", "warning", c2)
kpi_card("Cob. Exacta", f"{cobertura_exacto:.1f}%",
         f"{format_money(monto_exacto)} — {n_conc} fact.", "danger" if cobertura_exacto < 50 else "warning", c3)
kpi_card("Cob. Total", f"{cobertura_total:.1f}%",
         f"{format_money(monto_identificado)} — {n_conc}+{cb.get('probable_duda_id', 0)} fact.", "warning" if cobertura_total < 80 else "success", c4)


# --- FILA 3: Banco — Desglose por nivel de match ---
st.markdown("###")
st.markdown("#### 🏦 Banco — Desglose por nivel de match")
c1, c2, c3, c4 = st.columns(4)
kpi_card("Match Exacto", f"{cb.get('match_exacto', 0)} mov.",
         f"{format_money(monto_exacto)} ({cb.get('match_directo', 0)} dir + {cb.get('match_suma', 0)} suma)",
         "success", c1)
kpi_card("Duda de ID", f"{cb.get('probable_duda_id', 0)} mov.",
         format_money(cb.get("probable_duda_id_monto", 0)), "warning", c2)
kpi_card("Dif. de Cambio", f"{cb.get('probable_dif_cambio', 0)} mov.",
         format_money(cb.get("probable_dif_cambio_monto", 0)), "warning", c3)
kpi_card("Sin Identificar", f"{cb.get('no_match', 0)} mov.",
         format_money(cb.get("no_match_monto", 0)), "danger", c4)

# ═══════════════════════════════════════════════════════
# SECCION B — ALERTAS PRIORITARIAS
# ═══════════════════════════════════════════════════════
st.markdown("###")
section_div("Alertas Prioritarias", "🚨")

# ── ALERTA 1: Top Clientes con Facturas Sin Match ──
# Clientes con facturas pendientes pero SIN cobros identificados
clientes_sin_match = pd.DataFrame()
if not df_det.empty:
    # Agrupar facturas por cliente
    agg_dict = {
        "Total Venta": "sum",
        "Estado Conciliacion": lambda x: (x != "Conciliada").all()  # True si NINGUNA conciliada
    }
    # Agregar conteo y última fecha si existen
    if "Nro Factura" in df_det.columns:
        agg_dict["Nro Factura"] = "count"
    if "Fecha Emision" in df_det.columns:
        agg_dict["Fecha Emision"] = "max"
    
    facturas_por_cliente = df_det.groupby("Cliente").agg(agg_dict).reset_index()
    
    # Renombrar columnas
    rename_map = {"Estado Conciliacion": "Sin Match Total", "Total Venta": "Monto Pendiente"}
    if "Nro Factura" in facturas_por_cliente.columns:
        rename_map["Nro Factura"] = "Cant. Facturas"
    if "Fecha Emision" in facturas_por_cliente.columns:
        rename_map["Fecha Emision"] = "Última Factura"
    facturas_por_cliente = facturas_por_cliente.rename(columns=rename_map)
    
    # Filtrar: clientes donde NINGUNA factura fue conciliada
    pendientes_strict = facturas_por_cliente[
        (facturas_por_cliente["Sin Match Total"] == True) & 
        (facturas_por_cliente["Monto Pendiente"] > 0)
    ].sort_values("Monto Pendiente", ascending=False)
    
    if not pendientes_strict.empty:
        top_pend = pendientes_strict.head(10)
        monto_riesgo = pendientes_strict["Monto Pendiente"].sum()
        
        # Formatear Monto Pendiente manualmente para evitar errores de sprintf
        top_pend["Monto Pendiente Formatted"] = top_pend["Monto Pendiente"].apply(lambda x: f"$ {x:,.0f}")
        
        # Columnas a mostrar
        show_cols = ["Cliente"]
        if "Cant. Facturas" in top_pend.columns:
            show_cols.append("Cant. Facturas")
        show_cols.append("Monto Pendiente Formatted")
        if "Última Factura" in top_pend.columns:
            show_cols.append("Última Factura")
        
        with st.expander(f"🔴 Top Clientes con Facturas Sin Match — {len(pendientes_strict)} clientes | {format_money(monto_riesgo)} en riesgo", expanded=True):
            st.caption("Clientes con facturas pendientes y **ningún cobro identificado** en bancos.")
            st.dataframe(
                top_pend[show_cols].rename(columns={"Monto Pendiente Formatted": "Monto Pendiente"}).reset_index(drop=True),
                use_container_width=True, hide_index=True
            )
            st.markdown(f"**Total en Riesgo: {format_money(monto_riesgo)}**")
            st.info("💡 Acción sugerida: Verificar si el pago llegó bajo otro alias → revisar Excepciones/Sin Identificar.")
    else:
        st.success("✅ Todos los clientes con facturas tienen al menos un cobro parcial identificado.")
else:
    st.info("⚠️ Alerta no disponible (faltan datos Contagram)")

# ── ALERTA 2: Cobros en Banco sin Factura en Contagram ──
# Movimientos match_exacto/probable pero cliente NO tiene facturas pendientes?
# O simplemente cobros matcheados a un cliente que no existe en Ventas? 
# Si matcheo, es porque existe en Ventas (o tabla parametrica).
# Riesgo: dinero entró, matcheamos cliente, pero "ese cliente no tiene facturas pendientes".
# Iteramos cobros matcheados y verificamos saldo del cliente en Contagram.
if not df_cobros.empty and not df_det.empty:
    cobros_match = df_cobros[df_cobros["nombre_contagram"].notna() & (df_cobros["nombre_contagram"] != "")]
    # Clientes con facturas pendientes
    clientes_con_deuda = df_det[df_det["Estado Conciliacion"] != "Conciliada"]["Cliente"].unique()
    
    # Cobros a clientes que NO estan en la lista de con deuda?
    # (Esto puede pasar si el cobro saldo la deuda y quedo 'Conciliada', ojo.
    #  La alerta dice: "no tiene facturas pendientes REGISTRADAS". O sea, sobró plata? o pagó algo que no está cargado?)
    # Asumimos riesgo: cobro identificado, pero cliente no tiene factura pendiente DE ANTES?
    # Simplificación: Cliente identificado en banco pero que no figura en el dataframe de Ventas del periodo?
    # O Cliente que figura en Ventas pero su saldo es 0 o a favor?
    
    # Implementación: Cobros donde el cliente NO tiene 'Total Venta' > 0 en el periodo analizado
    # (Si usamos solo ventas del periodo, esto detecta anticipos o pagos de facturas viejas no incluidas)
    clientes_ventas_periodo = df_det["Cliente"].unique()
    cobros_sin_factura = cobros_match[~cobros_match["nombre_contagram"].isin(clientes_ventas_periodo)]
    
    if not cobros_sin_factura.empty:
        with st.expander(f"🔴 Cobros en Banco sin Factura en Contagram — {len(cobros_sin_factura)} movimientos", expanded=False):
            st.caption("Cobros identificados de clientes que **no tienen facturas registradas** en este período.")
            
            # Formato moneda
            cobros_sin_factura["monto"] = cobros_sin_factura["monto"].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) else x)
            
            st.dataframe(
                cobros_sin_factura[["nombre_contagram", "monto", "fecha", "banco"]],
                use_container_width=True, hide_index=True
            )
            st.warning("Verificar si son anticipos o pagos de facturas de meses anteriores no cargadas.")
    else:
       st.success("✅ Todos los clientes identificados tienen facturas en el período.")


# ── ALERTA 3: Top 5 Créditos Sin Identificar ──
match_col = "match_nivel" if "match_nivel" in df_cobros.columns else "conciliation_status"
if match_col in df_cobros.columns:
    df_no_match = df_cobros[df_cobros[match_col] == "no_match"]
    if not df_no_match.empty:
        top5 = df_no_match.nlargest(5, "monto").copy()
        top5["monto"] = top5["monto"].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) else x)
        
        with st.expander(f"🔴 Top 5 Créditos Sin Identificar — Total: {format_money(df_no_match['monto'].sum())}", expanded=True):
            st.dataframe(
                top5[["descripcion", "banco", "fecha", "monto"]],
                use_container_width=True, hide_index=True
            )
            st.info("💡 Acción: Agregar alias a tabla paramétrica.")
    else:
        st.success("✅ No hay créditos sin identificar.")


# ── ALERTA 4: Clientes con Cobro Diferente ──
if "diferencia_monto" in df_cobros.columns:
    df_dif = df_cobros[
        (df_cobros["diferencia_monto"].abs() > 0.01) & 
        (df_cobros[match_col] != "no_match")
    ]
    if not df_dif.empty:
        cob_mas = df_dif[df_dif["diferencia_monto"] > 0]
        cob_menos = df_dif[df_dif["diferencia_monto"] < 0]
        
        # Columnas disponibles para la tabla de diferencias
        dif_cols = [c for c in ["nombre_contagram", "monto", "monto_factura", "diferencia_monto", "diferencia_pct"] if c in df_dif.columns]
        
        # Formatear columnas numericas
        cols_to_fmt = [c for c in ["monto", "monto_factura", "diferencia_monto"] if c in df_dif.columns]
        
        with st.expander(f"🟡 Clientes con Cobro Diferente — {len(df_dif)} casos", expanded=False):
            st.markdown(f"**📈 Cobrado de MÁS: {len(cob_mas)}**")
            if not cob_mas.empty:
                disp_mas = cob_mas[dif_cols].copy()
                for c in cols_to_fmt:
                    disp_mas[c] = disp_mas[c].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) else x)
                st.dataframe(disp_mas.reset_index(drop=True), hide_index=True, use_container_width=True)
            
            st.markdown(f"**📉 Cobrado de MENOS: {len(cob_menos)}**")
            if not cob_menos.empty:
                disp_menos = cob_menos[dif_cols].copy()
                for c in cols_to_fmt:
                    disp_menos[c] = disp_menos[c].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) else x)
                st.dataframe(disp_menos.reset_index(drop=True), hide_index=True, use_container_width=True)


# ═══════════════════════════════════════════════════════
# SECCION C — TABLA (doble tab: Contagram → Banco)
# ═══════════════════════════════════════════════════════
st.markdown("###")
section_div("Detalle de Cobros", "📄")

# Determinar si la vista Contagram está disponible
_vista_ctg_disponible = not df_det.empty and "Estado Conciliacion" in df_det.columns

if not _vista_ctg_disponible:
    st.warning("⚠️ Vista Contagram no disponible (modo demo o datos sin detalle_facturas) — mostrando vista banco.")

# Tabs: Contagram como default, Banco como secundaria
tab_ctg, tab_banco = st.tabs(["📋 Facturas Contagram", "🏦 Movimientos Banco"])

# ── Tab 1: Facturas Contagram ──
with tab_ctg:
    if _vista_ctg_disponible:
        # --- Filtros ---
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            estados_disp = sorted(df_det["Estado Conciliacion"].dropna().unique())
            estado_sel = st.multiselect("Estado Conciliación", estados_disp, key="ctg_estado")
        with c2:
            # Banco del cobro (solo para conciliadas que tienen medio de cobro)
            if "Medio de Cobro" in df_det.columns:
                medios_disp = sorted(df_det["Medio de Cobro"].dropna().unique())
                medio_sel = st.multiselect("Medio de Cobro", medios_disp, key="ctg_medio")
            else:
                medio_sel = []
        with c3:
            if "Fecha Emision" in df_det.columns:
                # Intentar parsear fechas para rango
                try:
                    _fechas_parsed = pd.to_datetime(df_det["Fecha Emision"], format="%d/%m/%Y", errors="coerce")
                    _min_f = _fechas_parsed.dropna().min()
                    _max_f = _fechas_parsed.dropna().max()
                    if pd.notna(_min_f) and pd.notna(_max_f) and _min_f < _max_f:
                        rango_fecha = st.date_input(
                            "Rango Fecha Emisión",
                            value=(_min_f.date(), _max_f.date()),
                            min_value=_min_f.date(),
                            max_value=_max_f.date(),
                            key="ctg_fecha_rango",
                        )
                    else:
                        rango_fecha = None
                except Exception:
                    rango_fecha = None
            else:
                rango_fecha = None
        with c4:
            search_ctg = st.text_input("Buscar cliente / nro factura", key="ctg_search")

        # --- Aplicar filtros ---
        df_det_show = df_det.copy()
        if estado_sel:
            df_det_show = df_det_show[df_det_show["Estado Conciliacion"].isin(estado_sel)]
        if medio_sel and "Medio de Cobro" in df_det_show.columns:
            df_det_show = df_det_show[df_det_show["Medio de Cobro"].isin(medio_sel)]
        if rango_fecha and isinstance(rango_fecha, tuple) and len(rango_fecha) == 2:
            try:
                _fp = pd.to_datetime(df_det_show["Fecha Emision"], format="%d/%m/%Y", errors="coerce")
                df_det_show = df_det_show[
                    (_fp >= pd.Timestamp(rango_fecha[0])) & (_fp <= pd.Timestamp(rango_fecha[1]))
                ]
            except Exception:
                pass
        if search_ctg:
            mask = df_det_show.astype(str).apply(
                lambda x: x.str.contains(search_ctg, case=False, na=False)
            ).any(axis=1)
            df_det_show = df_det_show[mask]

        # --- Columnas a mostrar ---
        det_cols = [
            "Fecha Emision", "Cliente", "CUIT", "Nro Factura", "Total Venta",
            "Estado Conciliacion", "Cobrado", "Diferencia Venta-Cobro",
            "Medio de Cobro", "Estado",
        ]
        det_cols = [c for c in det_cols if c in df_det_show.columns]

        # --- Colorear filas ---
        df_det_disp = df_det_show[det_cols].copy().reset_index(drop=True)

        def _color_estado(row):
            if "Estado Conciliacion" in row.index:
                if row["Estado Conciliacion"] == "Conciliada":
                    return ["background-color: rgba(13, 124, 61, 0.12)"] * len(row)
                elif row["Estado Conciliacion"] == "Sin Match":
                    return ["background-color: rgba(227, 6, 19, 0.10)"] * len(row)
            return [""] * len(row)

        # Formatear montos
        for mc in ["Total Venta", "Cobrado", "Diferencia Venta-Cobro"]:
            if mc in df_det_disp.columns:
                df_det_disp[mc] = df_det_disp[mc].apply(
                    lambda x: f"$ {x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x
                )

        styled = df_det_disp.style.apply(_color_estado, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # --- Totales al pie ---
        total_facturado = df_det_show["Total Venta"].sum() if "Total Venta" in df_det_show.columns else 0
        total_cobrado = df_det_show["Cobrado"].sum() if "Cobrado" in df_det_show.columns else 0
        dif_neta = total_facturado - total_cobrado

        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("Total Facturado (visible)", format_money(total_facturado))
        tc2.metric("Total Cobrado (visible)", format_money(total_cobrado))
        tc3.metric("Diferencia Neta", format_money(dif_neta))
    else:
        st.info("Sin datos de facturas Contagram. Utilice la pestaña **Movimientos Banco**.")

# ── Tab 2: Movimientos Banco (tabla original) ──
with tab_banco:
    if not df_cobros.empty:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            banco_sel = st.multiselect("Banco", df_cobros["banco"].unique(), key="banco_sel_mov")
        with c2:
            niveles = df_cobros[match_col].astype(str).unique()
            nivel_sel = st.multiselect("Nivel Match", niveles, key="nivel_sel_mov")
        with c3:
            pass
        with c4:
            search = st.text_input("Buscar cliente/importe", key="search_mov")

        df_show = df_cobros.copy()
        if banco_sel:
            df_show = df_show[df_show["banco"].isin(banco_sel)]
        if nivel_sel:
            df_show = df_show[df_show[match_col].astype(str).isin(nivel_sel)]
        if search:
            df_show = df_show[df_show.astype(str).apply(
                lambda x: x.str.contains(search, case=False, na=False)
            ).any(axis=1)]

        cols = ["fecha", "banco", "descripcion", "nombre_contagram", "monto", "monto_factura", "diferencia_monto", match_col]
        cols = [c for c in cols if c in df_show.columns]

        df_disp = df_show[cols].copy()
        num_cols = ["monto", "monto_factura", "diferencia_monto"]
        for c in num_cols:
            if c in df_disp.columns:
                df_disp[c] = df_disp[c].apply(
                    lambda x: f"$ {x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x
                )

        st.dataframe(df_disp, use_container_width=True, hide_index=True)
        st.markdown(f"**Total visible: {format_money(df_show['monto'].sum())}**")
    else:
        st.info("Sin movimientos bancarios de tipo crédito.")


# ═══════════════════════════════════════════════════════
# SECCION D — Excepciones Banco (créditos sin identificar)
# ═══════════════════════════════════════════════════════
if not df_cobros.empty:
    # Filtrar créditos no_match / EXCLUDED
    _exc_mask = pd.Series(False, index=df_cobros.index)
    if "conciliation_status" in df_cobros.columns:
        _exc_mask = _exc_mask | (df_cobros["conciliation_status"] == "EXCLUDED")
    if match_col in df_cobros.columns:
        _exc_mask = _exc_mask | (df_cobros[match_col] == "no_match")

    df_exc_banco = df_cobros[_exc_mask].copy()

    if not df_exc_banco.empty:
        n_exc = len(df_exc_banco)
        monto_exc = df_exc_banco["monto"].sum()

        with st.expander(
            f"🔴 Movimientos Bancarios Sin Identificar — {n_exc} movimientos | {format_money(monto_exc)}",
            expanded=False,
        ):
            exc_cols = ["fecha", "banco", "descripcion", "cuit_banco", "nombre_contagram", "monto", "conciliation_tag", "match_detalle"]
            exc_cols = [c for c in exc_cols if c in df_exc_banco.columns]

            df_exc_disp = df_exc_banco[exc_cols].copy()
            if "monto" in df_exc_disp.columns:
                df_exc_disp["monto"] = df_exc_disp["monto"].apply(
                    lambda x: f"$ {x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x
                )

            st.dataframe(df_exc_disp.reset_index(drop=True), use_container_width=True, hide_index=True)

            st.info(
                "💡 Estos movimientos pueden ser cobros de clientes no registrados en Contagram, "
                "transferencias internas, o pagos de períodos anteriores. Revisarlos en "
                "Excepciones para agregar alias a la tabla paramétrica."
            )

from src.chatbot import render_chatbot_flotante
render_chatbot_flotante()