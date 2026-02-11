"""
DILCOR - Sistema de Conciliacion Bancaria con Contagram
MVP Opcion A - Interfaz Streamlit
Branding: Negro (#1A1A1A) / Rojo (#E30613) / Blanco (#FFFFFF)
"""
import streamlit as st
import pandas as pd
import os
import io
from src.motor_conciliacion import MotorConciliacion
from src.matcher import MATCH_CONFIG
from src.ui.styles import load_css, render_header
from src.ui.components import kpi_card, section_div, format_money, build_column_config

# --- Configuracion de pagina ---
st.set_page_config(
    page_title="Dilcor - Conciliacion Bancaria",
    page_icon="https://img.icons8.com/fluency/48/bank-building.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Branding Dilcor: Negro / Rojo / Blanco ---
# --- Branding Dilcor ---
load_css()
render_header()

# --- Sidebar ---
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0;">
        <div style="font-size:2rem; font-weight:800; color:#FFF; letter-spacing:2px;">
            D<span style="color:#E30613;">i</span>lcor
        </div>
        <div style="font-size:0.65rem; color:#999; letter-spacing:4px; text-transform:uppercase;">
            Distribuidora Mayorista
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    modo = st.radio(
        "Modo de operacion",
        ["Demo (datos de prueba)", "Manual (subir archivos)"],
        index=0,
    )

    st.markdown("---")
    st.markdown("**Bancos soportados**")
    st.caption("Banco Galicia | Banco Santander | Mercado Pago")

    # --- Umbrales configurables ---
    st.markdown("---")
    with st.expander("Ajustar umbrales de matching"):
        niveles_umbral = {
            1: {
                "etiqueta": "Muy estricto",
                "tol_exacto_pct": 0.2,
                "tol_probable_pct": 0.5,
                "tol_probable_abs": 250,
                "umbral_id_exacto_pct": 92,
                "umbral_id_probable_pct": 70,
                "descripcion": "Maxima exactitud: menos falsos positivos, pero mas casos pendientes.",
            },
            2: {
                "etiqueta": "Estricto",
                "tol_exacto_pct": 0.3,
                "tol_probable_pct": 0.8,
                "tol_probable_abs": 300,
                "umbral_id_exacto_pct": 88,
                "umbral_id_probable_pct": 65,
                "descripcion": "Conservador: exige bastante similitud y tolera poca diferencia de monto.",
            },
            3: {
                "etiqueta": "Balanceado (recomendado)",
                "tol_exacto_pct": 0.5,
                "tol_probable_pct": 1.0,
                "tol_probable_abs": 500,
                "umbral_id_exacto_pct": 80,
                "umbral_id_probable_pct": 55,
                "descripcion": "Equilibrio entre precision y cobertura para operacion diaria.",
            },
            4: {
                "etiqueta": "Flexible",
                "tol_exacto_pct": 0.8,
                "tol_probable_pct": 1.5,
                "tol_probable_abs": 800,
                "umbral_id_exacto_pct": 77,
                "umbral_id_probable_pct": 50,
                "descripcion": "Acepta mas variaciones: reduce pendientes, pero requiere revision.",
            },
            5: {
                "etiqueta": "Muy flexible",
                "tol_exacto_pct": 1.0,
                "tol_probable_pct": 2.0,
                "tol_probable_abs": 1000,
                "umbral_id_exacto_pct": 75,
                "umbral_id_probable_pct": 45,
                "descripcion": "Maxima cobertura: mas coincidencias con mayor control manual.",
            },
        }

        nivel_umbral = st.slider(
            "Filtro deslizante de umbral",
            min_value=1,
            max_value=5,
            value=3,
            step=1,
            help="Izquierda: mas estricto. Derecha: mas flexible.",
        )
        cfg_umbral = niveles_umbral[nivel_umbral]

        st.caption("1 = Muy estricto · 3 = Balanceado · 5 = Muy flexible")

        st.markdown('<div class="threshold-panel">', unsafe_allow_html=True)
        st.markdown(f'<div class="threshold-title">Nivel actual: {cfg_umbral["etiqueta"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="threshold-help">{cfg_umbral["descripcion"]}</div>', unsafe_allow_html=True)
        st.caption("Si lo moves a la izquierda: menos matches y mas precision. A la derecha: mas matches y mas revision manual.")
        st.markdown('</div>', unsafe_allow_html=True)

        tol_exacto = cfg_umbral["tol_exacto_pct"] / 100
        tol_probable_pct = cfg_umbral["tol_probable_pct"] / 100
        tol_probable_abs = cfg_umbral["tol_probable_abs"]
        umbral_id_exacto = cfg_umbral["umbral_id_exacto_pct"] / 100
        umbral_id_probable = cfg_umbral["umbral_id_probable_pct"] / 100

    match_config_override = {
        "tolerancia_monto_exacto_pct": tol_exacto,
        "tolerancia_monto_probable_pct": tol_probable_pct,
        "tolerancia_monto_probable_abs": float(tol_probable_abs),
        "umbral_id_exacto": umbral_id_exacto,
        "umbral_id_probable": umbral_id_probable,
    }

    st.markdown("---")
    st.caption("Dilcor v3.0 MVP | 2025")


# --- Helpers ---



def load_demo_data():
    base = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base, "data")
    extractos = []
    for fname in ["extracto_galicia_dic2025.csv", "extracto_santander_dic2025.csv", "extracto_mercadopago_dic2025.csv"]:
        path = os.path.join(data_dir, "test", fname)
        if os.path.exists(path):
            extractos.append(pd.read_csv(path))
    ventas = pd.read_csv(os.path.join(data_dir, "contagram", "ventas_pendientes_dic2025.csv"))
    compras = pd.read_csv(os.path.join(data_dir, "contagram", "compras_pendientes_dic2025.csv"))
    tabla_param = pd.read_csv(os.path.join(data_dir, "config", "tabla_parametrica.csv"))
    return extractos, ventas, compras, tabla_param


