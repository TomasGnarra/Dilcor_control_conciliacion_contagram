"""
DILCOR - Sistema de Conciliación Bancaria
MVP Opción A - Interfaz Streamlit
"""
import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime

from src.motor_conciliacion import MotorConciliacion

# --- Configuración de página ---
st.set_page_config(
    page_title="Dilcor - Conciliación Bancaria",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS personalizado ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        padding: 0.5rem 0;
        border-bottom: 3px solid #e94560;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6c757d;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card-red {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card-orange {
        background: linear-gradient(135deg, #f2994a 0%, #f2c94c 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
    }
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.9;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        font-weight: 600;
    }
    div[data-testid="stExpander"] details summary p {
        font-weight: 600;
        font-size: 1.05rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown('<div class="main-header">DILCOR - Conciliación Bancaria</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Sistema de conciliación automática entre extractos bancarios y Contagram (ERP)</div>', unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/bank-building.png", width=80)
    st.markdown("### Configuración")
    st.markdown("---")

    modo = st.radio(
        "Modo de operación",
        ["Demo (datos de prueba)", "Manual (subir archivos)"],
        index=0,
        help="Use 'Demo' para ver el sistema con datos de ejemplo, o 'Manual' para subir sus propios archivos."
    )

    st.markdown("---")
    st.markdown("### Bancos soportados")
    st.markdown("- 🏦 Banco Galicia")
    st.markdown("- 🏦 Banco Santander")
    st.markdown("- 💳 Mercado Pago")

    st.markdown("---")
    st.markdown("### Acerca de")
    st.markdown(
        "**Opción A - MVP Manual**\n\n"
        "El usuario sube extractos bancarios (CSV) "
        "y el sistema genera archivos listos para "
        "importar en Contagram."
    )
    st.markdown("---")
    st.caption("Dilcor v1.0 MVP | Dic 2025")


def format_money(val):
    """Formato moneda argentina."""
    if pd.isna(val) or val == 0:
        return "$0,00"
    return f"${val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def load_demo_data():
    """Carga datos de demostración."""
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
    """Interfaz para subir archivos manualmente."""
    st.markdown("### 📁 Cargar Archivos")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Extractos Bancarios**")
        uploaded_banks = st.file_uploader(
            "Subir extractos bancarios (CSV)",
            type=["csv"],
            accept_multiple_files=True,
            help="Suba uno o más extractos bancarios en formato CSV. El sistema detecta automáticamente el banco."
        )

    with col2:
        st.markdown("**Datos Contagram**")
        uploaded_ventas = st.file_uploader("Ventas pendientes (CSV)", type=["csv"])
        uploaded_compras = st.file_uploader("Compras pendientes (CSV)", type=["csv"])
        uploaded_param = st.file_uploader("Tabla paramétrica (CSV)", type=["csv"])

    extractos = [pd.read_csv(f) for f in uploaded_banks] if uploaded_banks else []
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


# --- Ejecución ---
if data_ready:
    if st.button("🚀 Ejecutar Conciliación", type="primary", use_container_width=True):
        with st.spinner("Procesando conciliación..."):
            motor = MotorConciliacion(tabla_param)
            resultado = motor.procesar(extractos, ventas, compras)
            st.session_state["resultado"] = resultado
            st.session_state["stats"] = motor.stats

    if "resultado" in st.session_state:
        resultado = st.session_state["resultado"]
        stats = st.session_state["stats"]

        # === DASHBOARD PRINCIPAL ===
        st.markdown("---")
        st.markdown("## 📊 Resultados de la Conciliación")

        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{stats['total_movimientos']}</div>
                <div class="metric-label">Movimientos Procesados</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card-green">
                <div class="metric-value">{stats['tasa_conciliacion_auto']:.1f}%</div>
                <div class="metric-label">Conciliación Automática</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card-orange">
                <div class="metric-value">{stats['probables']}</div>
                <div class="metric-label">Match Probable (revisión)</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card-red">
                <div class="metric-value">{stats['excepciones']}</div>
                <div class="metric-label">Excepciones</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Métricas de montos
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Total Cobranzas", format_money(stats["monto_cobranzas"]),
                       f"{stats['total_cobranzas']} movimientos")
        with col2:
            st.metric("💸 Total Pagos a Proveedores", format_money(stats["monto_pagos"]),
                       f"{stats['total_pagos']} movimientos")
        with col3:
            st.metric("🏦 Gastos Bancarios", format_money(stats["monto_gastos_bancarios"]),
                       f"{stats['gastos_bancarios']} movimientos")

        # === TABS ===
        st.markdown("---")
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 Resumen por Banco",
            "✅ Cobranzas (para Contagram)",
            "💳 Pagos (para Contagram)",
            "⚠️ Excepciones",
            "📄 Detalle Completo"
        ])

        with tab1:
            st.markdown("### Resumen por Banco")
            for banco, data in stats["por_banco"].items():
                with st.expander(f"🏦 {banco} - {data['movimientos']} movimientos"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Automáticos", data["automaticos"])
                    c2.metric("Probables", data["probables"])
                    c3.metric("Excepciones", data["excepciones"])
                    c4.metric("Créditos", format_money(data["monto_creditos"]))

        with tab2:
            st.markdown("### Cobranzas - Listas para importar en Contagram")
            df_cob = resultado["cobranzas_csv"]
            if not df_cob.empty:
                # Filtros
                col1, col2 = st.columns(2)
                with col1:
                    filtro_nivel = st.multiselect(
                        "Filtrar por nivel de match",
                        ["automatico", "probable"],
                        default=["automatico", "probable"],
                        key="filtro_cob"
                    )
                with col2:
                    filtro_banco = st.multiselect(
                        "Filtrar por banco",
                        df_cob["Banco Origen"].unique().tolist(),
                        default=df_cob["Banco Origen"].unique().tolist(),
                        key="filtro_banco_cob"
                    )

                df_filtered = df_cob[
                    (df_cob["Nivel Match"].isin(filtro_nivel)) &
                    (df_cob["Banco Origen"].isin(filtro_banco))
                ]

                st.dataframe(df_filtered, use_container_width=True, hide_index=True)
                st.markdown(f"**Total: {len(df_filtered)} cobranzas | Monto: {format_money(df_filtered['Monto Cobrado'].sum())}**")

                # Descarga
                csv_cob = df_filtered.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "📥 Descargar subir_cobranzas_contagram.csv",
                    csv_cob,
                    "subir_cobranzas_contagram.csv",
                    "text/csv",
                    use_container_width=True,
                )
            else:
                st.info("No se encontraron cobranzas conciliadas.")

        with tab3:
            st.markdown("### Pagos a Proveedores - Listos para importar en Contagram")
            df_pag = resultado["pagos_csv"]
            if not df_pag.empty:
                st.dataframe(df_pag, use_container_width=True, hide_index=True)
                st.markdown(f"**Total: {len(df_pag)} pagos | Monto: {format_money(df_pag['Monto Pagado'].sum())}**")

                csv_pag = df_pag.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "📥 Descargar subir_pagos_contagram.csv",
                    csv_pag,
                    "subir_pagos_contagram.csv",
                    "text/csv",
                    use_container_width=True,
                )
            else:
                st.info("No se encontraron pagos conciliados.")

        with tab4:
            st.markdown("### Excepciones - Requieren revisión manual")
            df_exc = resultado["excepciones"]
            if not df_exc.empty:
                st.warning(f"Se encontraron **{len(df_exc)} movimientos** que no pudieron ser conciliados automáticamente.")
                st.dataframe(df_exc, use_container_width=True, hide_index=True)

                # Descarga Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df_exc.to_excel(writer, index=False, sheet_name="Excepciones")
                    workbook = writer.book
                    worksheet = writer.sheets["Excepciones"]
                    header_format = workbook.add_format({
                        "bold": True,
                        "bg_color": "#e94560",
                        "font_color": "white",
                        "border": 1,
                    })
                    for col_num, value in enumerate(df_exc.columns):
                        worksheet.write(0, col_num, value, header_format)
                        worksheet.set_column(col_num, col_num, max(15, len(str(value)) + 5))

                st.download_button(
                    "📥 Descargar excepciones.xlsx",
                    buffer.getvalue(),
                    "excepciones.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.success("No hay excepciones. Todos los movimientos fueron conciliados.")

        with tab5:
            st.markdown("### Detalle Completo de Conciliación")
            df_full = resultado["resultados"]
            cols_mostrar = [
                "fecha", "banco", "tipo", "clasificacion", "descripcion",
                "monto", "match_nivel", "confianza", "nombre_contagram",
                "factura_match", "diferencia_monto"
            ]
            cols_disponibles = [c for c in cols_mostrar if c in df_full.columns]
            st.dataframe(df_full[cols_disponibles], use_container_width=True, hide_index=True)

        # === FLUJO OPERATIVO ===
        st.markdown("---")
        st.markdown("## 📝 Pasos Siguientes")
        st.markdown("""
        1. **Descargar** los archivos CSV generados (Cobranzas y Pagos)
        2. **Ingresar a Contagram**
        3. **Importar** `subir_cobranzas_contagram.csv` en el módulo **Cobranzas**
        4. **Importar** `subir_pagos_contagram.csv` en el módulo **Pagos a Proveedores**
        5. **Revisar** las excepciones y resolverlas manualmente
        6. Contagram registrará automáticamente la cancelación de facturas y movimientos bancarios
        """)

elif modo == "Manual (subir archivos)":
    st.info("👆 Suba los archivos requeridos para comenzar la conciliación.")
else:
    st.warning("No se encontraron datos de demostración. Ejecute `python generar_datos_test.py` primero.")
