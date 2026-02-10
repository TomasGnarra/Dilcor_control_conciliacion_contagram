"""
Motor de conciliacion para datos reales.
Usa CUIT como clave primaria + flags de medio de cobro + reglas de 3 niveles.

Niveles:
  - NIVEL 1 (MATCHED): CUIT ok + Santander puro + monto ok + fecha ok → automatica
  - NIVEL 2 (SUGGESTED): CUIT ok + multiples medios + monto ok → revision manual
  - NIVEL 3 (EXCLUDED): Caja GRANDE / sin CUIT / sin match
"""
import pandas as pd
from src.fuzzy_matcher import calcular_similitud


# ─── CONFIGURACION ──────────────────────────────────────────────────
REAL_CONFIG = {
    "tolerancia_monto_pct": 0.005,       # 0.5% tolerancia monto
    "tolerancia_monto_abs": 1.0,         # $1 tolerancia absoluta
    "ventana_dias_nivel1": 30,           # ±30 dias para nivel 1
    "ventana_dias_nivel2": 45,           # ±45 dias para nivel 2
    "umbral_fuzzy_nombre": 0.70,         # 70% similitud nombre para nivel 2
}


def _monto_match(monto_banco: float, monto_contagram: float, tol_pct: float, tol_abs: float) -> bool:
    """Verifica si dos montos coinciden dentro de tolerancia."""
    if monto_contagram == 0:
        return False
    diff_abs = abs(monto_banco - monto_contagram)
    diff_pct = diff_abs / monto_contagram
    return diff_pct <= tol_pct or diff_abs <= tol_abs


def _fecha_en_ventana(fecha_banco, fecha_contagram, dias: int) -> bool:
    """Verifica si dos fechas estan dentro de una ventana de dias."""
    if pd.isna(fecha_banco) or pd.isna(fecha_contagram):
        return True  # Si falta fecha, no penalizar
    try:
        diff = abs((pd.Timestamp(fecha_banco) - pd.Timestamp(fecha_contagram)).days)
        return diff <= dias
    except Exception:
        return True


def conciliar_real(
    extracto: pd.DataFrame,
    ventas: pd.DataFrame,
    config: dict = None,
) -> pd.DataFrame:
    """
    Concilia extracto bancario real contra ventas de Contagram.
    Usa CUIT como clave primaria, monto y fecha como validacion.

    Args:
        extracto: Extracto bancario normalizado (con cuit_banco, nombre_banco_extraido)
        ventas: Ventas Contagram normalizadas (con cuit_limpio, flags de medio)
        config: Override de REAL_CONFIG

    Returns:
        DataFrame con resultados de conciliacion
    """
    cfg = {**REAL_CONFIG, **(config or {})}

    # Solo conciliar ventas con estado "Cobrado" y que mencionen Santander
    ventas_santander = ventas[
        (ventas["contiene_santander"] == True) &
        (ventas.get("estado", pd.Series(dtype=str)).str.lower() != "vencido")
    ].copy() if "contiene_santander" in ventas.columns else ventas.copy()

    # Track ventas ya usadas para evitar doble conciliacion
    ventas_usadas = set()
    resultados = []

    # ─── Clasificar movimientos bancarios ────────────────────────────
    creditos = extracto[extracto["tipo"] == "CREDITO"].copy()
    debitos = extracto[extracto["tipo"] == "DEBITO"].copy()

    # ─── PASO 1: Conciliar creditos (cobranzas) ─────────────────────
    for idx, mov in creditos.iterrows():
        result = _conciliar_credito(mov, ventas_santander, ventas, ventas_usadas, cfg)
        resultados.append(result)

    # ─── PASO 2: Clasificar debitos ─────────────────────────────────
    for idx, mov in debitos.iterrows():
        result = _clasificar_debito(mov)
        resultados.append(result)

    df = pd.DataFrame(resultados)

    # Mapear a match_nivel para compatibilidad con dashboard existente
    status_to_nivel = {
        "MATCHED": "match_exacto",
        "SUGGESTED": "probable_duda_id",
        "EXCLUDED": "no_match",
    }
    if "conciliation_status" in df.columns:
        df["match_nivel"] = df["conciliation_status"].map(status_to_nivel).fillna("no_match")

    return df


