"""
Pagina 2: Banco → Contagram
"¿Cada peso que entró/salió del banco tiene contraparte en Contagram?"
Perspectiva del extracto bancario: cada movimiento y su estado de conciliación.
"""
import streamlit as st
import pandas as pd
from src.ui.styles import load_css
from src.ui.components import (
    kpi_card, section_div, page_header, format_money,
    build_column_config, render_data_table, no_data_warning,
    donut_chart, alert_card,
)

load_css()

page_header(
    "Banco → Contagram",
    "Cada movimiento bancario y su estado de conciliación en Contagram",
    "🏦",
)

if "resultado" not in st.session_state:
    no_data_warning()
    st.stop()

resultado = st.session_state["resultado"]
stats = st.session_state["stats"]

# ═══════════════════════════════════════════════════════
# COBROS (Créditos)
# ═══════════════════════════════════════════════════════
cb = stats.get("cobros", {})
section_div(f"COBROS — {cb.get('total', 0)} movimientos ({cb.get('tasa_conciliacion', 0)}% conciliado)", "📥")

# Fila 1: Montos principales
c1, c2, c3 = st.columns(3)
kpi_card("Cobrado en Bancos", format_money(cb.get("monto_total", 0)), f"{cb.get('total', 0)} movimientos", "neutral", c1)
kpi_card("Facturado Contagram", format_money(stats.get("monto_ventas_contagram", 0)), "Ventas pendientes", "neutral", c2)

gap = stats.get("revenue_gap", 0)
gap_status = "success" if abs(gap) < 10000 else "danger"
kpi_card("Revenue Gap", format_money(gap), "Casi perfecto" if abs(gap) < 10000 else "Revisar diferencia", gap_status, c3)

# Fila 2: Desglose por nivel de match
st.markdown("###")
c1, c2, c3, c4 = st.columns(4)
kpi_card(
    "Match Exacto", f"{cb.get('match_exacto', 0)} mov.",
    f"{cb.get('match_directo', 0)} dir + {cb.get('match_suma', 0)} suma", "success", c1
)
kpi_card("Duda de ID", f"{cb.get('probable_duda_id', 0)} mov.", format_money(cb.get("probable_duda_id_monto", 0)), "warning", c2)
kpi_card("Dif. de Cambio", f"{cb.get('probable_dif_cambio', 0)} mov.", format_money(cb.get("probable_dif_cambio_monto", 0)), "warning", c3)
kpi_card("Sin Identificar", f"{cb.get('no_match', 0)} mov.", format_money(cb.get("no_match_monto", 0)), "danger", c4)

# Fila 3: Flujo conciliado vs pendiente
st.markdown("###")
c1, c2, c3 = st.columns(3)
mt = max(cb.get("monto_total", 1), 1)
pct_conc = round(cb.get("match_exacto_monto", 0) / mt * 100, 1)
pct_ident = round((cb.get("probable_dif_cambio_monto", 0) + cb.get("probable_duda_id_monto", 0)) / mt * 100, 1)
pct_sin = round(cb.get("no_match_monto", 0) / mt * 100, 1)

kpi_card("Conciliado 100%", format_money(cb.get("match_exacto_monto", 0)), f"{pct_conc}% del total", "success", c1)
kpi_card("Identificado", format_money(cb.get("probable_dif_cambio_monto", 0) + cb.get("probable_duda_id_monto", 0)), f"{pct_ident}% (asignar)", "warning", c2)
kpi_card("Sin Identificar", format_money(cb.get("no_match_monto", 0)), f"{pct_sin}% match manual", "danger", c3)

# Fila 4: Tipo de match + Diferencias
st.markdown("###")
c1, c2, c3, c4 = st.columns(4)
kpi_card("Match Directo (1:1)", f"{cb.get('match_directo', 0)} mov", format_money(cb.get("match_directo_monto", 0)), "success", c1)
kpi_card("Match Suma", f"{cb.get('match_suma', 0)} mov", format_money(cb.get("match_suma_monto", 0)), "success", c2)
kpi_card("Cobrado de Más", format_money(cb.get("de_mas", 0)), "Cliente pagó de más", "warning", c3)
diff_st = "success" if cb.get("diferencia_neta", 0) >= 0 else "danger"
kpi_card("Cobrado de Menos", format_money(cb.get("de_menos", 0)), "Cliente pagó de menos", diff_st, c4)


