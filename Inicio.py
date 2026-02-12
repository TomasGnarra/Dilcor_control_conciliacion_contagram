"""
DILCOR - Sistema de Conciliacion Bancaria con Contagram
v4.1 - Arq. Multi-Pagina (Inicio unificado)
"""
import streamlit as st
import pandas as pd
import os
import json
from src.motor_conciliacion import MotorConciliacion
from src.ui.styles import load_css, render_header
from src.ui.components import (
    format_money, kpi_hero, kpi_card, status_semaphore, alert_card,
    section_div, format_pct, donut_chart, horizontal_bar_chart,
    stacked_bar_chart, no_data_warning,
)

# --- Configuracion de pagina ---
st.set_page_config(
    page_title="Dilcor - Conciliacion",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Branding ---
load_css()
render_header()

# ═══════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════
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
                "tol_exacto_pct": 0.2, "tol_probable_pct": 0.5,
                "tol_probable_abs": 250, "umbral_id_exacto_pct": 92,
                "umbral_id_probable_pct": 70,
                "descripcion": "Maxima exactitud: menos falsos positivos, pero mas casos pendientes.",
            },
            2: {
                "etiqueta": "Estricto",
                "tol_exacto_pct": 0.3, "tol_probable_pct": 0.8,
                "tol_probable_abs": 300, "umbral_id_exacto_pct": 88,
                "umbral_id_probable_pct": 65,
                "descripcion": "Conservador: exige bastante similitud y tolera poca diferencia de monto.",
            },
            3: {
                "etiqueta": "Balanceado (recomendado)",
                "tol_exacto_pct": 0.5, "tol_probable_pct": 1.0,
                "tol_probable_abs": 500, "umbral_id_exacto_pct": 80,
                "umbral_id_probable_pct": 55,
                "descripcion": "Equilibrio entre precision y cobertura para operacion diaria.",
            },
            4: {
                "etiqueta": "Flexible",
                "tol_exacto_pct": 0.8, "tol_probable_pct": 1.5,
                "tol_probable_abs": 800, "umbral_id_exacto_pct": 77,
                "umbral_id_probable_pct": 50,
                "descripcion": "Acepta mas variaciones: reduce pendientes, pero requiere revision.",
            },
            5: {
                "etiqueta": "Muy flexible",
                "tol_exacto_pct": 1.0, "tol_probable_pct": 2.0,
                "tol_probable_abs": 1000, "umbral_id_exacto_pct": 75,
                "umbral_id_probable_pct": 45,
                "descripcion": "Maxima cobertura: mas coincidencias con mayor control manual.",
            },
        }

        nivel_umbral = st.slider(
            "Filtro deslizante de umbral", min_value=1, max_value=5, value=3, step=1,
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
    st.caption("Dilcor v4.1 | 2025")


# ═══════════════════════════════════════════════════════
# HELPERS DE CARGA
# ═══════════════════════════════════════════════════════

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
    if uploaded_file is None:
        return pd.DataFrame()
    name = uploaded_file.name.lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file)
    return pd.read_csv(uploaded_file)


def _detectar_columna_medio(df):
    for candidato in ["Medio de Cobro", "Medio de Pago", "Forma de Pago"]:
        if candidato in df.columns:
            return candidato
    for c in df.columns:
        if c.lower().strip() in ["medio de cobro", "medio de pago", "forma de pago"]:
            return c
    return None


def _cargar_mapeo_banco_medio():
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "data", "config", "mapeo_banco_medio_pago.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _crear_mask_filtro(df, col_medio, seleccionados, filtro_contiene=False):
    if filtro_contiene:
        mask = df[col_medio].fillna("").apply(
            lambda x: any(sel.lower() in str(x).lower() for sel in seleccionados)
        )
    else:
        mask = df[col_medio].isin(seleccionados)
    return mask


