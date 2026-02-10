"""
Normalizador de datos de Contagram (ventas/compras reales).
Transforma al formato esperado por el motor + genera flags de medio de cobro.
"""
import pandas as pd
import re


def _normalizar_cuit(cuit_raw) -> str:
    """Normaliza CUIT: quita guiones y espacios. '30-71836775-8' -> '30718367758'."""
    if pd.isna(cuit_raw):
        return ""
    return re.sub(r"[^0-9]", "", str(cuit_raw))


def _analizar_medio_cobro(medio: str) -> dict:
    """Analiza el campo 'Medio de Cobro' y genera flags derivados."""
    if pd.isna(medio) or not str(medio).strip():
        return {
            "es_pago_unico": False,
            "es_pago_multiples_medios": False,
            "es_medio_homogeneo": False,
            "contiene_santander": False,
            "contiene_caja_grande": False,
            "es_santander_puro": False,
            "medios_count": 0,
        }

    medio = str(medio).strip()
    partes = [p.strip() for p in medio.split(" - ") if p.strip()]
    n = len(partes)

    partes_norm = [p.lower().strip() for p in partes]

    es_pago_unico = (n == 1)
    es_pago_multiples = (n > 1)

    # Medio homogeneo: todas las partes son iguales (error de registro duplicado)
    es_medio_homogeneo = es_pago_multiples and len(set(partes_norm)) == 1

    contiene_santander = any("santander" in p for p in partes_norm)
    contiene_caja_grande = any("caja grande" in p for p in partes_norm)

    # Santander puro: solo medios Santander, sin Caja GRANDE
    medios_santander = [p for p in partes_norm if "santander" in p]
    es_santander_puro = (
        contiene_santander
        and not contiene_caja_grande
        and len(medios_santander) == n
    )

    medios_caja = [p for p in partes_norm if "caja grande" in p]
    medios_otros = [p for p in partes_norm if "santander" not in p and "caja grande" not in p]

    return {
        "es_pago_unico": es_pago_unico,
        "es_pago_multiples_medios": es_pago_multiples,
        "es_medio_homogeneo": es_medio_homogeneo,
        "contiene_santander": contiene_santander,
        "contiene_caja_grande": contiene_caja_grande,
        "es_santander_puro": es_santander_puro,
        "medios_count": n,
        "santander_parts_count": len(medios_santander),
        "caja_grande_parts_count": len(medios_caja),
        "otros_parts_count": len(medios_otros),
    }


def normalizar_ventas_contagram(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza DataFrame de ventas de Contagram.
    Detecta si es formato real (con 'Cobrado', 'Medio de Cobro') o formato test.
    Retorna DataFrame con columnas estandar + flags.
    """
    cols_lower = [c.lower().strip() for c in df.columns]

    if "cobrado" in cols_lower or "medio de cobro" in cols_lower:
        return _normalizar_ventas_real(df)
    else:
        # Formato test: ya compatible, agregar flags vacios
        df = df.copy()
        for flag in ["es_pago_unico", "es_pago_multiples_medios", "es_medio_homogeneo",
                      "contiene_santander", "contiene_caja_grande", "es_santander_puro"]:
            if flag not in df.columns:
                df[flag] = False
        if "cuit_limpio" not in df.columns:
            df["cuit_limpio"] = ""
        if "medio_cobro" not in df.columns:
            df["medio_cobro"] = ""
        return df


def _normalizar_ventas_real(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza ventas reales de Contagram al formato del matcher."""
    rows = []

    for _, r in df.iterrows():
        medio = str(r.get("Medio de Cobro", "")) if pd.notna(r.get("Medio de Cobro")) else ""
        flags = _analizar_medio_cobro(medio)

        cuit_raw = r.get("CUIT", "")
        cuit_limpio = _normalizar_cuit(cuit_raw)

        cobrado = float(r.get("Cobrado", 0)) if pd.notna(r.get("Cobrado")) else 0.0
        total_venta = float(r.get("Total Venta", 0)) if pd.notna(r.get("Total Venta")) else 0.0

        # Manejar columnas con/sin acentos
        fecha_raw = r.get("Emisión", r.get("Emision"))
        fecha_emision = pd.to_datetime(fecha_raw, errors="coerce")

        nro_factura = r.get("N° de Factura", r.get("N de Factura", ""))

        rows.append({
            # Campos standard para el matcher
            "ID Cliente": str(r.get("Id", "")),
            "Nombre": str(r.get("Cliente", "")),
            "CUIT": str(cuit_raw) if pd.notna(cuit_raw) else "",
            "cuit_limpio": cuit_limpio,
            "Nro Factura": str(nro_factura) if pd.notna(nro_factura) else "",
            "Monto Total": cobrado,  # Usar Cobrado para matching
            "total_venta": total_venta,
            "fecha_emision": fecha_emision,
            "estado": str(r.get("Estado", "")),
            "tipo_comprobante": str(r.get("Tipo", "")) if pd.notna(r.get("Tipo")) else "",
            "medio_cobro": medio,
            # Flags
            **flags,
        })

    return pd.DataFrame(rows)
