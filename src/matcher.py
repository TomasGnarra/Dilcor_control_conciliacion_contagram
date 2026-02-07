"""
Motor de matching - Cruza movimientos bancarios contra datos de Contagram.
Implementa lógica ternaria:
  - Match Exacto: ID exacto + monto dentro de tolerancia
  - Match Probable (A - Duda de ID): Monto coincide pero alias es fuzzy
  - Match Probable (B - Diferencia de Cambio): ID exacto pero monto difiere
  - No Match: Sin coincidencia

Umbrales configurables vía diccionario MATCH_CONFIG.
"""
import pandas as pd
import re
from difflib import SequenceMatcher


# ─── UMBRALES CONFIGURABLES ─────────────────────────────────────────
# Estos valores se pueden sobreescribir desde Streamlit (sidebar)
MATCH_CONFIG = {
    # Umbral mínimo de similitud de alias para considerar match exacto de ID
    "umbral_id_exacto": 0.80,
    # Umbral mínimo de similitud de alias para match probable (duda de ID)
    "umbral_id_probable": 0.55,
    # Tolerancia de monto para match exacto (porcentaje, ej: 0.005 = 0.5%)
    "tolerancia_monto_exacto_pct": 0.005,
    # Tolerancia de monto para match probable - diferencia de cambio (porcentaje)
    "tolerancia_monto_probable_pct": 0.01,
    # Tolerancia de monto absoluta para match probable (en pesos ARS)
    "tolerancia_monto_probable_abs": 500.0,
}


def get_config(key: str) -> float:
    """Obtiene valor de config. Permite override en runtime."""
    return MATCH_CONFIG.get(key, 0)


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
    prefijos = [
        "MERPAG\\*", "MP\\*", "MERCPAGO\\*", "MERPAGO ",
        "TRANSF ", "TRF CR ", "ACRED\\.TRANSF ", "CR\\.TRANSF ",
        "TRANSF\\.RECIB ", "TRANSF CR ", "ACRED TRANSF ", "CR TRANSF ",
        "PAG ",
    ]
    for p in prefijos:
        desc = re.sub(f"^{p}", "", desc)
    desc = re.sub(r"\s*-RET$", "", desc)
    return desc.strip()


def _match_identidad(desc: str, desc_orig: str, nombre_banco: str,
                     alias_limpio: str, nombre: str) -> tuple[float, str]:
    """
    Evalúa match de identidad (alias/nombre).
    Returns: (score, tipo_match_id)
        tipo_match_id: 'exacto', 'fuzzy', 'none'
    """
    # Match exacto: alias aparece como substring en descripción
    if alias_limpio and (alias_limpio in desc or alias_limpio in desc_orig.upper()):
        return 0.95, "exacto"
    if nombre and (nombre in desc or nombre in desc_orig.upper()):
        return 0.90, "exacto"

    # Fuzzy match
    score_alias = _similitud(nombre_banco, alias_limpio)
    score_nombre = _similitud(nombre_banco, nombre)
    score = max(score_alias, score_nombre)

    # Boost por overlap parcial significativo
    if nombre_banco and len(nombre_banco) > 3:
        for word in nombre_banco.split():
            if len(word) > 3 and word in nombre:
                score = max(score, 0.85)
                break

    if score >= get_config("umbral_id_exacto"):
        return score, "exacto"
    elif score >= get_config("umbral_id_probable"):
        return score, "fuzzy"
    else:
        return score, "none"