def _conciliar_credito(
    mov: pd.Series,
    ventas_santander: pd.DataFrame,
    ventas_todas: pd.DataFrame,
    ventas_usadas: set,
    cfg: dict,
) -> dict:
    """Concilia un credito bancario contra ventas de Contagram."""
    base = {
        **mov.to_dict(),
        "clasificacion": "cobranza",
    }

    cuit_banco = mov.get("cuit_banco", "")
    monto = mov.get("monto", 0)
    fecha_banco = mov.get("fecha")
    nombre_banco = mov.get("nombre_banco_extraido", "")

    # ─── Sin CUIT: no podemos conciliar con certeza ─────────────────
    if not cuit_banco:
        return {
            **base,
            "conciliation_status": "EXCLUDED",
            "conciliation_tag": "SIN_CUIT_BANCO",
            "conciliation_confidence": "BAJA",
            "conciliation_reason": "No se pudo extraer CUIT de la descripcion bancaria",
            "nombre_contagram": "",
            "factura_match": None,
            "diferencia_monto": None,
            "confianza": 0,
            "tipo_match_monto": None,
            "facturas_count": 0,
        }

    # ─── Buscar ventas con mismo CUIT ───────────────────────────────
    # Primero en ventas con Santander, luego en todas
    ventas_cuit = ventas_santander[
        (ventas_santander["cuit_limpio"] == cuit_banco) &
        (~ventas_santander.index.isin(ventas_usadas))
    ]

    if ventas_cuit.empty:
        # Buscar en TODAS las ventas (quizas no tiene "Santander" en medio)
        ventas_cuit = ventas_todas[
            (ventas_todas["cuit_limpio"] == cuit_banco) &
            (~ventas_todas.index.isin(ventas_usadas))
        ]

    if ventas_cuit.empty:
        # CUIT no encontrado en Contagram
        return {
            **base,
            "conciliation_status": "EXCLUDED",
            "conciliation_tag": "CUIT_SIN_VENTA",
            "conciliation_confidence": "BAJA",
            "conciliation_reason": f"CUIT {cuit_banco} no encontrado en ventas Contagram",
            "nombre_contagram": "",
            "factura_match": None,
            "diferencia_monto": None,
            "confianza": 0,
            "tipo_match_monto": None,
            "facturas_count": 0,
        }

    # ─── Buscar match por monto ─────────────────────────────────────
    tol_pct = cfg["tolerancia_monto_pct"]
    tol_abs = cfg["tolerancia_monto_abs"]

    # 1:1 match por monto exacto
    best = None
    best_diff = float("inf")

    for vidx, venta in ventas_cuit.iterrows():
        monto_venta = venta.get("Monto Total", 0)
        if monto_venta <= 0:
            continue

        diff = abs(monto - monto_venta)
        if _monto_match(monto, monto_venta, tol_pct, tol_abs) and diff < best_diff:
            best = (vidx, venta, diff)
            best_diff = diff

    if best:
        vidx, venta, diff = best
        return _evaluar_match(mov, base, venta, vidx, diff, ventas_usadas, cfg, tipo_monto="directo")

    # Sum matching: sumar varias ventas del mismo cliente
    sum_result = _buscar_sum_match(monto, ventas_cuit, ventas_usadas, tol_pct, tol_abs)
    if sum_result:
        return _evaluar_sum_match(mov, base, sum_result, ventas_usadas, cfg)

    # CUIT encontrado pero monto no matchea
    primer_venta = ventas_cuit.iloc[0]
    nombre_cliente = primer_venta.get("Nombre", "")
    return {
        **base,
        "conciliation_status": "SUGGESTED",
        "conciliation_tag": "CUIT_OK_MONTO_DIFF",
        "conciliation_confidence": "MEDIA",
        "conciliation_reason": (
            f"CUIT coincide con {nombre_cliente}, pero monto ${monto:,.2f} "
            f"no matchea con ninguna venta"
        ),
        "nombre_contagram": nombre_cliente,
        "id_contagram": primer_venta.get("ID Cliente", ""),
        "factura_match": None,
        "diferencia_monto": None,
        "confianza": 60,
        "tipo_match_monto": None,
        "facturas_count": 0,
    }