# ═══════════════════════════════════════════════════════
# PAGOS A PROVEEDORES (Débitos)
# ═══════════════════════════════════════════════════════
pg = stats.get("pagos_prov", {})
section_div(f"PAGOS A PROVEEDORES — {pg.get('total', 0)} movimientos ({pg.get('tasa_conciliacion', 0)}%)", "📤")

c1, c2, c3 = st.columns(3)
kpi_card("Pagado en Bancos", format_money(pg.get("monto_total", 0)), f"{pg.get('total', 0)} pagos", "neutral", c1)
kpi_card("OCs en Contagram", format_money(stats.get("monto_compras_contagram", 0)), "OC registradas", "neutral", c2)

pgap = stats.get("payment_gap", 0)
pgap_st = "success" if abs(pgap) < 10000 else "danger"
kpi_card("Payment Gap", format_money(pgap), "Alineado" if abs(pgap) < 10000 else "Revisar diferencia", pgap_st, c3)

st.markdown("###")
c1, c2, c3, c4 = st.columns(4)
kpi_card("Match Exacto", f"{pg.get('match_exacto', 0)} mov.", f"{pg.get('match_directo', 0)} dir + {pg.get('match_suma', 0)} suma", "success", c1)
kpi_card("Duda de ID", f"{pg.get('probable_duda_id', 0)} mov.", format_money(pg.get("probable_duda_id_monto", 0)), "warning", c2)
kpi_card("Dif. de Cambio", f"{pg.get('probable_dif_cambio', 0)} mov.", format_money(pg.get("probable_dif_cambio_monto", 0)), "warning", c3)
kpi_card("Sin Identificar", f"{pg.get('no_match', 0)} mov.", format_money(pg.get("no_match_monto", 0)), "danger", c4)

st.markdown("###")
c1, c2, c3 = st.columns(3)
pmt = max(pg.get("monto_total", 1), 1)
pct_pg_conc = round(pg.get("match_exacto_monto", 0) / pmt * 100, 1)
pct_pg_ident = round((pg.get("probable_dif_cambio_monto", 0) + pg.get("probable_duda_id_monto", 0)) / pmt * 100, 1)
pct_pg_sin = round(pg.get("no_match_monto", 0) / pmt * 100, 1)

kpi_card("Conciliado 100%", format_money(pg.get("match_exacto_monto", 0)), f"{pct_pg_conc}% del total", "success", c1)
kpi_card("Identificado", format_money(pg.get("probable_dif_cambio_monto", 0) + pg.get("probable_duda_id_monto", 0)), f"{pct_pg_ident}% (asignar OC)", "warning", c2)
kpi_card("Sin Identificar", format_money(pg.get("no_match_monto", 0)), f"{pct_pg_sin}% match manual", "danger", c3)

st.markdown("###")
c1, c2, c3, c4 = st.columns(4)
kpi_card("Match Directo", f"{pg.get('match_directo', 0)} mov", format_money(pg.get("match_directo_monto", 0)), "success", c1)
kpi_card("Match Suma", f"{pg.get('match_suma', 0)} mov", format_money(pg.get("match_suma_monto", 0)), "success", c2)
kpi_card("Pagado de Más", format_money(pg.get("de_mas", 0)), "Pagado > OC", "warning", c3)
dpg_st = "success" if pg.get("diferencia_neta", 0) >= 0 else "danger"
kpi_card("Pagado de Menos", format_money(pg.get("de_menos", 0)), "Pagado < OC", dpg_st, c4)


