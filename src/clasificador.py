"""
Clasificador de movimientos bancarios.
Determina si cada movimiento es Cobranza, Pago a Proveedor, Gasto Bancario u Otro.
"""
import pandas as pd
import re

# Patrones para detectar gastos/comisiones bancarias
PATRONES_GASTO_BANCARIO = [
    r"COMISION",
    r"IMP\s+DEBITO",
    r"IMP\s+CREDITO",
    r"IVA\s+COMIS",
    r"SELLADO",
    r"MANTENIMIENTO\s+CTA",
    r"CARGO\s+MENSUAL",
    r"SEGURO\s+CTA",
]

# Patrones de pago a proveedor
PATRONES_PAGO = [
    r"^PAG\s",
    r"^PAGO\s",
    r"TRANSF\s+ENV",
    r"DB\s+TRANSF",
    r"DEBIN",
]


def clasificar_movimiento(row: pd.Series) -> str:
    """
    Clasifica un movimiento bancario normalizado.
    Returns: 'cobranza', 'pago_proveedor', 'gasto_bancario', 'otro'
    """
    desc = str(row.get("descripcion_normalizada", "")).upper()
    tipo = str(row.get("tipo", "")).upper()

    # Gastos bancarios
    for patron in PATRONES_GASTO_BANCARIO:
        if re.search(patron, desc):
            return "gasto_bancario"

    # Si es crédito -> cobranza (dinero que entra)
    if tipo == "CREDITO":
        return "cobranza"

    # Si es débito, verificar si es pago a proveedor
    if tipo == "DEBITO":
        for patron in PATRONES_PAGO:
            if re.search(patron, desc):
                return "pago_proveedor"
        # Débito sin patrón claro
        return "pago_proveedor"

    return "otro"


def clasificar_extracto(df: pd.DataFrame) -> pd.DataFrame:
    """Clasifica todos los movimientos de un extracto normalizado."""
    df = df.copy()
    df["clasificacion"] = df.apply(clasificar_movimiento, axis=1)
    return df
