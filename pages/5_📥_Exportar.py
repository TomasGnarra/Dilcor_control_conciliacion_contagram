"""
Pagina 5: Exportar & Acciones
Stepper visual, previews de CSV, descarga individual y en lote.
"""
import streamlit as st
import pandas as pd
import io
import zipfile
from src.ui.styles import load_css
from src.ui.components import (
    section_div, page_header, format_money, stepper,
    render_data_table, no_data_warning,
    download_csv, download_excel, alert_card,
)

load_css()

page_header(
    "Exportar & Acciones",
    "Descargá los archivos para importar en Contagram",
    "📥",
)

if "resultado" not in st.session_state:
    no_data_warning()
    st.stop()

resultado = st.session_state["resultado"]
stats = st.session_state["stats"]


# ═══════════════════════════════════════════════════════
# STEPPER VISUAL
# ═══════════════════════════════════════════════════════
df_exc = resultado.get("excepciones", pd.DataFrame())
exc_count = len(df_exc)

steps = [
    {
        "title": "Revisar excepciones",
        "desc": f"{exc_count} excepciones pendientes" if exc_count > 0 else "Sin excepciones ✅",
        "done": exc_count == 0,
    },
    {
        "title": "Descargar CSV de Cobranzas",
        "desc": "Archivo para importar en módulo Cobranzas de Contagram",
        "done": False,
    },
    {
        "title": "Descargar CSV de Pagos",
        "desc": "Archivo para importar en módulo Pagos a Proveedores",
        "done": False,
    },
    {
        "title": "Importar en Contagram",
        "desc": "Ingresar a Contagram → Cobranzas / Pagos → Importar CSV",
        "done": False,
    },
    {
        "title": "Guardar en Base de Datos",
        "desc": "Opcional: persistir en TiDB Cloud para historial",
        "done": False,
    },
]

current = 0 if exc_count > 0 else 1
stepper(steps, current)


# ═══════════════════════════════════════════════════════
# PREVIEW Y DESCARGA: COBRANZAS
# ═══════════════════════════════════════════════════════
section_div("Cobranzas Conciliadas", "📥")
df_cob = resultado.get("cobranzas_csv", pd.DataFrame())

if not df_cob.empty:
    with st.expander(f"👁️ Vista previa ({len(df_cob)} registros)", expanded=False):
        render_data_table(df_cob.head(20), key="preview_cob")
        if len(df_cob) > 20:
            st.caption(f"Mostrando 20 de {len(df_cob)} registros")

    monto_col = "Monto Cobrado" if "Monto Cobrado" in df_cob.columns else None
    if monto_col:
        st.markdown(f"**{len(df_cob)} cobranzas** | Total: **{format_money(df_cob[monto_col].sum())}**")
    download_csv(df_cob, "subir_cobranzas_contagram.csv", "📥 Descargar Cobranzas CSV")
else:
    st.info("Sin cobranzas conciliadas para exportar.")


# ═══════════════════════════════════════════════════════
# PREVIEW Y DESCARGA: PAGOS
# ═══════════════════════════════════════════════════════
section_div("Pagos a Proveedores", "📤")
df_pag = resultado.get("pagos_csv", pd.DataFrame())

if not df_pag.empty:
    with st.expander(f"👁️ Vista previa ({len(df_pag)} registros)", expanded=False):
        render_data_table(df_pag.head(20), key="preview_pag")
        if len(df_pag) > 20:
            st.caption(f"Mostrando 20 de {len(df_pag)} registros")

    monto_col_p = "Monto Pagado" if "Monto Pagado" in df_pag.columns else None
    if monto_col_p:
        st.markdown(f"**{len(df_pag)} pagos** | Total: **{format_money(df_pag[monto_col_p].sum())}**")
    download_csv(df_pag, "subir_pagos_contagram.csv", "📥 Descargar Pagos CSV")
else:
    st.info("Sin pagos conciliados para exportar.")


# ═══════════════════════════════════════════════════════
# PREVIEW Y DESCARGA: EXCEPCIONES
# ═══════════════════════════════════════════════════════
if not df_exc.empty:
    section_div("Excepciones", "⚠️")
    with st.expander(f"👁️ Vista previa ({len(df_exc)} registros)", expanded=False):
        render_data_table(df_exc.head(20), key="preview_exc")

    c1, c2 = st.columns(2)
    with c1:
        download_excel(df_exc, "excepciones.xlsx", "Excepciones", "📥 Descargar Excel")
    with c2:
        download_csv(df_exc, "excepciones.csv", "📥 Descargar CSV")


# ═══════════════════════════════════════════════════════
# DESCARGA TODO EN ZIP
# ═══════════════════════════════════════════════════════
st.markdown("###")
section_div("Descargar Todo", "📦")

def generar_zip():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if not df_cob.empty:
            zf.writestr("subir_cobranzas_contagram.csv", df_cob.to_csv(index=False))
        if not df_pag.empty:
            zf.writestr("subir_pagos_contagram.csv", df_pag.to_csv(index=False))
        if not df_exc.empty:
            # Excel para excepciones
            exc_buffer = io.BytesIO()
            with pd.ExcelWriter(exc_buffer, engine="xlsxwriter") as writer:
                df_exc.to_excel(writer, index=False, sheet_name="Excepciones")
            zf.writestr("excepciones.xlsx", exc_buffer.getvalue())
    return buffer.getvalue()

st.download_button(
    "📦 Descargar TODO en ZIP",
    generar_zip(),
    "conciliacion_dilcor.zip",
    "application/zip",
    use_container_width=True,
    type="primary",
)
st.caption("Incluye: cobranzas CSV + pagos CSV + excepciones Excel")


# ═══════════════════════════════════════════════════════
# GUARDAR EN TIDB
# ═══════════════════════════════════════════════════════
st.markdown("###")
section_div("Guardar en Base de Datos", "🗄️")

import os

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
    if st.button("💾 Guardar en TiDB Cloud", use_container_width=True):
        try:
            from src.db_connector import guardar_conciliacion
            secrets = st.secrets["tidb"]
            with st.spinner("Guardando en TiDB Cloud..."):
                res = guardar_conciliacion(resultado["resultados"], secrets)
            if res["status"] == "ok":
                st.success(f"✅ Guardado: {res['registros_insertados']} registros en TiDB Cloud")
            else:
                st.error(f"Error TiDB: {res['mensaje']}")
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            st.info("Verificar credenciales en `.streamlit/secrets.toml`")


# ═══════════════════════════════════════════════════════
# INSTRUCCIONES
# ═══════════════════════════════════════════════════════
st.markdown("###")
section_div("Instrucciones de Importación", "📖")

st.markdown("""
**Para importar en Contagram:**

1. **Cobranzas** → Ingresar a Contagram → Módulo Cobranzas → Importar → Seleccionar `subir_cobranzas_contagram.csv`
2. **Pagos** → Ingresar a Contagram → Módulo Pagos a Proveedores → Importar → Seleccionar `subir_pagos_contagram.csv`
3. **Excepciones** → Revisar `excepciones.xlsx` → Para cada excepción, agregar el alias en `data/config/tabla_parametrica.csv`

> **Tip:** Cada alias que agregues a la tabla paramétrica reduce las excepciones en futuras conciliaciones. Con el tiempo, el sistema se vuelve cada vez más preciso.
""")
