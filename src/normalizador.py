"""
Normalizador bancario - Estandariza extractos de diferentes bancos
a un formato unificado para el motor de conciliación.
"""
import pandas as pd
import re


FORMATO_UNIFICADO = [
    "fecha",
    "banco",
    "tipo",          # CREDITO / DEBITO
    "descripcion",
    "descripcion_normalizada",
    "monto",
    "referencia",
]


def _limpiar_texto(texto: str) -> str:
    """Normaliza texto: mayúsculas, sin acentos, sin caracteres especiales."""
    if pd.isna(texto):
        return ""
    texto = str(texto).upper().strip()
    reemplazos = {
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "Ñ": "N", "Ü": "U",
    }
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    texto = re.sub(r"[^A-Z0-9\s\-\.]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _parse_monto(valor) -> float:
    """Parsea montos en formato argentino (1.234.567,89) o estándar."""
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    if str(valor).strip() == "":
        return 0.0
    s = str(valor).strip()
    # Formato argentino: puntos como separadores de miles, coma decimal
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def normalizar_galicia(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza extracto del Banco Galicia."""
    rows = []
    for _, r in df.iterrows():
        debito = _parse_monto(r.get("Debito", 0))
        credito = _parse_monto(r.get("Credito", 0))
        if (pd.isna(debito) or debito == 0) and (pd.isna(credito) or credito == 0):
            continue
        debito = 0.0 if pd.isna(debito) else debito
        credito = 0.0 if pd.isna(credito) else credito
        if credito > 0:
            tipo = "CREDITO"
            monto = credito
        else:
            tipo = "DEBITO"
            monto = debito
        rows.append({
            "fecha": pd.to_datetime(r["Fecha"], dayfirst=True),
            "banco": "Banco Galicia",
            "tipo": tipo,
            "descripcion": str(r.get("Descripcion", "")),
            "descripcion_normalizada": _limpiar_texto(r.get("Descripcion", "")),
            "monto": round(monto, 2),
            "referencia": str(r.get("Referencia", "")),
        })
    return pd.DataFrame(rows)


def normalizar_santander(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza extracto del Banco Santander."""
    rows = []
    for _, r in df.iterrows():
        importe = _parse_monto(r.get("Importe", 0))
        if importe >= 0:
            tipo = "CREDITO"
            monto = abs(importe)
        else:
            tipo = "DEBITO"
            monto = abs(importe)
        rows.append({
            "fecha": pd.to_datetime(r["Fecha Operacion"], dayfirst=True),
            "banco": "Banco Santander",
            "tipo": tipo,
            "descripcion": str(r.get("Concepto", "")),
            "descripcion_normalizada": _limpiar_texto(r.get("Concepto", "")),
            "monto": round(monto, 2),
            "referencia": str(r.get("Nro Comprobante", "")),
        })
    return pd.DataFrame(rows)


def normalizar_mercadopago(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza extracto de Mercado Pago."""
    rows = []
    for _, r in df.iterrows():
        tipo_op = str(r.get("Tipo Operacion", "")).upper()
        monto_bruto = _parse_monto(r.get("Monto Bruto", 0))
        comision = _parse_monto(r.get("Comision MP", 0))
        iva_com = _parse_monto(r.get("IVA Comision", 0))
        monto_neto = _parse_monto(r.get("Monto Neto", 0))

        if "COBRO" in tipo_op or "LIQUID" in tipo_op:
            tipo = "CREDITO"
        else:
            tipo = "DEBITO"

        rows.append({
            "fecha": pd.to_datetime(r["Fecha"], dayfirst=True),
            "banco": "Mercado Pago",
            "tipo": tipo,
            "descripcion": str(r.get("Detalle", "")),
            "descripcion_normalizada": _limpiar_texto(r.get("Detalle", "")),
            "monto": round(monto_bruto, 2),
            "monto_neto": round(monto_neto, 2),
            "comision_mp": round(comision, 2),
            "iva_comision_mp": round(iva_com, 2),
            "referencia": str(r.get("Nro Operacion", "")),
        })
    result = pd.DataFrame(rows)
    # Asegurar columnas del formato unificado
    for col in FORMATO_UNIFICADO:
        if col not in result.columns:
            result[col] = ""
    return result


def _parse_fecha_santander_real(valor):
    """Parsea fecha de Santander real - serial Excel o string DD/MM/YYYY."""
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, (int, float)):
        return pd.Timestamp("1899-12-30") + pd.Timedelta(days=int(valor))
    return pd.to_datetime(str(valor), dayfirst=True, errors="coerce")


def _extraer_datos_transferencia(desc: str) -> tuple:
    """Extrae nombre y CUIT de una descripcion de transferencia bancaria.
    Patterns:
      'Transferencia Recibida  - De Magueteco S.a.s. / - Var / 30718850289'
      'Transf Recibida Cvu Dif Titular  - De Pizza Italia Srl / Mercado Pago /30715023853'
    """
    desc = str(desc)
    nombre = None
    cuit = None

    # Pattern: "De NOMBRE / ... / CUIT"
    m = re.search(r'De\s+(.+?)\s*/.*?(\d{11})', desc)
    if m:
        nombre = m.group(1).strip()
        cuit = m.group(2)
        return nombre, cuit

    # Pattern: "De NOMBRE / CUIT" (sin detalles intermedios)
    m = re.search(r'De\s+(.+?)\s*/\s*(\d{11})', desc)
    if m:
        nombre = m.group(1).strip()
        cuit = m.group(2)
        return nombre, cuit

    # Solo CUIT si presente
    m = re.search(r'(\d{11})', desc)
    if m:
        cuit = m.group(1)

    return nombre, cuit


def normalizar_santander_real(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza extracto real de Banco Santander (XLSX con headers no estandar).

    Formato detectado: 6 columnas (Fecha|Sucursal|CodTx|NroMov|Descripcion|Importe)
    con fechas mixtas (serial Excel + strings DD/MM/YYYY) y CUIT en descripciones.
    """
    df = df.copy()

    # Mapear columnas por posicion (headers no limpios)
    col_map = {}
    for i, col in enumerate(df.columns):
        col_map[col] = ["fecha_raw", "sucursal", "cod_transaccion",
                        "nro_comprobante", "descripcion", "importe"][i]
    df = df.rename(columns=col_map)

    rows = []
    for _, r in df.iterrows():
        fecha = _parse_fecha_santander_real(r["fecha_raw"])
        importe = float(r["importe"])
        tipo = "CREDITO" if importe >= 0 else "DEBITO"

        desc = str(r["descripcion"])
        nombre_extraido, cuit_extraido = _extraer_datos_transferencia(desc)

        rows.append({
            "fecha": fecha,
            "banco": "Banco Santander",
            "tipo": tipo,
            "descripcion": desc,
            "descripcion_normalizada": _limpiar_texto(desc),
            "monto": round(abs(importe), 2),
            "referencia": str(int(r["nro_comprobante"])) if pd.notna(r["nro_comprobante"]) else "",
            "sucursal": str(r.get("sucursal", "")),
            "cod_transaccion": int(r.get("cod_transaccion", 0)),
            "cuit_banco": cuit_extraido or "",
            "nombre_banco_extraido": nombre_extraido or "",
        })
    return pd.DataFrame(rows)


NORMALIZADORES = {
    "galicia": normalizar_galicia,
    "santander": normalizar_santander,
    "santander_real": normalizar_santander_real,
    "mercadopago": normalizar_mercadopago,
}


def detectar_banco(df: pd.DataFrame) -> str:
    """Detecta automaticamente el banco segun las columnas del archivo."""
    cols = [c.lower().strip() for c in df.columns]
    cols_str = " ".join(cols)

    # Santander real: primera columna contiene "movimientos" y tiene 6 columnas
    if len(df.columns) == 6 and "movimientos" in cols[0]:
        return "santander_real"

    if "debito" in cols_str and "credito" in cols_str:
        return "galicia"
    if "fecha operacion" in cols_str or "nro comprobante" in cols_str:
        return "santander"
    if "monto bruto" in cols_str or "comision mp" in cols_str or "tipo operacion" in cols_str:
        return "mercadopago"
    return "desconocido"


def normalizar(df: pd.DataFrame, banco: str = None) -> pd.DataFrame:
    """Normaliza un extracto bancario al formato unificado."""
    if banco is None:
        banco = detectar_banco(df)
    if banco not in NORMALIZADORES:
        raise ValueError(f"Banco no soportado: {banco}. Opciones: {list(NORMALIZADORES.keys())}")
    return NORMALIZADORES[banco](df)
