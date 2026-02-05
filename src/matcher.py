"""
Motor de matching - Cruza movimientos bancarios contra datos de Contagram.
Implementa 3 niveles: Automático, Probable, Excepción.
"""
import pandas as pd
import re
from difflib import SequenceMatcher


def _similitud(a: str, b: str) -> float:
    """Calcula similitud entre dos strings (0 a 1)."""
    if not a or not b:
        return 0.0
    a = a.upper().strip()
    b = b.upper().strip()
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _extraer_nombre_banco(descripcion: str) -> str:
    """Extrae el nombre relevante de una descripción bancaria."""
    desc = descripcion.upper().strip()
    # Remover prefijos comunes
    prefijos = [
        "MERPAG\\*", "MP\\*", "MERCPAGO\\*", "MERPAGO ",
        "TRANSF ", "TRF CR ", "ACRED\\.TRANSF ", "CR\\.TRANSF ",
        "TRANSF\\.RECIB ", "TRANSF CR ", "ACRED TRANSF ", "CR TRANSF ",
        "PAG ",
    ]
    for p in prefijos:
        desc = re.sub(f"^{p}", "", desc)
    # Remover sufijos
    desc = re.sub(r"\s*-RET$", "", desc)
    return desc.strip()


def match_por_tabla_parametrica(
    movimiento: pd.Series,
    tabla_param: pd.DataFrame,
) -> dict:
    """
    Intenta matchear un movimiento usando la tabla paramétrica.
    Returns dict con resultado del match.
    """
    desc = str(movimiento.get("descripcion_normalizada", ""))
    desc_orig = str(movimiento.get("descripcion", ""))
    monto = movimiento.get("monto", 0)
    clasificacion = movimiento.get("clasificacion", "")

    # Filtrar tabla por tipo
    if clasificacion == "cobranza":
        filtro = tabla_param[tabla_param["tipo"] == "Cliente"]
    elif clasificacion == "pago_proveedor":
        filtro = tabla_param[tabla_param["tipo"] == "Proveedor"]
    else:
        filtro = tabla_param

    best_match = None
    best_score = 0

    nombre_banco = _extraer_nombre_banco(desc_orig)

    for _, param in filtro.iterrows():
        alias = str(param.get("alias_banco", "")).upper()
        nombre = str(param.get("nombre_contagram", "")).upper()
        alias_limpio = _extraer_nombre_banco(alias)

        # Score por alias en descripción normalizada o original
        if alias_limpio and (alias_limpio in desc or alias_limpio in desc_orig.upper()):
            score = 0.95
        elif nombre and (nombre in desc or nombre in desc_orig.upper()):
            score = 0.90
        else:
            # Similitud fuzzy contra nombre extraído del banco
            score_alias = _similitud(nombre_banco, alias_limpio)
            score_nombre = _similitud(nombre_banco, nombre)
            score = max(score_alias, score_nombre)
            # Boost si hay overlap parcial significativo
            if nombre_banco and len(nombre_banco) > 3:
                for word in nombre_banco.split():
                    if len(word) > 3 and word in nombre:
                        score = max(score, 0.85)
                        break

        if score > best_score:
            best_score = score
            best_match = param

    if best_match is None:
        return {
            "match_nivel": "excepcion",
            "confianza": 0,
            "entidad_match": None,
            "id_contagram": None,
            "nombre_contagram": None,
        }

    if best_score >= 0.80:
        nivel = "automatico"
    elif best_score >= 0.55:
        nivel = "probable"
    else:
        nivel = "excepcion"

    return {
        "match_nivel": nivel,
        "confianza": round(best_score * 100, 1),
        "entidad_match": best_match.get("tipo", ""),
        "id_contagram": best_match.get("id_contagram", ""),
        "nombre_contagram": best_match.get("nombre_contagram", ""),
        "cuit": best_match.get("cuit", ""),
    }


def match_contra_facturas(
    movimiento: pd.Series,
    match_info: dict,
    facturas: pd.DataFrame,
    tolerancia_monto: float = 0.05,
) -> dict:
    """
    Intenta matchear un movimiento contra facturas específicas de Contagram.
    """
    if match_info["match_nivel"] == "excepcion":
        return {**match_info, "factura_match": None, "diferencia_monto": None}

    id_contagram = match_info.get("id_contagram")
    monto = movimiento.get("monto", 0)

    # Buscar facturas del cliente/proveedor
    if movimiento.get("clasificacion") == "cobranza":
        id_col = "ID Cliente"
    else:
        id_col = "ID Proveedor"

    facturas_entidad = facturas[facturas[id_col] == id_contagram] if id_col in facturas.columns else pd.DataFrame()

    if facturas_entidad.empty:
        return {**match_info, "factura_match": None, "diferencia_monto": None}

    # Buscar factura que mejor matchee por monto
    best_factura = None
    best_diff = float("inf")
    nro_col = "Nro Factura" if "Nro Factura" in facturas.columns else "Nro OC"

    for _, f in facturas_entidad.iterrows():
        monto_factura = f.get("Monto Total", 0)
        diff = abs(monto - monto_factura)
        diff_pct = diff / monto_factura if monto_factura > 0 else float("inf")

        if diff_pct < best_diff:
            best_diff = diff_pct
            best_factura = {
                "nro_documento": f.get(nro_col, ""),
                "monto_factura": monto_factura,
                "diferencia": round(monto - monto_factura, 2),
                "diferencia_pct": round(diff_pct * 100, 2),
            }

    if best_factura and best_diff <= tolerancia_monto:
        return {
            **match_info,
            "factura_match": best_factura["nro_documento"],
            "monto_factura": best_factura["monto_factura"],
            "diferencia_monto": best_factura["diferencia"],
            "diferencia_pct": best_factura["diferencia_pct"],
        }
    elif best_factura:
        # Mantener el nivel de match de entidad; la diferencia de monto
        # se reporta como nota pero no downgradea el match del cliente
        return {
            **match_info,
            "factura_match": best_factura["nro_documento"],
            "monto_factura": best_factura["monto_factura"],
            "diferencia_monto": best_factura["diferencia"],
            "diferencia_pct": best_factura["diferencia_pct"],
            "nota": "Diferencia de monto - posible pago parcial o retención",
        }
    return {**match_info, "factura_match": None, "diferencia_monto": None}


def ejecutar_matching(
    extracto: pd.DataFrame,
    tabla_param: pd.DataFrame,
    ventas: pd.DataFrame,
    compras: pd.DataFrame,
) -> pd.DataFrame:
    """
    Ejecuta el matching completo sobre un extracto normalizado y clasificado.
    """
    resultados = []

    for idx, mov in extracto.iterrows():
        # Paso 1: Match por tabla paramétrica
        match_info = match_por_tabla_parametrica(mov, tabla_param)

        # Paso 2: Match contra facturas
        if mov.get("clasificacion") == "cobranza":
            match_info = match_contra_facturas(mov, match_info, ventas)
        elif mov.get("clasificacion") == "pago_proveedor":
            match_info = match_contra_facturas(mov, match_info, compras)
        elif mov.get("clasificacion") == "gasto_bancario":
            match_info["match_nivel"] = "gasto_bancario"
            match_info["nombre_contagram"] = "GASTO BANCARIO"

        resultado = {**mov.to_dict(), **match_info}
        resultados.append(resultado)

    return pd.DataFrame(resultados)