# ═══════════════════════════════════════════════════════
# GASTOS BANCARIOS
# ═══════════════════════════════════════════════════════
section_div("GASTOS BANCARIOS", "🏦")
c1, c2 = st.columns([2, 1])
kpi_card("Total Gastos (Comisiones, Impuestos)", format_money(stats.get("monto_gastos_bancarios", 0)), "No se concilian en Contagram", "neutral", c1)
kpi_card("Cantidad Movimientos", f"{stats.get('gastos_bancarios', 0)}", "Solo informativo", "neutral", c2)


# ═══════════════════════════════════════════════════════
# RESUMEN POR BANCO
# ═══════════════════════════════════════════════════════
section_div("Resumen por Banco", "🏛️")
for banco, data in stats.get("por_banco", {}).items():
    with st.expander(f"{banco} — {data['movimientos']} movimientos"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Match Exacto", data["match_exacto"])
        c2.metric("Duda de ID", data["probable_duda_id"])
        c3.metric("Dif. Cambio", data["probable_dif_cambio"])
        c4.metric("Sin Match", data["no_match"])
        st.caption(f"Créditos: {format_money(data['monto_creditos'])} | Débitos: {format_money(data['monto_debitos'])}")


# ═══════════════════════════════════════════════════════
# DETALLE COMPLETO
# ═══════════════════════════════════════════════════════
section_div("Detalle Completo de Movimientos", "📄")

df_full = resultado.get("resultados", pd.DataFrame())
if not df_full.empty:
    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        if "banco" in df_full.columns:
            bancos = ["Todos"] + sorted(df_full["banco"].dropna().unique().tolist())
            banco_sel = st.selectbox("Banco", bancos, key="detalle_banco")
        else:
            banco_sel = "Todos"

    with col_f2:
        if "clasificacion" in df_full.columns:
            clasifs = ["Todos"] + sorted(df_full["clasificacion"].dropna().unique().tolist())
            clasif_sel = st.selectbox("Clasificación", clasifs, key="detalle_clasif")
        else:
            clasif_sel = "Todos"

    with col_f3:
        # Filtro por nivel de match
        match_col = None
        for c in ["match_nivel", "conciliation_status"]:
            if c in df_full.columns:
                match_col = c
                break
        if match_col:
            niveles = ["Todos"] + sorted([str(n) for n in df_full[match_col].dropna().unique()])
            nivel_sel = st.selectbox("Nivel Match", niveles, key="detalle_nivel")
        else:
            nivel_sel = "Todos"

    # Buscador general
    busqueda = st.text_input("🔍 Buscar (Descripción, Referencia, CUIT, Importe...)", placeholder="Escribe para filtrar...", key="search_banco_gral")

    df_filtered = df_full.copy()

    # Filtros de selectbox
    if banco_sel != "Todos" and "banco" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["banco"] == banco_sel]
    if clasif_sel != "Todos" and "clasificacion" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["clasificacion"] == clasif_sel]
    if nivel_sel != "Todos" and match_col:
        df_filtered = df_filtered[df_filtered[match_col].astype(str) == nivel_sel]

    # Filtro de texto
    if busqueda:
        term = busqueda.lower()
        mask = pd.Series(False, index=df_filtered.index)
        # Buscar en columnas de texto principales
        cols_msg = [c for c in df_filtered.columns if df_filtered[c].dtype == object]
        for c in cols_msg:
             mask |= df_filtered[c].fillna("").astype(str).str.lower().str.contains(term, na=False)
        # Tambien buscar en montos (convertidos a string)
        if "monto" in df_filtered.columns:
             mask |= df_filtered["monto"].astype(str).str.contains(term, na=False)
        df_filtered = df_filtered[mask]

    # Ordenar columnas prioritarias
    if st.session_state.get("modo_real"):
        priority_cols = [
            "fecha", "banco", "tipo", "clasificacion", "descripcion",
            "monto", "cuit_banco", "nombre_banco_extraido",
            "conciliation_status", "conciliation_tag",
            "conciliation_confidence", "conciliation_reason",
            "nombre_contagram", "factura_match", "diferencia_monto",
            "tipo_match_monto", "facturas_count",
        ]
    else:
        priority_cols = [
            "fecha", "banco", "tipo", "clasificacion", "descripcion",
            "monto", "match_nivel", "tipo_match_monto", "facturas_count",
            "match_detalle", "confianza",
            "nombre_contagram", "factura_match", "diferencia_monto",
        ]

    ordered_cols = [c for c in priority_cols if c in df_filtered.columns]
    remaining_cols = [c for c in df_filtered.columns if c not in ordered_cols]
    all_cols = ordered_cols + remaining_cols

    st.dataframe(
        df_filtered[all_cols],
        use_container_width=True,
        hide_index=True,
        column_config=build_column_config(df_filtered[all_cols]),
    )
    st.caption(f"Mostrando {len(df_filtered)} de {len(df_full)} movimientos")