def _match_monto(monto_banco: float, monto_factura: float) -> tuple[str, float, float]:
    """
    Evalúa match de monto.
    Returns: (tipo_match_monto, diferencia_abs, diferencia_pct)
        tipo_match_monto: 'exacto', 'probable', 'no_match'
    """
    if monto_factura == 0:
        return "no_match", abs(monto_banco), 100.0

    diff_abs = abs(monto_banco - monto_factura)
    diff_pct = diff_abs / monto_factura

    tol_exacto = get_config("tolerancia_monto_exacto_pct")
    tol_prob_pct = get_config("tolerancia_monto_probable_pct")
    tol_prob_abs = get_config("tolerancia_monto_probable_abs")

    if diff_pct <= tol_exacto:
        return "exacto", diff_abs, diff_pct
    elif diff_pct <= tol_prob_pct or diff_abs <= tol_prob_abs:
        return "probable", diff_abs, diff_pct
    else:
        return "no_match", diff_abs, diff_pct


def _match_monto_suma(monto_banco: float, facturas_entidad: pd.DataFrame,
                      nro_col: str, tolerancia_pct: float) -> dict | None:
    """
    Busca combinacion de facturas que sumen el monto bancario (± tolerancia).
    Estrategia: 1) suma total, 2) subconjuntos de 2 a max_size facturas.
    """
    from itertools import combinations

    facturas_list = []
    for _, f in facturas_entidad.iterrows():
        m = float(f.get("Monto Total", 0))
        if m > 0:
            facturas_list.append({"nro": str(f.get(nro_col, "")), "monto": m})

    if len(facturas_list) < 2:
        return None

    # 1. Suma total de todas las facturas
    total = sum(f["monto"] for f in facturas_list)
    if total > 0:
        diff_pct = abs(monto_banco - total) / total
        if diff_pct <= tolerancia_pct:
            return {
                "facturas": facturas_list,
                "suma": round(total, 2),
                "diferencia": round(monto_banco - total, 2),
                "diferencia_pct": round(diff_pct * 100, 2),
                "tipo": "suma_total",
                "count": len(facturas_list),
            }

    # 2. Subconjuntos (limitar segun cantidad de facturas)
    n = len(facturas_list)
    if n <= 12:
        max_size = min(n - 1, 8)
    elif n <= 18:
        max_size = min(n - 1, 6)
    else:
        max_size = min(n - 1, 5)

    facturas_list.sort(key=lambda x: x["monto"], reverse=True)

    for size in range(2, max_size + 1):
        for combo in combinations(facturas_list, size):
            combo_sum = sum(f["monto"] for f in combo)
            if combo_sum > 0:
                diff_pct = abs(monto_banco - combo_sum) / combo_sum
                if diff_pct <= tolerancia_pct:
                    return {
                        "facturas": list(combo),
                        "suma": round(combo_sum, 2),
                        "diferencia": round(monto_banco - combo_sum, 2),
                        "diferencia_pct": round(diff_pct * 100, 2),
                        "tipo": "suma_parcial",
                        "count": size,
                    }

    return None


def match_por_tabla_parametrica(
    movimiento: pd.Series,
    tabla_param: pd.DataFrame,
) -> dict:
    """
    Intenta matchear un movimiento usando la tabla paramétrica.
    """
    desc = str(movimiento.get("descripcion_normalizada", ""))
    desc_orig = str(movimiento.get("descripcion", ""))
    monto = movimiento.get("monto", 0)
    clasificacion = movimiento.get("clasificacion", "")

    if clasificacion == "cobranza":
        filtro = tabla_param[tabla_param["tipo"] == "Cliente"]
    elif clasificacion == "pago_proveedor":
        filtro = tabla_param[tabla_param["tipo"] == "Proveedor"]
    else:
        filtro = tabla_param

    best_match = None
    best_score = 0
    best_tipo_id = "none"

    nombre_banco = _extraer_nombre_banco(desc_orig)

    for _, param in filtro.iterrows():
        alias = str(param.get("alias_banco", "")).upper()
        nombre = str(param.get("nombre_contagram", "")).upper()
        alias_limpio = _extraer_nombre_banco(alias)

        score, tipo_id = _match_identidad(desc, desc_orig, nombre_banco,
                                          alias_limpio, nombre)

        if score > best_score:
            best_score = score
            best_match = param
            best_tipo_id = tipo_id

    if best_match is None or best_tipo_id == "none":
        return {
            "match_nivel": "no_match",
            "match_detalle": "Sin coincidencia en tabla parametrica",
            "confianza": 0,
            "entidad_match": None,
            "id_contagram": None,
            "nombre_contagram": None,
            "tipo_match_id": "none",
        }

    return {
        "match_nivel": "pendiente",  # Se resuelve en match_contra_facturas
        "confianza": round(best_score * 100, 1),
        "entidad_match": best_match.get("tipo", ""),
        "id_contagram": best_match.get("id_contagram", ""),
        "nombre_contagram": best_match.get("nombre_contagram", ""),
        "cuit": best_match.get("cuit", ""),
        "tipo_match_id": best_tipo_id,
    }