def _evaluar_match(
    mov: pd.Series, base: dict, venta: pd.Series, vidx,
    diff: float, ventas_usadas: set, cfg: dict, tipo_monto: str,
) -> dict:
    """Evalua un match 1:1 y asigna nivel segun reglas de medio de cobro."""
    monto = mov.get("monto", 0)
    fecha_banco = mov.get("fecha")
    nombre_banco = mov.get("nombre_banco_extraido", "")

    nombre_cliente = venta.get("Nombre", "")
    medio = venta.get("medio_cobro", "")
    es_santander_puro = venta.get("es_santander_puro", False)
    es_pago_unico = venta.get("es_pago_unico", False)
    es_medio_homogeneo = venta.get("es_medio_homogeneo", False)
    contiene_caja = venta.get("contiene_caja_grande", False)
    fecha_venta = venta.get("fecha_emision")
    monto_venta = venta.get("Monto Total", 0)
    nro_factura = venta.get("Nro Factura", "")

    diferencia = round(monto - monto_venta, 2)

    # ─── NIVEL 1: MATCHED (alta certeza) ────────────────────────────
    if contiene_caja:
        # Caja GRANDE → nunca auto-conciliar
        ventas_usadas.add(vidx)
        return {
            **base,
            "conciliation_status": "EXCLUDED",
            "conciliation_tag": "MIXTO_CAJA_Y_BANCO",
            "conciliation_confidence": "BAJA",
            "conciliation_reason": (
                f"Venta de {nombre_cliente} tiene Caja GRANDE en medio de cobro. "
                f"No se puede determinar porcion Santander. Medio: {medio}"
            ),
            "nombre_contagram": nombre_cliente,
            "id_contagram": venta.get("ID Cliente", ""),
            "factura_match": nro_factura,
            "diferencia_monto": diferencia,
            "confianza": 20,
            "tipo_match_monto": tipo_monto,
            "facturas_count": 1,
        }

    en_ventana_1 = _fecha_en_ventana(fecha_banco, fecha_venta, cfg["ventana_dias_nivel1"])

    if (es_santander_puro or (es_pago_unico and venta.get("contiene_santander", False))) and en_ventana_1:
        # Auto-conciliar: Santander puro (o unico) + monto ok + fecha ok
        tag = "AUTO_EXACTA_SANTANDER" if es_pago_unico else "AUTO_SANTANDER_MEDIO_DUPLICADO"
        ventas_usadas.add(vidx)
        return {
            **base,
            "conciliation_status": "MATCHED",
            "conciliation_tag": tag,
            "conciliation_confidence": "ALTA",
            "conciliation_reason": (
                f"CUIT + monto exacto + medio Santander puro. "
                f"Cliente: {nombre_cliente}, Factura: {nro_factura}"
            ),
            "nombre_contagram": nombre_cliente,
            "id_contagram": venta.get("ID Cliente", ""),
            "factura_match": nro_factura,
            "diferencia_monto": diferencia,
            "confianza": 95,
            "tipo_match_monto": tipo_monto,
            "facturas_count": 1,
        }

    # ─── NIVEL 2: SUGGESTED (revision manual) ───────────────────────
    en_ventana_2 = _fecha_en_ventana(fecha_banco, fecha_venta, cfg["ventana_dias_nivel2"])
    if en_ventana_2:
        tag = "PROBABLE_MULTIPLE_MEDIO"
        confianza = 75
        razon = (
            f"CUIT + monto coincide, pero medio de cobro tiene multiples metodos. "
            f"Cliente: {nombre_cliente}, Medio: {medio}"
        )
        if es_medio_homogeneo:
            tag = "PROBABLE_MEDIO_HOMOGENEO"
            confianza = 85
            razon = (
                f"CUIT + monto coincide, medio duplicado (mismo Santander repetido). "
                f"Cliente: {nombre_cliente}"
            )

        ventas_usadas.add(vidx)
        return {
            **base,
            "conciliation_status": "SUGGESTED",
            "conciliation_tag": tag,
            "conciliation_confidence": "MEDIA",
            "conciliation_reason": razon,
            "nombre_contagram": nombre_cliente,
            "id_contagram": venta.get("ID Cliente", ""),
            "factura_match": nro_factura,
            "diferencia_monto": diferencia,
            "confianza": confianza,
            "tipo_match_monto": tipo_monto,
            "facturas_count": 1,
        }

    # Fuera de ventana temporal
    ventas_usadas.add(vidx)
    return {
        **base,
        "conciliation_status": "SUGGESTED",
        "conciliation_tag": "FUERA_VENTANA_TEMPORAL",
        "conciliation_confidence": "MEDIA",
        "conciliation_reason": (
            f"CUIT + monto coincide pero fecha fuera de ventana. "
            f"Banco: {fecha_banco}, Venta: {fecha_venta}. Cliente: {nombre_cliente}"
        ),
        "nombre_contagram": nombre_cliente,
        "id_contagram": venta.get("ID Cliente", ""),
        "factura_match": nro_factura,
        "diferencia_monto": diferencia,
        "confianza": 60,
        "tipo_match_monto": tipo_monto,
        "facturas_count": 1,
    }