else:
    st.info("Sin datos de detalle disponibles.")


# ═══════════════════════════════════════════════════════
# ALERTAS Y PATRONES
# ═══════════════════════════════════════════════════════
df_full_alertas = resultado.get("resultados", pd.DataFrame())
alertas_banco = []

if not df_full_alertas.empty:
    # Detectar columna de match
    _mc = None
    for _c in ["match_nivel", "conciliation_status"]:
        if _c in df_full_alertas.columns:
            _mc = _c
            break

    # Movimientos sin match
    if _mc:
        df_sin = df_full_alertas[df_full_alertas[_mc].astype(str).str.lower().isin(["sin match", "no_match", "sin_match"])]
    else:
        df_sin = pd.DataFrame()

    # 1. Top descripciones recurrentes sin match
    if not df_sin.empty and "descripcion" in df_sin.columns:
        top_desc = df_sin["descripcion"].value_counts().head(5)
        if len(top_desc) > 0:
            desc_lines = [f"• **{desc}**: {cnt} veces" for desc, cnt in top_desc.items()]
            alertas_banco.append((
                "Top Descripciones Sin Match (Banco)",
                "Estas descripciones bancarias aparecen repetidamente sin ser identificadas. "
                "Considere agregarlas a la tabla paramétrica como alias.\n" + "\n".join(desc_lines),
                "warning"
            ))

    # 2. Movimientos grandes sin match
    monto_col_full = "monto" if "monto" in df_sin.columns else "Monto" if "Monto" in df_sin.columns else None
    if not df_sin.empty and monto_col_full:
        df_grandes = df_sin.nlargest(3, monto_col_full)
        if len(df_grandes) > 0 and df_grandes[monto_col_full].iloc[0] > 50000:
            lines = [f"• {format_money(row[monto_col_full])} — {row.get('descripcion', 'N/A')}" for _, row in df_grandes.iterrows()]
            alertas_banco.append((
                "Movimientos Grandes Sin Identificar",
                "Estos movimientos tienen montos significativos y no fueron conciliados:\n" + "\n".join(lines),
                "danger"
            ))

    # 3. Concentración de excepciones por fecha
    if not df_sin.empty and "fecha" in df_sin.columns:
        try:
            fechas = pd.to_datetime(df_sin["fecha"], errors="coerce")
            if fechas.notna().sum() > 0:
                top_fecha = fechas.dt.date.value_counts().head(3)
                if top_fecha.iloc[0] >= 5:
                    fecha_lines = [f"• {f}: {c} movimientos" for f, c in top_fecha.items()]
                    alertas_banco.append((
                        "Concentración por Fecha",
                        "Varias excepciones se concentran en pocas fechas. Revise si hubo un evento puntual:\n" + "\n".join(fecha_lines),
                        "info"
                    ))
        except Exception:
            pass

    # 4. Gastos bancarios elevados
    gastos_total = stats.get("monto_gastos_bancarios", 0)
    monto_total_banco = stats.get("monto_total_banco", 0)
    if monto_total_banco > 0 and gastos_total / max(monto_total_banco, 1) > 0.02:
        alertas_banco.append((
            "Gastos Bancarios Elevados",
            f"Los gastos bancarios ({format_money(gastos_total)}) representan más del 2% del volumen total. Revise comisiones.",
            "warning"
        ))

if alertas_banco:
    section_div("Alertas y Patrones", "🔔")
    for title, msg, sev in alertas_banco:
        alert_card(title, msg, sev)