def _render_preview_filtro(ventas, col_medio, seleccionados, todos_medios, filtro_contiene=False):
    mask = _crear_mask_filtro(ventas, col_medio, seleccionados, filtro_contiene)
    df_filtrado = ventas[mask]

    col_monto = None
    for candidato in ["Cobrado", "Monto Total", "Total"]:
        if candidato in ventas.columns:
            col_monto = candidato
            break

    total_filas = len(ventas)
    filtrado_filas = len(df_filtrado)
    total_monto = ventas[col_monto].sum() if col_monto else 0
    filtrado_monto = df_filtrado[col_monto].sum() if col_monto else 0
    medios_excluidos = sorted(set(todos_medios) - set(seleccionados))
    excluidos_txt = ", ".join(medios_excluidos) if medios_excluidos else "Ninguno"
    seleccionados_txt = ", ".join(seleccionados)

    st.markdown(
        f'<div style="'
        f'background: linear-gradient(135deg, #1A1A1A 0%, #2D2D2D 100%);'
        f'border-left: 4px solid #E30613;'
        f'border-radius: 8px;'
        f'padding: 1.2rem 1.5rem;'
        f'margin: 1rem 0;'
        f'color: #FFFFFF;'
        f'">'
        f'<div style="font-size: 0.85rem; color: #E30613; font-weight: 700; '
        f'text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.8rem;">'
        f'Preview de Filtrado</div>'
        f'<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.9rem;">'
        f'<div>Total en archivo: <b>{total_filas}</b> ventas</div>'
        f'<div>Monto total: <b>${total_monto:,.0f}</b></div>'
        f'<div style="color: #4CAF50;">A conciliar: <b>{filtrado_filas}</b> ventas</div>'
        f'<div style="color: #4CAF50;">Monto filtrado: <b>${filtrado_monto:,.0f}</b></div>'
        f'</div>'
        f'<div style="margin-top: 0.8rem; font-size: 0.8rem; color: #AAA;">'
        f'Medios seleccionados: {seleccionados_txt}<br>'
        f'Medios excluidos: {excluidos_txt}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def load_manual_data():
    st.markdown("### Cargar Archivos")
    tab_banco, tab_ctg = st.tabs(["Extracto Bancario", "Contagram (Ventas y Pagos)"])

    extractos = []
    medios_pago_seleccionados = []

    with tab_banco:
        banco_opciones = ["Autodetectar", "Banco Galicia", "Banco Santander", "Mercado Pago"]
        banco_seleccionado = st.selectbox(
            "Seleccionar banco del extracto", banco_opciones, index=0,
            help="Elegi el banco correspondiente al extracto. Si no estas seguro, deja 'Autodetectar'.",
        )
        st.session_state["banco_seleccionado"] = banco_seleccionado

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
        st.markdown("**Archivo de Contagram** — Ventas y pagos con Cliente, CUIT, Cobrado, Medio de Cobro")
        uploaded_ventas = st.file_uploader("Subir archivo Contagram (CSV o XLSX)", type=["csv", "xlsx", "xls"], key="ventas")
        if uploaded_ventas:
            ventas = _leer_archivo(uploaded_ventas)
            st.success(f"{uploaded_ventas.name}: {len(ventas)} ventas cargadas")

            cols = [c.lower().strip() for c in ventas.columns]
            cols_requeridas = {"cliente", "cobrado"}
            cols_encontradas = {c for c in cols_requeridas if c in cols}
            if cols_encontradas != cols_requeridas:
                faltantes = cols_requeridas - cols_encontradas
                st.warning(f"Columnas faltantes en ventas: {', '.join(faltantes)}. Se usara formato disponible.")

            col_medio = _detectar_columna_medio(ventas)

            if col_medio is not None:
                # Ordenar medios de pago por frecuencia (mayor a menor)
                _conteos = ventas[col_medio].dropna().astype(str).value_counts()
                medios_unicos = [m for m in _conteos.index if m.strip()]

                if medios_unicos:
                    mapeo = _cargar_mapeo_banco_medio()
                    banco_sel = st.session_state.get("banco_seleccionado", "Autodetectar")

                    default_medios = []
                    if banco_sel != "Autodetectar" and banco_sel in mapeo:
                        patrones = mapeo[banco_sel]
                        for medio in medios_unicos:
                            medio_lower = medio.lower()
                            if any(patron.lower() in medio_lower for patron in patrones):
                                default_medios.append(medio)

                    st.markdown("---")
                    st.markdown("##### Filtrar por Medio de Pago")
                    if banco_sel != "Autodetectar":
                        st.caption(f"Banco seleccionado: **{banco_sel}** — se pre-seleccionan medios de pago relacionados")
                    else:
                        st.caption("Selecciona los medios de pago para filtrar las ventas a conciliar")

                    medios_pago_seleccionados = st.multiselect(
                        "Medios de pago a conciliar", medios_unicos, default=default_medios,
                        help="Solo las ventas con estos medios de pago se cruzaran contra el extracto bancario.",
                    )
                    st.session_state["medios_pago_seleccionados"] = medios_pago_seleccionados

                    filtro_contiene = st.toggle(
                        "Incluir medios que **contengan** los seleccionados", value=True,
                        help="Activado: filtra ventas cuyo medio de pago CONTENGA alguno de los seleccionados. Desactivado: solo match exacto.",
                    )
                    st.session_state["filtro_medio_contiene"] = filtro_contiene

                    if medios_pago_seleccionados:
                        _render_preview_filtro(ventas, col_medio, medios_pago_seleccionados, medios_unicos, filtro_contiene)

    return extractos, ventas, medios_pago_seleccionados


# ═══════════════════════════════════════════════════════
# CARGA DE DATOS
# ═══════════════════════════════════════════════════════
if modo == "Demo (datos de prueba)":
    extractos, ventas, compras, tabla_param = load_demo_data()
    data_ready = len(extractos) > 0
    modo_real = False
else:
    extractos, ventas, medios_pago_sel = load_manual_data()
    compras = pd.DataFrame()
    tabla_param = pd.DataFrame()
    cols_ventas = [c.lower().strip() for c in ventas.columns] if not ventas.empty else []
    modo_real = "cobrado" in cols_ventas or "medio de cobro" in cols_ventas
    data_ready = len(extractos) > 0 and not ventas.empty


# ═══════════════════════════════════════════════════════
# EJECUCION DEL MOTOR
# ═══════════════════════════════════════════════════════
if data_ready:
    if st.button("🚀 Ejecutar Conciliación", type="primary", use_container_width=True):
        with st.spinner("Procesando conciliación bancaria..."):
            if modo_real:
                motor = MotorConciliacion(pd.DataFrame())
                resultado = motor.procesar_real(
                    extractos, ventas,
                    match_config=match_config_override,
                    medios_pago_filtro=medios_pago_sel if modo == "Manual (subir archivos)" else None,
                    filtro_medio_contiene=st.session_state.get("filtro_medio_contiene", False) if modo == "Manual (subir archivos)" else False,
                )
            else:
                motor = MotorConciliacion(tabla_param)
                resultado = motor.procesar(extractos, ventas, compras, match_config=match_config_override)
            st.session_state["resultado"] = resultado
            st.session_state["stats"] = motor.stats
            st.session_state["modo_real"] = modo_real
        st.success("✅ Conciliación completada.")

    # ═══════════════════════════════════════════════════════
    # DASHBOARD PRINCIPAL (INICIO)
    # ═══════════════════════════════════════════════════════
    if "resultado" in st.session_state:
        st.markdown("---")
        resultado = st.session_state["resultado"]
        stats = st.session_state["stats"]
        df_det = resultado.get("detalle_facturas", pd.DataFrame())

        # SEMAFORO
        pct_conc = float(stats.get("tasa_conciliacion_total", 0))
        n_exc = stats.get("no_match", 0)
        status_semaphore(pct_conc, n_exc)

        # 4 KPIs HERO (Banco + Contagram + Gap)
        c1, c2, c3, c4 = st.columns(4)

        # 1. Banco
        with c1:
            kpi_hero(
                "🏦", f"{pct_conc}%", "Conciliación Bancaria",
                f"{stats['match_exacto']} exactos + {stats['probable_dif_cambio']} probables",
                "success" if pct_conc >= 90 else "warning" if pct_conc >= 70 else "danger",
            )

        # 2. Contagram
        total_facturado = df_det["Total Venta"].sum() if not df_det.empty and "Total Venta" in df_det.columns else stats.get("monto_ventas_contagram", 0)
        with c2:
            kpi_hero(
                "📄", format_money(total_facturado), "Total Facturado",
                f"Ventas: {len(df_det) if not df_det.empty else 0}",
                "neutral",
            )

        # 3. Gap
        gap = stats.get("revenue_gap", 0)
        with c3:
            kpi_hero(
                "💰", format_money(gap), "Revenue Gap",
                "Dif. Banco vs Contagram",
                "success" if abs(gap) < 10000 else "danger",
            )

        # 4. Excepciones
        with c4:
            kpi_hero(
                "⚠️", str(n_exc), "Excepciones Banco",
                format_money(stats.get("monto_no_conciliado", 0)),
                "success" if n_exc == 0 else "warning" if n_exc < 10 else "danger",
            )

        st.markdown("###")

        # Columnas de Graficos
        col_g1, col_g2 = st.columns(2)
        with col_g1:
             # Dona: Distribucion de matching (Banco)
            labels = ["Match Exacto", "Duda de ID", "Dif. Cambio", "Sin Match", "Gastos"]
            values = [stats.get("match_exacto", 0), stats.get("probable_duda_id", 0),
                      stats.get("probable_dif_cambio", 0), stats.get("no_match", 0),
                      stats.get("gastos_bancarios", 0)]
            filtered = [(l, v) for l, v in zip(labels, values) if v > 0]
            if filtered:
                fl, fv = zip(*filtered)
                # Colores
                colors_map = {
                    "Match Exacto": "#0D7C3D", "Duda de ID": "#D4760A", "Dif. Cambio": "#F59E0B",
                    "Sin Match": "#E30613", "Gastos": "#888"
                }
                cols = [colors_map.get(l, "#666") for l in fl]
                donut_chart(list(fl), list(fv), "Distribución Conciliación (Banco)", cols)
        
        with col_g2:
            # Grafico adaptable: Si hay 1 solo banco, mostrar desglose por tipo. Si hay >1, por banco.
            por_banco = stats.get("por_banco", {})
            bancos_activos = [b for b, d in por_banco.items() if d["movimientos"] > 0]
            
            if len(bancos_activos) > 1:
                # Barras por banco
                montos = [por_banco[b].get("monto_creditos", 0) + por_banco[b].get("monto_debitos", 0) for b in bancos_activos]
                horizontal_bar_chart(bancos_activos, montos, "Monto Total por Banco", "#1A1A1A")
            else:
                # Desglose por tipo de movimiento (Credito / Debito)
                cb = stats.get("cobros", {})
                pg = stats.get("pagos_prov", {})
                gastos = stats.get("monto_gastos_bancarios", 0)
                lbls = ["Cobros (Créditos)", "Pagos (Débitos)", "Gastos Bancarios"]
                vals = [cb.get("monto_total", 0), pg.get("monto_total", 0), gastos]
                horizontal_bar_chart(lbls, vals, "Volumen por Tipo de Movimiento", "#1A1A1A")

        # DESGLOSE CONTAGRAM (Mini)
        if not df_det.empty:
            st.markdown("###")
            section_div("Contagram", "📈")
            total_cobrado = df_det["Cobrado"].sum() if "Cobrado" in df_det.columns else 0
            pendiente = total_facturado - total_cobrado
            conciliado_ctg = df_det[df_det["Estado Conciliacion"] == "Conciliada"]["Cobrado"].sum() if "Cobrado" in df_det.columns else 0
            n_conciliadas = len(df_det[df_det["Estado Conciliacion"] == "Conciliada"])
            sin_match_ctg = len(df_det[df_det["Estado Conciliacion"] == "Sin Match"])
            
            c1, c2, c3, c4 = st.columns(4)
            kpi_card("Facturas Cargadas", f"{len(df_det)}", format_money(total_facturado), "neutral", c1)
            kpi_card("Total Cobrado", format_money(total_cobrado), f"Pendiente: {format_money(pendiente)}", "neutral", c2)
            kpi_card("Conciliado en Banco", format_money(conciliado_ctg), f"{n_conciliadas} facturas identificadas", "success", c3)
            col_status = "success" if sin_match_ctg == 0 else "danger"
            kpi_card("Facturas Sin Match", f"{sin_match_ctg}", "No halladas en Banco", col_status, c4)
            
        st.info("👈 Usa el **menú lateral** para navegar a las vistas de detalle (Banco, Contagram, Excepciones).")

elif modo == "Manual (subir archivos)":
    st.info("Suba los archivos requeridos en las pestañas de arriba para comenzar.")
else:
    st.warning("No se encontraron datos de demostración. Ejecute `python generar_datos_test.py` primero.")


# ═══════════════════════════════════════════════════════
# ASISTENTE DE CONCILIACION (Gemini Chat)
# ═══════════════════════════════════════════════════════
for msg in st.session_state.get("chat_history", []):
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(msg["parts"][0]["text"])

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