def _buscar_sum_match(
    monto_banco: float,
    ventas_cuit: pd.DataFrame,
    ventas_usadas: set,
    tol_pct: float,
    tol_abs: float,
) -> dict | None:
    """Busca combinacion de ventas del mismo CUIT que sumen el monto bancario."""
    from itertools import combinations

    disponibles = []
    for vidx, v in ventas_cuit.iterrows():
        if vidx not in ventas_usadas:
            m = v.get("Monto Total", 0)
            if m > 0:
                disponibles.append({"idx": vidx, "venta": v, "monto": m})

    if len(disponibles) < 2:
        return None

    # Suma total
    total = sum(d["monto"] for d in disponibles)
    if total > 0 and _monto_match(monto_banco, total, tol_pct, tol_abs):
        return {
            "ventas": disponibles,
            "suma": total,
            "diferencia": round(monto_banco - total, 2),
            "tipo": "suma_total",
        }

    # Subconjuntos de 2 a min(6, n-1)
    n = len(disponibles)
    max_size = min(n, 6)
    disponibles.sort(key=lambda x: x["monto"], reverse=True)

    for size in range(2, max_size + 1):
        for combo in combinations(disponibles, size):
            combo_sum = sum(d["monto"] for d in combo)
            if combo_sum > 0 and _monto_match(monto_banco, combo_sum, tol_pct, tol_abs):
                return {
                    "ventas": list(combo),
                    "suma": combo_sum,
                    "diferencia": round(monto_banco - combo_sum, 2),
                    "tipo": "suma_parcial",
                }

    return None