def _leer_archivo(uploaded_file):
    """Lee CSV o XLSX segun extension."""
    if uploaded_file is None:
        return pd.DataFrame()
    name = uploaded_file.name.lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    return pd.read_csv(uploaded_file)


def load_manual_data():
    """Interfaz con tabs por banco para subir archivos (CSV + XLSX)."""
    st.markdown("### Cargar Archivos")
    tab_banco, tab_ctg = st.tabs(["Extracto Bancario", "Ventas Contagram"])

    extractos = []
    with tab_banco:
        st.markdown("**Extracto bancario** — Soporta Galicia, Santander, Mercado Pago (CSV o XLSX)")
        f_bancos = st.file_uploader(
            "Subir extracto(s) bancario(s)",
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=True,
            key="extractos",
        )
        if f_bancos:
            for f in f_bancos:
                df = _leer_archivo(f)
                extractos.append(df)
                st.success(f"{f.name}: {len(df)} filas cargadas")

    ventas = pd.DataFrame()
    with tab_ctg:
        st.markdown("**Ventas de Contagram** — Listado de ventas con Cliente, CUIT, Cobrado, Medio de Cobro")
        uploaded_ventas = st.file_uploader("Subir ventas (CSV o XLSX)", type=["csv", "xlsx", "xls"], key="ventas")
        if uploaded_ventas:
            ventas = _leer_archivo(uploaded_ventas)
            st.success(f"{uploaded_ventas.name}: {len(ventas)} ventas cargadas")

            # Validar columnas requeridas
            cols = [c.lower().strip() for c in ventas.columns]
            cols_requeridas = {"cliente", "cobrado"}
            cols_encontradas = {c for c in cols_requeridas if c in cols}
            if cols_encontradas != cols_requeridas:
                faltantes = cols_requeridas - cols_encontradas
                st.warning(f"Columnas faltantes en ventas: {', '.join(faltantes)}. Se usara formato disponible.")

    return extractos, ventas


# --- Carga de datos ---
if modo == "Demo (datos de prueba)":
    extractos, ventas, compras, tabla_param = load_demo_data()
    data_ready = len(extractos) > 0
    modo_real = False
