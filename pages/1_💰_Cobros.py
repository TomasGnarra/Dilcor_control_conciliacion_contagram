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
# SECCION A — KPIs (3 FILAS)
# ═══════════════════════════════════════════════════════
section_div("Panorama de Cobros", "📊")

# --- FILA 1: Banco vs Contagram ---
col_banco, col_sep, col_ctg = st.columns([5, 1, 5])

with col_banco:
    st.markdown("#### 🏦 Banco (Ingresos)")
    c1, c2 = st.columns(2)
    kpi_card("Créditos Bancarios", format_money(cb.get("monto_total", 0)),
             f"{cb.get('total', 0)} movimientos", "neutral", c1)
    
    monto_conciliado = cb.get("match_exacto_monto", 0)
    monto_pendiente = cb.get("monto_total", 0) - monto_conciliado
    kpi_card("Conciliado $", format_money(monto_conciliado),
             f"Pendiente: {format_money(monto_pendiente)}", "success", c2)

with col_sep:
    st.markdown("<div style='border-left: 2px solid #E30613; height: 160px; margin: 20px auto; width: 0;'></div>", unsafe_allow_html=True)

with col_ctg:
    st.markdown("#### 📋 Contagram (Ventas)")
    c1, c2 = st.columns(2)
    monto_ventas = stats.get("monto_ventas_contagram", 0)
    n_facturas = len(df_ventas) if not df_ventas.empty else 0
    kpi_card("Total Facturado", format_money(monto_ventas),
             f"{n_facturas} facturas emitidas", "neutral", c1)

    # Facturas pendientes (usar df_det si existe, sino estimar)
    if not df_det.empty and "Estado Conciliacion" in df_det.columns:
        pendientes = df_det[df_det["Estado Conciliacion"] != "Conciliada"]
        n_pend = len(pendientes)
        m_pend = pendientes["Total Venta"].sum() if "Total Venta" in pendientes.columns else 0
    else:
        n_pend = "N/D"
        m_pend = 0
    
    kpi_card("Facturas Pendientes", f"{n_pend}",
             f"Monto: {format_money(m_pend)}", "warning", c2)


# --- FILA 2: Desglose por nivel ---
st.markdown("###")
c1, c2, c3, c4 = st.columns(4)
kpi_card("Match Exacto", f"{cb.get('match_exacto', 0)} mov.",
         f"({cb.get('match_directo', 0)} dir + {cb.get('match_suma', 0)} suma)",
         "success", c1)
kpi_card("Duda de ID", f"{cb.get('probable_duda_id', 0)} mov.",
         format_money(cb.get("probable_duda_id_monto", 0)), "warning", c2)
kpi_card("Dif. de Cambio", f"{cb.get('probable_dif_cambio', 0)} mov.",
         format_money(cb.get("probable_dif_cambio_monto", 0)), "warning", c3)
kpi_card("Sin Identificar", f"{cb.get('no_match', 0)} mov.",
         format_money(cb.get("no_match_monto", 0)), "danger", c4)


# --- FILA 3: Métricas Contagram ---
st.markdown("###")
c1, c2, c3, c4 = st.columns([2, 2, 2, 2])

# Monto exacto (solo MATCHED)
monto_exacto = cb.get("match_exacto_monto", 0)
kpi_card("Conciliado Exacto $", format_money(monto_exacto),
         "Solo match exacto confirmado", "success", c1)

# Monto total identificado (exacto + probable)
monto_identificado = monto_exacto + cb.get("probable_duda_id_monto", 0)
kpi_card("Identificado Total $", format_money(monto_identificado),
         "Exacto + probable (duda de ID)", "warning", c2)

# Facturas Conciliadas
if not df_det.empty and "Estado Conciliacion" in df_det.columns:
    conciliadas = df_det[df_det["Estado Conciliacion"] == "Conciliada"]
    n_conc = len(conciliadas)
else:
    n_conc = 0
kpi_card("Facturas Conciliadas", f"{n_conc}",
         f"de {n_facturas} totales ({(n_conc/n_facturas*100):.1f}%)" if n_facturas > 0 else "Sin datos",
         "success" if n_facturas > 0 and n_conc / n_facturas >= 0.8 else "warning", c3)

# % Cobertura: dos sub-tarjetas dentro de c4
cobertura_exacto = (monto_exacto / monto_ventas * 100) if monto_ventas > 0 else 0
cobertura_total = (monto_identificado / monto_ventas * 100) if monto_ventas > 0 else 0

with c4:
    sub1, sub2 = st.columns(2)
    kpi_card("Cob. Exacta", f"{cobertura_exacto:.1f}%",
             format_money(monto_exacto), "danger", sub1)
    kpi_card("Cob. Total", f"{cobertura_total:.1f}%",
             format_money(monto_identificado), "warning", sub2)

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
# SECCION C — TABLA
# ═══════════════════════════════════════════════════════
st.markdown("###")
section_div("Detalle de Cobros", "📄")

if not df_cobros.empty:
    # Filtros
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        banco_sel = st.multiselect("Banco", df_cobros["banco"].unique())
    with c2:
        niveles = df_cobros[match_col].astype(str).unique()
        nivel_sel = st.multiselect("Nivel Match", niveles)
    with c3:
        # Date filter logic skipped for brevity, implementing basic
        pass
    with c4:
        search = st.text_input("Buscar cliente/importe")

    df_show = df_cobros.copy()
    if banco_sel: df_show = df_show[df_show["banco"].isin(banco_sel)]
    if nivel_sel: df_show = df_show[df_show[match_col].astype(str).isin(nivel_sel)]
    if search:
        df_show = df_show[df_show.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)]

    # Columns
    cols = ["fecha", "banco", "descripcion", "nombre_contagram", "monto", "monto_factura", "diferencia_monto", match_col]
    cols = [c for c in cols if c in df_show.columns]
    
    # Formatear
    df_disp = df_show[cols].copy()
    num_cols = ["monto", "monto_factura", "diferencia_monto"]
    for c in num_cols:
        if c in df_disp.columns:
            df_disp[c] = df_disp[c].apply(lambda x: f"$ {x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x)

    st.dataframe(
        df_disp, 
        use_container_width=True, hide_index=True
    )
    st.markdown(f"**Total visible: {format_money(df_show['monto'].sum())}**")