def _evaluar_sum_match(
    mov: pd.Series, base: dict, sum_result: dict,
    ventas_usadas: set, cfg: dict,
) -> dict:
    """Evalua un sum match y asigna nivel."""
    ventas_list = sum_result["ventas"]
    primera = ventas_list[0]["venta"]
    nombre_cliente = primera.get("Nombre", "")

    # Verificar flags de todas las ventas en el sum
    todas_santander_puro = all(v["venta"].get("es_santander_puro", False) for v in ventas_list)
    alguna_caja = any(v["venta"].get("contiene_caja_grande", False) for v in ventas_list)

    facturas = " + ".join(str(v["venta"].get("Nro Factura", "")) for v in ventas_list)
    count = len(ventas_list)

    # Marcar todas como usadas
    for v in ventas_list:
        ventas_usadas.add(v["idx"])

    if alguna_caja:
        return {
            **base,
            "conciliation_status": "EXCLUDED",
            "conciliation_tag": "SUM_MIXTO_CAJA",
            "conciliation_confidence": "BAJA",
            "conciliation_reason": f"Suma de {count} ventas matchea pero alguna incluye Caja GRANDE",
            "nombre_contagram": nombre_cliente,
            "id_contagram": primera.get("ID Cliente", ""),
            "factura_match": facturas,
            "diferencia_monto": sum_result["diferencia"],
            "confianza": 25,
            "tipo_match_monto": sum_result["tipo"],
            "facturas_count": count,
        }

    if todas_santander_puro:
        return {
            **base,
            "conciliation_status": "MATCHED",
            "conciliation_tag": "AUTO_SUMA_SANTANDER",
            "conciliation_confidence": "ALTA",
            "conciliation_reason": (
                f"CUIT + suma de {count} ventas Santander puro = ${sum_result['suma']:,.2f}. "
                f"Cliente: {nombre_cliente}"
            ),
            "nombre_contagram": nombre_cliente,
            "id_contagram": primera.get("ID Cliente", ""),
            "factura_match": facturas,
            "diferencia_monto": sum_result["diferencia"],
            "confianza": 90,
            "tipo_match_monto": sum_result["tipo"],
            "facturas_count": count,
        }

    return {
        **base,
        "conciliation_status": "SUGGESTED",
        "conciliation_tag": "PROBABLE_SUMA_MULTIPLE_MEDIO",
        "conciliation_confidence": "MEDIA",
        "conciliation_reason": (
            f"CUIT + suma de {count} ventas = ${sum_result['suma']:,.2f}, "
            f"pero no todas son Santander puro. Cliente: {nombre_cliente}"
        ),
        "nombre_contagram": nombre_cliente,
        "id_contagram": primera.get("ID Cliente", ""),
        "factura_match": facturas,
        "diferencia_monto": sum_result["diferencia"],
        "confianza": 70,
        "tipo_match_monto": sum_result["tipo"],
        "facturas_count": count,
    }


def _clasificar_debito(mov: pd.Series) -> dict:
    """Clasifica un debito bancario."""
    desc = str(mov.get("descripcion", "")).upper()
    cod = mov.get("cod_transaccion", 0)

    # Gastos bancarios: impuestos, comisiones
    codigos_gasto = {3254, 4637, 4633, 1743, 3083, 2233}
    patrones_gasto = ["IMPUESTO", "IVA", "SIRCREB", "IIBB", "RETENCION", "COMISION"]

    if cod in codigos_gasto or any(p in desc for p in patrones_gasto):
        clasificacion = "gasto_bancario"
        tag = "GASTO_BANCARIO"
    else:
        clasificacion = "pago_proveedor"
        tag = "DEBITO_PROVEEDOR"

    return {
        **mov.to_dict(),
        "clasificacion": clasificacion,
        "conciliation_status": "EXCLUDED",
        "conciliation_tag": tag,
        "conciliation_confidence": "BAJA" if clasificacion == "gasto_bancario" else "MEDIA",
        "conciliation_reason": f"Debito: {desc[:80]}",
        "match_nivel": "gasto_bancario" if clasificacion == "gasto_bancario" else "no_match",
        "nombre_contagram": "GASTO BANCARIO" if clasificacion == "gasto_bancario" else "",
        "factura_match": None,
        "diferencia_monto": None,
        "confianza": 0,
        "tipo_match_monto": None,
        "facturas_count": 0,
    }
