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

# --- Configuracion de pagina ---
st.set_page_config(
    page_title="Dilcor - Conciliacion Bancaria",
    page_icon="https://img.icons8.com/fluency/48/bank-building.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Branding Dilcor: Negro / Rojo / Blanco ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Header principal */
    .dilcor-header {
        background: #1A1A1A;
        padding: 1.5rem 2rem;
        border-radius: 0 0 16px 16px;
        text-align: center;
        margin: -1rem -1rem 1.5rem -1rem;
    }
    .dilcor-logo {
        font-size: 2.8rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: 3px;
        margin-bottom: 0;
    }
    .dilcor-logo span {
        color: #E30613;
    }
    .dilcor-subtitle {
        font-size: 0.85rem;
        color: #CCCCCC;
        letter-spacing: 5px;
        text-transform: uppercase;
        margin-top: 0.2rem;
    }
    .dilcor-sub2 {
        font-size: 1rem;
        color: #E30613;
        font-weight: 600;
        margin-top: 0.8rem;
        padding-top: 0.8rem;
        border-top: 1px solid #333;
    }

    /* Metric cards */
    .mc { padding: 1.2rem; border-radius: 12px; text-align: center;
          box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
    .mc-dark { background: #1A1A1A; color: #FFF; }
    .mc-red { background: #E30613; color: #FFF; }
    .mc-gray { background: #F5F5F5; color: #1A1A1A; border: 1px solid #E0E0E0; }
    .mc-green { background: #0D7C3D; color: #FFF; }
    .mc-orange { background: #D4760A; color: #FFF; }
    .mc-val { font-size: 2rem; font-weight: 800; }
    .mc-lbl { font-size: 0.8rem; opacity: 0.9; margin-top: 0.3rem; }

    /* KPI financiero */
    .kpi-row { display: flex; gap: 1rem; margin: 1rem 0; }
    .kpi-card { flex: 1; background: #FAFAFA; border-left: 4px solid #E30613;
                padding: 1rem 1.2rem; border-radius: 0 8px 8px 0; }
    .kpi-card-green { flex: 1; background: #F0FFF4; border-left: 4px solid #0D7C3D;
                      padding: 1rem 1.2rem; border-radius: 0 8px 8px 0; }
    .kpi-card-amber { flex: 1; background: #FFFBEB; border-left: 4px solid #D4760A;
                      padding: 1rem 1.2rem; border-radius: 0 8px 8px 0; }
    .kpi-val { font-size: 1.4rem; font-weight: 700; color: #1A1A1A; }
    .kpi-lbl { font-size: 0.78rem; color: #666; }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 20px; font-weight: 600; }

    /* Sidebar branding */
    section[data-testid="stSidebar"] {
        background: #1A1A1A;
    }
    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] .stRadio label span {
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #333 !important;
    }
    section[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] div {
        background: #E30613 !important;
    }

    /* Expander headers */
    div[data-testid="stExpander"] details summary p {
        font-weight: 600; font-size: 1.05rem;
    }

    /* Download buttons */
    .stDownloadButton button {
        background: #1A1A1A !important;
        color: #FFF !important;
        border: none !important;
    }
    .stDownloadButton button:hover {
        background: #E30613 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<div class="dilcor-header">
    <div class="dilcor-logo">D<span>i</span>lcor</div>
    <div class="dilcor-subtitle">Distribuidora Mayorista</div>
    <div class="dilcor-sub2">Sistema de Conciliacion Bancaria</div>
</div>
""", unsafe_allow_html=True)

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
        tol_exacto = st.slider(
            "Tolerancia monto exacto (%)",
            0.0, 2.0, 0.5, 0.1,
            help="Diferencia maxima de monto para match exacto"
        ) / 100
        tol_probable_pct = st.slider(
            "Tolerancia monto probable (%)",
            0.0, 5.0, 1.0, 0.1,
            help="Diferencia maxima de monto para match probable"
        ) / 100
        tol_probable_abs = st.number_input(
            "Tolerancia monto probable ($ ARS)",
            0, 10000, 500, 50,
            help="Diferencia absoluta maxima en pesos para match probable"
        )
        umbral_id_exacto = st.slider(
            "Umbral similitud ID exacto",
            0.5, 1.0, 0.80, 0.05,
        )
        umbral_id_probable = st.slider(
            "Umbral similitud ID probable",
            0.3, 0.8, 0.55, 0.05,
        )

    match_config_override = {
        "tolerancia_monto_exacto_pct": tol_exacto,
        "tolerancia_monto_probable_pct": tol_probable_pct,
        "tolerancia_monto_probable_abs": float(tol_probable_abs),
        "umbral_id_exacto": umbral_id_exacto,
        "umbral_id_probable": umbral_id_probable,
    }

    st.markdown("---")
    st.caption("Dilcor v2.0 MVP | 2025")


# --- Helpers ---
def format_money(val):
    if pd.isna(val) or val == 0:
        return "$0,00"
    sign = "-" if val < 0 else ""
    return f"{sign}${abs(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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


def load_manual_data():
    """Interfaz con tabs por banco para subir archivos."""
    st.markdown("### Cargar Archivos")
    tab_g, tab_s, tab_mp, tab_otro, tab_ctg = st.tabs([
        "Banco Galicia", "Banco Santander", "Mercado Pago", "Otro Banco", "Datos Contagram"
    ])

    extractos = []
    with tab_g:
        st.markdown("**Extracto Banco Galicia** (CSV con Fecha, Descripcion, Debito, Credito, Saldo)")
        f_g = st.file_uploader("Subir extracto Galicia", type=["csv"], key="galicia")
        if f_g:
            extractos.append(pd.read_csv(f_g))
            st.success(f"Galicia: {f_g.name} cargado")

    with tab_s:
        st.markdown("**Extracto Banco Santander** (CSV con Fecha Operacion, Concepto, Importe, Saldo)")
        f_s = st.file_uploader("Subir extracto Santander", type=["csv"], key="santander")
        if f_s:
            extractos.append(pd.read_csv(f_s))
            st.success(f"Santander: {f_s.name} cargado")

    with tab_mp:
        st.markdown("**Extracto Mercado Pago** (CSV con Monto Bruto, Comision MP, Monto Neto)")
        f_mp = st.file_uploader("Subir extracto Mercado Pago", type=["csv"], key="mercadopago")
        if f_mp:
            extractos.append(pd.read_csv(f_mp))
            st.success(f"Mercado Pago: {f_mp.name} cargado")

    with tab_otro:
        st.markdown("**Otro banco** - El sistema intentara detectar el formato automaticamente.")
        f_otros = st.file_uploader("Subir extracto(s)", type=["csv"], accept_multiple_files=True, key="otros")
        if f_otros:
            for f in f_otros:
                extractos.append(pd.read_csv(f))
                st.success(f"{f.name} cargado")

    with tab_ctg:
        st.markdown("**Datos de Contagram**")
        uploaded_ventas = st.file_uploader("Ventas pendientes (CSV)", type=["csv"], key="ventas")
        uploaded_compras = st.file_uploader("Compras pendientes (CSV)", type=["csv"], key="compras")
        uploaded_param = st.file_uploader("Tabla parametrica (CSV)", type=["csv"], key="param")

    ventas = pd.read_csv(uploaded_ventas) if uploaded_ventas else pd.DataFrame()
    compras = pd.read_csv(uploaded_compras) if uploaded_compras else pd.DataFrame()
    tabla_param = pd.read_csv(uploaded_param) if uploaded_param else pd.DataFrame()

    return extractos, ventas, compras, tabla_param


# --- Carga de datos ---
if modo == "Demo (datos de prueba)":
    extractos, ventas, compras, tabla_param = load_demo_data()
    data_ready = len(extractos) > 0
else:
    extractos, ventas, compras, tabla_param = load_manual_data()
    data_ready = len(extractos) > 0 and not ventas.empty and not tabla_param.empty


# --- Ejecucion ---
if data_ready:
    if st.button("Ejecutar Conciliacion", type="primary", use_container_width=True):
        with st.spinner("Procesando conciliacion bancaria..."):
            motor = MotorConciliacion(tabla_param)
            resultado = motor.procesar(extractos, ventas, compras, match_config=match_config_override)
            st.session_state["resultado"] = resultado
            st.session_state["stats"] = motor.stats

    if "resultado" in st.session_state:
        resultado = st.session_state["resultado"]
        stats = st.session_state["stats"]

        # ═══ DASHBOARD PRINCIPAL ═══
        st.markdown("---")

        # --- Fila 1: Metricas de conciliacion ternaria ---
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f'<div class="mc mc-dark"><div class="mc-val">{stats["total_movimientos"]}</div><div class="mc-lbl">Movimientos</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="mc mc-green"><div class="mc-val">{stats["match_exacto"]}</div><div class="mc-lbl">Match Exacto</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="mc mc-orange"><div class="mc-val">{stats["probable_duda_id"]}</div><div class="mc-lbl">Duda de ID</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="mc mc-orange"><div class="mc-val">{stats["probable_dif_cambio"]}</div><div class="mc-lbl">Dif. de Cambio</div></div>', unsafe_allow_html=True)
        with c5:
            st.markdown(f'<div class="mc mc-red"><div class="mc-val">{stats["no_match"]}</div><div class="mc-lbl">Sin Match</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Fila 2: Tasas ---
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Tasa Match Exacto", f"{stats['tasa_match_exacto']}%")
        with c2:
            st.metric("Tasa Probable (revision)", f"{stats['tasa_probable']}%")
        with c3:
            st.metric("Conciliacion Total", f"{stats['tasa_conciliacion_total']}%",
                       delta=f"{stats['no_match']} sin conciliar", delta_color="inverse")

        st.markdown("---")

        # ═══ KPIs DE IMPACTO FINANCIERO ═══
        st.markdown("### Impacto Financiero")
        st.markdown("""
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-lbl">Cobrado en Bancos</div>
                <div class="kpi-val">""" + format_money(stats["monto_cobranzas"]) + """</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-lbl">Facturado en Contagram</div>
                <div class="kpi-val">""" + format_money(stats["monto_ventas_contagram"]) + """</div>
            </div>
            <div class="kpi-card""" + ("-green" if stats["revenue_gap"] >= 0 else "") + """">
                <div class="kpi-lbl">Revenue Gap (Banco - Contagram)</div>
                <div class="kpi-val">""" + format_money(stats["revenue_gap"]) + """</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Pagos a Proveedores", format_money(stats["monto_pagos"]),
                       f"{stats['total_pagos']} movimientos")
        with c2:
            st.metric("Gastos Bancarios", format_money(stats["monto_gastos_bancarios"]),
                       f"{stats['gastos_bancarios']} movimientos")
        with c3:
            delta_dif = format_money(stats["monto_dif_cambio_neto"])
            st.metric("Diferencias de Cambio (neto)", delta_dif,
                       f"+{format_money(stats['monto_a_favor'])} / -{format_money(stats['monto_en_contra'])}")
        with c4:
            st.metric("Dinero sin Conciliar", format_money(stats["monto_no_conciliado"]),
                       f"{stats['no_match']} movimientos", delta_color="inverse")

        # ═══ TABS DE DETALLE ═══
        st.markdown("---")
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "Por Banco", "Cobranzas", "Pagos", "Excepciones", "Detalle Completo"
        ])

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
                col1, col2 = st.columns(2)
                with col1:
                    niveles = [n for n in df_cob["Nivel Match"].unique() if pd.notna(n)]
                    filtro_nivel = st.multiselect("Filtrar por nivel", niveles, default=niveles, key="f_cob")
                with col2:
                    bancos = df_cob["Banco Origen"].unique().tolist()
                    filtro_banco = st.multiselect("Filtrar por banco", bancos, default=bancos, key="fb_cob")

                df_f = df_cob[(df_cob["Nivel Match"].isin(filtro_nivel)) & (df_cob["Banco Origen"].isin(filtro_banco))]
                st.dataframe(df_f, use_container_width=True, hide_index=True)
                st.markdown(f"**Total: {len(df_f)} cobranzas | {format_money(df_f['Monto Cobrado'].sum())}**")

                st.download_button(
                    "Descargar subir_cobranzas_contagram.csv",
                    df_f.to_csv(index=False).encode("utf-8-sig"),
                    "subir_cobranzas_contagram.csv", "text/csv",
                    use_container_width=True)
            else:
                st.info("Sin cobranzas conciliadas.")

        with tab3:
            st.markdown("### Pagos a Proveedores - Para importar en Contagram")
            df_pag = resultado["pagos_csv"]
            if not df_pag.empty:
                st.dataframe(df_pag, use_container_width=True, hide_index=True)
                st.markdown(f"**Total: {len(df_pag)} pagos | {format_money(df_pag['Monto Pagado'].sum())}**")
                st.download_button(
                    "Descargar subir_pagos_contagram.csv",
                    df_pag.to_csv(index=False).encode("utf-8-sig"),
                    "subir_pagos_contagram.csv", "text/csv",
                    use_container_width=True)
            else:
                st.info("Sin pagos conciliados.")

        with tab4:
            st.markdown("### Excepciones - Requieren revision manual")
            df_exc = resultado["excepciones"]
            if not df_exc.empty:
                st.warning(f"**{len(df_exc)} movimientos** sin conciliar por un total de **{format_money(df_exc['Monto'].sum())}**")
                st.dataframe(df_exc, use_container_width=True, hide_index=True)

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
                    "Descargar excepciones.xlsx", buffer.getvalue(),
                    "excepciones.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)
            else:
                st.success("Sin excepciones. Todos los movimientos fueron conciliados.")

        with tab5:
            st.markdown("### Detalle Completo")
            df_full = resultado["resultados"]
            cols = ["fecha", "banco", "tipo", "clasificacion", "descripcion",
                    "monto", "match_nivel", "match_detalle", "confianza",
                    "nombre_contagram", "factura_match", "diferencia_monto"]
            cols_ok = [c for c in cols if c in df_full.columns]
            st.dataframe(df_full[cols_ok], use_container_width=True, hide_index=True)

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