else:
    extractos, ventas = load_manual_data()
    compras = pd.DataFrame()
    tabla_param = pd.DataFrame()
    # Detectar si es datos reales (Contagram con Medio de Cobro) o test
    cols_ventas = [c.lower().strip() for c in ventas.columns] if not ventas.empty else []
    modo_real = "cobrado" in cols_ventas or "medio de cobro" in cols_ventas
    data_ready = len(extractos) > 0 and not ventas.empty


# --- Ejecucion ---
if data_ready:
    if st.button("Ejecutar Conciliacion", type="primary", use_container_width=True):
        with st.spinner("Procesando conciliacion bancaria..."):
            if modo_real:
                motor = MotorConciliacion(pd.DataFrame())
                resultado = motor.procesar_real(extractos, ventas, match_config=match_config_override)
            else:
                motor = MotorConciliacion(tabla_param)
                resultado = motor.procesar(extractos, ventas, compras, match_config=match_config_override)
            st.session_state["resultado"] = resultado
            st.session_state["stats"] = motor.stats
            st.session_state["modo_real"] = modo_real

    if "resultado" in st.session_state:
        resultado = st.session_state["resultado"]
        stats = st.session_state["stats"]

        # ═══ DASHBOARD PRINCIPAL ═══
        st.markdown("---")

        # --- Resumen General ---
        c1, c2, c3, c4, c5 = st.columns(5)
        kpi_card("Total Movimientos", stats["total_movimientos"], status="neutral", col=c1)
        kpi_card("Conciliacion Total", f"{stats['tasa_conciliacion_total']}%", status="success", col=c2)
        kpi_card("Match Exacto", stats["match_exacto"], status="success", col=c3)
        kpi_card("Requieren Revision", stats["probable_duda_id"] + stats["probable_dif_cambio"], status="warning", col=c4)
        kpi_card("Sin Identificar", stats["no_match"], status="danger", col=c5)

        # ═══════════════════════════════════════════════════════
        # BLOQUE 1: COBROS (Creditos / Ventas)
        # ═══════════════════════════════════════════════════════
        # ═══════════════════════════════════════════════════════
        # BLOQUE 1: COBROS (Creditos / Ventas)
        # ═══════════════════════════════════════════════════════
        cb = stats["cobros"]
        section_div(f"COBROS — {cb['total']} movimientos ({cb['tasa_conciliacion']}%)", "📥")

        # Fila 1: Montos principales
        c1, c2, c3 = st.columns(3)
        kpi_card("Cobrado en Bancos", format_money(cb['monto_total']), f"{cb['total']} movimientos", "neutral", c1)
        kpi_card("Facturado en Contagram", format_money(stats['monto_ventas_contagram']), "Ventas pendientes", "neutral", c2)
        
        gap_status = "success" if abs(stats['revenue_gap']) < 10000 else "danger"
        gap_msg = "Casi perfecto" if abs(stats['revenue_gap']) < 10000 else "Revisar diferencia"
        kpi_card("Revenue Gap", format_money(stats['revenue_gap']), gap_msg, gap_status, c3)

        # Fila 2: Desglose por nivel de match
        st.markdown("###")
        c1, c2, c3, c4 = st.columns(4)
        kpi_card("Match Exacto", f"{cb['match_exacto']} mov.", f"{cb['match_directo']} dir + {cb['match_suma']} suma", "success", c1)
        kpi_card("Duda de ID", f"{cb['probable_duda_id']} mov.", format_money(cb['probable_duda_id_monto']), "warning", c2)
        kpi_card("Dif. de Cambio", f"{cb['probable_dif_cambio']} mov.", format_money(cb['probable_dif_cambio_monto']), "warning", c3)
        kpi_card("Sin Identificar", f"{cb['no_match']} mov.", format_money(cb['no_match_monto']), "danger", c4)

        # Fila 3: Flujo (Conciliado vs Pendiente)
        st.markdown("###")
        c1, c2, c3 = st.columns(3)
        pct_conciliado = round(cb['match_exacto_monto'] / max(cb['monto_total'], 1) * 100, 1)
        pct_identificado = round((cb['probable_dif_cambio_monto'] + cb['probable_duda_id_monto']) / max(cb['monto_total'], 1) * 100, 1)
        pct_sin_id = round(cb['no_match_monto'] / max(cb['monto_total'], 1) * 100, 1)
        
        kpi_card("Conciliado 100%", format_money(cb['match_exacto_monto']), f"{pct_conciliado}% del total", "success", c1)
        kpi_card("Identificado", format_money(cb['probable_dif_cambio_monto'] + cb['probable_duda_id_monto']), f"{pct_identificado}% (asignar)", "warning", c2)
        kpi_card("Sin Identificar", format_money(cb['no_match_monto']), f"{pct_sin_id}% match manual", "danger", c3)
        
        # Fila 4: Diferencias (Mas / Menos)
        st.markdown("###")
        c1, c2, c3, c4 = st.columns(4)
        kpi_card("Match Directo (1:1)", f"{cb['match_directo']} mov", format_money(cb['match_directo_monto']), "success", c1)
        kpi_card("Match Suma", f"{cb['match_suma']} mov", format_money(cb['match_suma_monto']), "success", c2)
        kpi_card("Cobrado de Más", format_money(cb['de_mas']), "Cliente pagó de más", "warning", c3)
        
        diff_status = "success" if cb['diferencia_neta'] >= 0 else "danger"
        kpi_card("Cobrado de Menos", format_money(cb['de_menos']), "Cliente pagó de menos", diff_status, c4)

        # ═══════════════════════════════════════════════════════
        # BLOQUE 2: PAGOS A PROVEEDORES (Debitos)
        # ═══════════════════════════════════════════════════════
        # ═══════════════════════════════════════════════════════
        # BLOQUE 2: PAGOS A PROVEEDORES (Debitos)
        # ═══════════════════════════════════════════════════════
        pg = stats["pagos_prov"]
        section_div(f"PAGOS A PROVEEDORES — {pg['total']} movimientos ({pg['tasa_conciliacion']}%)", "📤")

        # Fila 1: Montos principales
        c1, c2, c3 = st.columns(3)
        kpi_card("Pagado en Bancos", format_money(pg['monto_total']), f"{pg['total']} pagos", "neutral", c1)
        kpi_card("OCs en Contagram", format_money(stats['monto_compras_contagram']), "OC registradas", "neutral", c2)
        
        gap_p_status = "success" if abs(stats['payment_gap']) < 10000 else "danger"
        gap_p_msg = "Alineado" if abs(stats['payment_gap']) < 10000 else "Revisar diferencia"
        kpi_card("Payment Gap", format_money(stats['payment_gap']), gap_p_msg, gap_p_status, c3)

        # Fila 2: Desglose por nivel
        st.markdown("###")
        c1, c2, c3, c4 = st.columns(4)
        kpi_card("Match Exacto", f"{pg['match_exacto']} mov.", f"{pg['match_directo']} dir + {pg['match_suma']} suma", "success", c1)
        kpi_card("Duda de ID", f"{pg['probable_duda_id']} mov.", format_money(pg['probable_duda_id_monto']), "warning", c2)
        kpi_card("Dif. de Cambio", f"{pg['probable_dif_cambio']} mov.", format_money(pg['probable_dif_cambio_monto']), "warning", c3)
        kpi_card("Sin Identificar", f"{pg['no_match']} mov.", format_money(pg['no_match_monto']), "danger", c4)

        # Fila 3: Resumen de flujo
        st.markdown("###")
        c1, c2, c3 = st.columns(3)
        pct_pg_conc = round(pg['match_exacto_monto'] / max(pg['monto_total'], 1) * 100, 1)
        pct_pg_ident = round((pg['probable_dif_cambio_monto'] + pg['probable_duda_id_monto']) / max(pg['monto_total'], 1) * 100, 1)
        pct_pg_sin = round(pg['no_match_monto'] / max(pg['monto_total'], 1) * 100, 1)
        
        kpi_card("Conciliado 100%", format_money(pg['match_exacto_monto']), f"{pct_pg_conc}% del total", "success", c1)
        kpi_card("Identificado", format_money(pg['probable_dif_cambio_monto'] + pg['probable_duda_id_monto']), f"{pct_pg_ident}% (asignar OC)", "warning", c2)
        kpi_card("Sin Identificar", format_money(pg['no_match_monto']), f"{pct_pg_sin}% match manual", "danger", c3)
        
        # Fila 4: Pagado de mas / de menos
        st.markdown("###")
        c1, c2, c3, c4 = st.columns(4)
        kpi_card("Match Directo", f"{pg['match_directo']} mov", format_money(pg['match_directo_monto']), "success", c1)
        kpi_card("Match Suma", f"{pg['match_suma']} mov", format_money(pg['match_suma_monto']), "success", c2)
        kpi_card("Pagado de Más", format_money(pg['de_mas']), "Pagado > OC", "warning", c3)
        
        diff_pg_status = "success" if pg['diferencia_neta'] >= 0 else "danger"
        kpi_card("Pagado de Menos", format_money(pg['de_menos']), "Pagado < OC", diff_pg_status, c4)

        # ═══════════════════════════════════════════════════════
        # GASTOS BANCARIOS
        # ═══════════════════════════════════════════════════════
        section_div("GASTOS BANCARIOS", "🏦")
        c1, c2 = st.columns([2, 1])
        kpi_card("Total Gastos (Comisiones, Impuestos)", format_money(stats['monto_gastos_bancarios']), "No se concilian en Contagram", "neutral", c1)
        kpi_card("Cantidad Movimientos", f"{stats['gastos_bancarios']}", "Solo informativo", "neutral", c2)

        # ═══ ANÁLISIS DE CONTAGRAM ═══
        if "detalle_facturas" in resultado:
            df_det = resultado["detalle_facturas"]
            if not df_det.empty:
                section_div("ANÁLISIS DE CONTAGRAM", "📈")
                
                # KPIs Generales
                total_facturado = df_det["Total Venta"].sum() if "Total Venta" in df_det.columns else 0
                total_cobrado = df_det["Cobrado"].sum() if "Cobrado" in df_det.columns else 0
                pendiente = total_facturado - total_cobrado
                
                conciliado = df_det[df_det["Estado Conciliacion"] == "Conciliada"]["Cobrado"].sum() if "Cobrado" in df_det.columns else 0
                sin_match = df_det[df_det["Estado Conciliacion"] == "Sin Match"]["Cobrado"].sum() if "Cobrado" in df_det.columns else 0
                pct_conciliacion = (conciliado / total_cobrado * 100) if total_cobrado > 0 else 0

                c1, c2, c3 = st.columns(3)
                kpi_card("Total Facturado", format_money(total_facturado), "Ventas brutas Contagram", "neutral", c1)
                kpi_card("Total Cobrado", format_money(total_cobrado), f"Pendiente: {format_money(pendiente)}", "neutral", c2)
                kpi_card("% Conciliación Bancaria", f"{pct_conciliacion:.1f}%", f"Sin Match: {format_money(sin_match)}", "alert" if pct_conciliacion < 90 else "success", c3)

                # Grafico por Medio de Cobro
                st.markdown("##### 📊 Cobros por Medio de Pago")
                if "Medio de Cobro" in df_det.columns and "Cobrado" in df_det.columns:
                    chart_data = df_det.groupby("Medio de Cobro")["Cobrado"].sum().sort_values(ascending=False)
                    st.bar_chart(chart_data, color="#ff4b4b")

        # ═══ TABS DE DETALLE ═══
        st.markdown("---")
        tab_names = ["Por Banco", "Cobranzas", "Pagos", "Excepciones", "Detalle Completo"]
        if st.session_state.get("modo_real") and "detalle_facturas" in resultado:
            tab_names.append("🔍 Auditoría Facturas")
        tabs = st.tabs(tab_names)
        tab1, tab2, tab3, tab4, tab5 = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4]
        tab6 = tabs[5] if len(tabs) > 5 else None

        with tab1:
            st.markdown("### Resumen por Banco")
            for banco, data in stats["por_banco"].items():
                with st.expander(f"{banco} - {data['movimientos']} movimientos"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Match Exacto", data["match_exacto"])
                    c2.metric("Duda de ID", data["probable_duda_id"])
                    c3.metric("Dif. Cambio", data["probable_dif_cambio"])
                    c4.metric("Sin Match", data["no_match"])
                    st.caption(f"Creditos: {format_money(data['monto_creditos'])} | Debitos: {format_money(data['monto_debitos'])}")

        with tab2:
            st.markdown("### Cobranzas - Para importar en Contagram")
            df_cob = resultado["cobranzas_csv"]
            if not df_cob.empty:
                # Filtros adaptativos segun modo
                col1, col2 = st.columns(2)
                with col1:
                    if "Status" in df_cob.columns:
                        niveles = [n for n in df_cob["Status"].unique() if pd.notna(n)]
                        filtro_nivel = st.multiselect("Filtrar por status", niveles, default=niveles, key="f_cob")
                        df_f = df_cob[df_cob["Status"].isin(filtro_nivel)]
                    elif "Nivel Match" in df_cob.columns:
                        niveles = [n for n in df_cob["Nivel Match"].unique() if pd.notna(n)]
                        filtro_nivel = st.multiselect("Filtrar por nivel", niveles, default=niveles, key="f_cob")
                        df_f = df_cob[df_cob["Nivel Match"].isin(filtro_nivel)]
                    else:
                        df_f = df_cob
                with col2:
                    banco_col = "Banco" if "Banco" in df_cob.columns else "Banco Origen"
                    if banco_col in df_cob.columns:
                        bancos = df_cob[banco_col].unique().tolist()
                        filtro_banco = st.multiselect("Filtrar por banco", bancos, default=bancos, key="fb_cob")
                        df_f = df_f[df_f[banco_col].isin(filtro_banco)]

                st.dataframe(
                    df_f,
                    use_container_width=True,
                    hide_index=True,
                    column_config=build_column_config(df_f),
                )
                st.markdown(f"**Total: {len(df_f)} cobranzas | {format_money(df_f['Monto Cobrado'].sum())}**")

                st.download_button(
                    "📥 Descargar Cobranzas Conciliadas",
                    df_f.to_csv(index=False).encode("utf-8-sig"),
                    "cobranzas_conciliadas.csv", "text/csv",
                    use_container_width=True,
                    type="primary")
            else:
                st.info("Sin cobranzas conciliadas.")

        with tab3:
            st.markdown("### Pagos a Proveedores - Para importar en Contagram")
            df_pag = resultado["pagos_csv"]
            if not df_pag.empty:
                st.dataframe(
                    df_pag,
                    use_container_width=True,
                    hide_index=True,
                    column_config=build_column_config(df_pag),
                )
                st.markdown(f"**Total: {len(df_pag)} pagos | {format_money(df_pag['Monto Pagado'].sum())}**")
                st.download_button(
                    "📥 Descargar Pagos Conciliados",
                    df_pag.to_csv(index=False).encode("utf-8-sig"),
                    "subir_pagos_contagram.csv", "text/csv",
                    use_container_width=True,
                    type="primary")
            else:
                st.info("Sin pagos conciliados.")

        with tab4:
            st.markdown("### Excepciones - Requieren revision manual")
            df_exc = resultado["excepciones"]
            if not df_exc.empty:
                st.warning(f"**{len(df_exc)} movimientos** sin conciliar por un total de **{format_money(df_exc['Monto'].sum())}**")
                st.dataframe(
                    df_exc,
                    use_container_width=True,
                    hide_index=True,
                    column_config=build_column_config(df_exc),
                )

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df_exc.to_excel(writer, index=False, sheet_name="Excepciones")
                    wb = writer.book
                    ws = writer.sheets["Excepciones"]
                    hfmt = wb.add_format({"bold": True, "bg_color": "#E30613", "font_color": "white", "border": 1})
                    for i, col in enumerate(df_exc.columns):
                        ws.write(0, i, col, hfmt)
                        ws.set_column(i, i, max(15, len(str(col)) + 5))

                st.download_button(
                    "📥 Descargar Excepciones", buffer.getvalue(),
                    "excepciones.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary")
            else:
                st.success("Sin excepciones. Todos los movimientos fueron conciliados.")

        with tab5:
            st.markdown("### Detalle Completo")
            df_full = resultado["resultados"]

            # Ordenar columnas: las mas relevantes primero, el resto disponible
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

            # Columnas prioritarias primero + el resto de columnas disponibles
            ordered_cols = [c for c in priority_cols if c in df_full.columns]
            remaining_cols = [c for c in df_full.columns if c not in ordered_cols]
            all_cols = ordered_cols + remaining_cols

            st.dataframe(
                df_full[all_cols],
                use_container_width=True,
                hide_index=True,
                column_config=build_column_config(df_full[all_cols]),
            )

        # ═══ TAB AUDITORIA FACTURAS ═══
        if tab6 is not None:
            with tab6:
                st.markdown("### Auditoría de Facturas Contagram")
                st.info("Visión completa de todas las facturas procesadas. Puedes filtrar para ver las conciliadas vs las que quedaron sin match.")

                df_detalle = resultado.get("detalle_facturas", pd.DataFrame())
                if not df_detalle.empty:
                    # Filtros
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        # Default a "Sin Match" para mantener foco en desvios, pero permite ver "Conciliada"
                        opciones_estado_con = ["Sin Match", "Conciliada"]
                        filtro_estado_con = st.multiselect(
                            "Estado Conciliación",
                            opciones_estado_con,
                            default=["Sin Match"],
                            key="f_estado_con_audit"
                        )
                        if filtro_estado_con:
                            df_detalle = df_detalle[df_detalle["Estado Conciliacion"].isin(filtro_estado_con)]

                    with c2:
                        if "Estado" in df_detalle.columns:
                            estados = [e for e in df_detalle["Estado"].unique() if pd.notna(e) and e != ""]
                            filtro_estado = st.multiselect("Estado Factura", estados, default=estados, key="f_estado_audit")
                            df_detalle = df_detalle[df_detalle["Estado"].isin(filtro_estado)]
                    with c3:
                        # Toggle rapido Santander
                        st.write("Filtros extra")
                        solo_santander = st.checkbox("Solo 'Santander'", value=False, key="check_santander_audit")
                        if solo_santander and "Contiene Santander" in df_detalle.columns:
                             df_detalle = df_detalle[df_detalle["Contiene Santander"] == True]

                        # Multiselect Medio de Cobro especifico
                        if "Medio de Cobro" in df_detalle.columns:
                            medios = [m for m in df_detalle["Medio de Cobro"].unique() if pd.notna(m) and m != ""]
                            filtro_medio = st.multiselect("Medio de Cobro", medios, default=[], key="f_medio_detalle")
                            if filtro_medio:
                                df_detalle = df_detalle[df_detalle["Medio de Cobro"].isin(filtro_medio)]

                    st.dataframe(
                        df_detalle,
                        use_container_width=True,
                        hide_index=True,
                        column_config=build_column_config(df_detalle),
                    )

                    # Stats resumen
                    total_venta_col = "Total Venta" if "Total Venta" in df_detalle.columns else None
                    cobrado_col = "Cobrado" if "Cobrado" in df_detalle.columns else None
                    resumen = f"**{len(df_detalle)} facturas listadas**"
                    if total_venta_col:
                        resumen += f" | Total Venta: **{format_money(df_detalle[total_venta_col].sum())}**"
                    if cobrado_col:
                        resumen += f" | Cobrado: **{format_money(df_detalle[cobrado_col].sum())}**"
                    st.markdown(resumen)

                    st.download_button(
                        "📥 Descargar Auditoría Facturas",
                        df_detalle.to_csv(index=False).encode("utf-8-sig"),
                        "auditoria_facturas.csv", "text/csv",
                        use_container_width=True,
                        type="primary")
                else:
                    st.info("No hay detalle de facturas disponible.")

        # ═══ PERSISTENCIA TIDB ═══
        st.markdown("---")
        col_db, col_steps = st.columns([1, 2])

        with col_db:
            st.markdown("### Guardar en Base de Datos")

            # Verificar si secrets de TiDB estan configurados
            tidb_configurado = False
            try:
                _ = st.secrets["tidb"]
                tidb_configurado = True
            except Exception:
                pass

            if not tidb_configurado:
                st.info("Para habilitar persistencia en TiDB Cloud, crear el archivo `.streamlit/secrets.toml` con:")
                st.code("""[tidb]
host = "gateway01.us-east-1.prod.aws.tidbcloud.com"
port = 4000
user = "TU_USUARIO"
password = "TU_PASSWORD"
database = "test"
""", language="toml")
                st.caption("Luego reiniciar Streamlit (Ctrl+C y volver a ejecutar `streamlit run app.py`)")
            else:
                if st.button("Guardar en TiDB Cloud", use_container_width=True):
                    try:
                        from src.db_connector import guardar_conciliacion
                        secrets = st.secrets["tidb"]
                        with st.spinner("Guardando en TiDB Cloud..."):
                            res = guardar_conciliacion(resultado["resultados"], secrets)
                        if res["status"] == "ok":
                            st.success(f"Guardado: {res['registros_insertados']} registros en TiDB Cloud")
                        else:
                            st.error(f"Error TiDB: {res['mensaje']}")
                    except Exception as e:
                        st.error(f"Error de conexion: {e}")
                        st.info("Verificar credenciales en `.streamlit/secrets.toml`")

        with col_steps:
            st.markdown("### Pasos Siguientes")
            st.markdown("""
            1. **Descargar** los CSVs generados (Cobranzas y Pagos)
            2. **Ingresar** a Contagram
            3. **Importar** `subir_cobranzas_contagram.csv` en modulo **Cobranzas**
            4. **Importar** `subir_pagos_contagram.csv` en modulo **Pagos a Proveedores**
            5. **Revisar** excepciones y actualizar tabla parametrica
            """)

elif modo == "Manual (subir archivos)":
    st.info("Suba los archivos requeridos en las pestanas de arriba para comenzar.")
else:
    st.warning("No se encontraron datos de demostracion. Ejecute `python generar_datos_test.py` primero.")


# ═══════════════════════════════════════════════════════
# ASISTENTE DE CONCILIACION (Gemini Chat)
# ═══════════════════════════════════════════════════════

# Display chat history
for msg in st.session_state.get("chat_history", []):
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(msg["parts"][0]["text"])

# Chat input - pinned at the bottom of the viewport by Streamlit
if prompt := st.chat_input("Preguntale al asistente sobre la conciliacion..."):
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    st.session_state["chat_history"].append(
        {"role": "user", "parts": [{"text": prompt}]}
    )

    _gkey = None
    try:
        _gkey = st.secrets["google"]["api_key"]
    except Exception:
        _gkey = os.environ.get("GOOGLE_API_KEY")

    if _gkey and "stats" in st.session_state:
        try:
            from src.chatbot import crear_cliente, chat_responder
            if "gemini_client" not in st.session_state:
                st.session_state["gemini_client"] = crear_cliente(_gkey)
            _resp = chat_responder(
                st.session_state["gemini_client"],
                st.session_state["stats"],
                st.session_state["chat_history"][:-1],
                prompt,
            )
        except Exception as e:
            _resp = f"Error al consultar el asistente: {e}"
    elif not _gkey:
        _resp = "Configura tu API key de Google Gemini en `.streamlit/secrets.toml` para habilitar el asistente."
    else:
        _resp = "Ejecuta la conciliacion primero para que pueda responder preguntas sobre los resultados."

    st.session_state["chat_history"].append(
        {"role": "model", "parts": [{"text": _resp}]}
    )
    st.rerun()