def match_contra_facturas(
    movimiento: pd.Series,
    match_info: dict,
    facturas: pd.DataFrame,
) -> dict:
    """
    Cruza un movimiento contra facturas y determina el nivel ternario final:
      - match_exacto: ID exacto + monto exacto
      - probable_duda_id: Monto coincide pero ID es fuzzy
      - probable_dif_cambio: ID exacto pero monto difiere
      - no_match: nada coincide
    """
    if match_info["match_nivel"] == "no_match":
        return {**match_info, "factura_match": None, "diferencia_monto": None,
                "diferencia_pct": None, "match_detalle": "Sin match de identidad",
                "tipo_match_monto": None, "facturas_count": 0}

    id_contagram = match_info.get("id_contagram")
    monto = movimiento.get("monto", 0)
    tipo_id = match_info.get("tipo_match_id", "none")

    id_col = "ID Cliente" if movimiento.get("clasificacion") == "cobranza" else "ID Proveedor"
    facturas_entidad = facturas[facturas[id_col] == id_contagram] if id_col in facturas.columns else pd.DataFrame()

    if facturas_entidad.empty:
        # Tiene match de ID pero no hay facturas => requiere revision
        if tipo_id == "exacto":
            nivel = "probable_dif_cambio"
            detalle = "Proveedor/cliente identificado, sin factura pendiente en Contagram"
        else:
            nivel = "probable_duda_id"
            detalle = "Alias similar pero sin factura pendiente en Contagram"
        return {**match_info, "match_nivel": nivel, "match_detalle": detalle,
                "factura_match": None, "diferencia_monto": None, "diferencia_pct": None,
                "tipo_match_monto": None, "facturas_count": 0}

    # Buscar mejor factura por monto
    nro_col = "Nro Factura" if "Nro Factura" in facturas.columns else "Nro OC"
    best_factura = None
    best_monto_tipo = "no_match"
    best_diff_abs = float("inf")
    best_diff_pct = float("inf")

    for _, f in facturas_entidad.iterrows():
        monto_factura = f.get("Monto Total", 0)
        tipo_monto, diff_abs, diff_pct = _match_monto(monto, monto_factura)

        # Prioridad: exacto > probable > no_match, luego menor diff
        prioridad = {"exacto": 0, "probable": 1, "no_match": 2}
        curr_pri = prioridad.get(tipo_monto, 2)
        best_pri = prioridad.get(best_monto_tipo, 2)

        if curr_pri < best_pri or (curr_pri == best_pri and diff_abs < best_diff_abs):
            best_monto_tipo = tipo_monto
            best_diff_abs = diff_abs
            best_diff_pct = diff_pct
            best_factura = {
                "nro_documento": f.get(nro_col, ""),
                "monto_factura": monto_factura,
                "diferencia": round(monto - monto_factura, 2),
                "diferencia_pct": round(diff_pct * 100, 2),
            }

    if best_factura is None:
        nivel = "match_exacto" if tipo_id == "exacto" else "probable_duda_id"
        return {**match_info, "match_nivel": nivel, "match_detalle": "Sin factura que matchee por monto",
                "factura_match": None, "diferencia_monto": None, "diferencia_pct": None,
                "tipo_match_monto": None, "facturas_count": 0}

    # ─── Resolución ternaria final (con sum matching) ───
    tipo_match_monto = None
    facturas_count = 1

    if tipo_id == "exacto" and best_monto_tipo == "exacto":
        # Caso ideal: ID exacto + monto exacto 1:1
        nivel = "match_exacto"
        tipo_match_monto = "directo"
        detalle = "ID exacto + monto exacto (1:1)"

    elif tipo_id == "exacto" and best_monto_tipo in ("probable", "no_match"):
        # ID exacto pero monto no matchea 1:1 → intentar suma de facturas
        sum_result = _match_monto_suma(
            monto, facturas_entidad, nro_col,
            get_config("tolerancia_monto_exacto_pct"),
        )
        if sum_result:
            nivel = "match_exacto"
            tipo_match_monto = sum_result["tipo"]
            facturas_count = sum_result["count"]
            facturas_str = " + ".join(f["nro"] for f in sum_result["facturas"])
            best_factura = {
                "nro_documento": facturas_str,
                "monto_factura": sum_result["suma"],
                "diferencia": sum_result["diferencia"],
                "diferencia_pct": sum_result["diferencia_pct"],
            }
            tipo_label = "todas las facturas" if sum_result["tipo"] == "suma_total" else f"{sum_result['count']} facturas"
            detalle = f"ID exacto + suma de {tipo_label}"
        else:
            # Sum matching fallo → probable_dif_cambio
            nivel = "probable_dif_cambio"
            if best_monto_tipo == "probable":
                detalle = f"ID exacto, mejor factura dif ${best_factura['diferencia']:+,.2f} ({best_factura['diferencia_pct']:.2f}%)"
            else:
                detalle = f"ID exacto, sin coincidencia de monto (mejor dif ${best_factura['diferencia']:+,.2f})"

    elif tipo_id == "fuzzy" and best_monto_tipo in ("exacto", "probable"):
        nivel = "probable_duda_id"
        tipo_match_monto = "directo"
        detalle = f"Alias fuzzy (conf {match_info['confianza']}%), monto {'coincide' if best_monto_tipo == 'exacto' else 'aproximado'}"

    else:
        nivel = "no_match"
        detalle = "Sin coincidencia suficiente"

    return {
        **match_info,
        "match_nivel": nivel,
        "match_detalle": detalle,
        "factura_match": best_factura["nro_documento"],
        "monto_factura": best_factura["monto_factura"],
        "diferencia_monto": best_factura["diferencia"],
        "diferencia_pct": best_factura["diferencia_pct"],
        "tipo_match_monto": tipo_match_monto,
        "facturas_count": facturas_count,
    }


def ejecutar_matching(
    extracto: pd.DataFrame,
    tabla_param: pd.DataFrame,
    ventas: pd.DataFrame,
    compras: pd.DataFrame,
    config: dict = None,
) -> pd.DataFrame:
    """
    Ejecuta el matching completo sobre un extracto normalizado y clasificado.
    config: dict opcional para override de MATCH_CONFIG.
    """
    if config:
        MATCH_CONFIG.update(config)

    resultados = []

    for idx, mov in extracto.iterrows():
        match_info = match_por_tabla_parametrica(mov, tabla_param)

        if mov.get("clasificacion") == "cobranza":
            match_info = match_contra_facturas(mov, match_info, ventas)
        elif mov.get("clasificacion") == "pago_proveedor":
            match_info = match_contra_facturas(mov, match_info, compras)
        elif mov.get("clasificacion") == "gasto_bancario":
            match_info["match_nivel"] = "gasto_bancario"
            match_info["match_detalle"] = "Gasto/comision bancaria"
            match_info["nombre_contagram"] = "GASTO BANCARIO"

        resultado = {**mov.to_dict(), **match_info}
        resultados.append(resultado)

    return pd.DataFrame(resultados)
