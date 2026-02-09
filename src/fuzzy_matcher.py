"""
Modulo de fuzzy matching profesional basado en rapidfuzz.
Provee funciones de similitud de texto optimizadas para conciliacion bancaria.

API principal:
    calcular_similitud(a, b) -> float  (0.0 a 1.0)

Uso desde matcher.py:
    from src.fuzzy_matcher import calcular_similitud
    score = calcular_similitud(nombre_banco, alias_contagram)
"""
import re
import unicodedata

from rapidfuzz import fuzz


# ─── PESOS CONFIGURABLES ──────────────────────────────────────────
# Cada algoritmo aporta un % al score final de texto.
# Ajustar segun resultados con datos reales.
PESOS_SIMILITUD = {
    "token_set_ratio": 0.45,   # Ignora orden y palabras extra
    "token_sort_ratio": 0.30,  # Compara tokens ordenados alfabeticamente
    "partial_ratio": 0.25,     # Mejor substring match
}


def _normalizar_texto(texto: str) -> str:
    """
    Normaliza texto para comparacion:
    - Lowercase
    - Quita acentos (á→a, ñ→n)
    - Quita simbolos y puntuacion
    - Colapsa espacios multiples
    - Quita palabras comunes sin valor (SA, SRL, SAS, etc.)
    """
    if not texto:
        return ""

    # Lowercase
    t = texto.lower().strip()

    # Quitar acentos (NFD decompose + strip combining marks)
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")

    # Quitar simbolos y puntuacion (dejar solo letras, numeros, espacios)
    t = re.sub(r"[^a-z0-9\s]", " ", t)

    # Quitar palabras sin valor para matching bancario
    stopwords = {
        "sa", "srl", "sas", "saic", "sacif", "sacifi",
        "de", "del", "la", "el", "los", "las", "y",
        "cia", "hnos", "hermanos", "e hijos",
        "distribuidora", "distribucion",
    }
    words = t.split()
    words = [w for w in words if w not in stopwords and len(w) > 0]

    return " ".join(words)


def calcular_similitud(a: str, b: str) -> float:
    """
    Calcula similitud entre dos strings usando rapidfuzz (0.0 a 1.0).

    Combina 3 algoritmos con pesos configurables:
    - token_set_ratio: "PRITTY SA" vs "SA PRITTY" → 100
    - token_sort_ratio: "DISTRIBUIDORA PRITTY" vs "PRITTY DISTRIBUIDORA" → 100
    - partial_ratio: "MERPAG*PRITTY-RET" vs "PRITTY" → alto

    Args:
        a: Primer string (tipicamente nombre del banco)
        b: Segundo string (tipicamente alias/nombre de Contagram)

    Returns:
        Score de 0.0 a 1.0 (compatible con la interfaz de _similitud original)
    """
    if not a or not b:
        return 0.0

    # Normalizar ambos textos
    na = _normalizar_texto(a)
    nb = _normalizar_texto(b)

    if not na or not nb:
        return 0.0

    # Match exacto post-normalizacion
    if na == nb:
        return 1.0

    # Calcular scores parciales (rapidfuzz devuelve 0-100)
    s_token_set = fuzz.token_set_ratio(na, nb) / 100.0
    s_token_sort = fuzz.token_sort_ratio(na, nb) / 100.0
    s_partial = fuzz.partial_ratio(na, nb) / 100.0

    # Score ponderado
    score = (
        PESOS_SIMILITUD["token_set_ratio"] * s_token_set
        + PESOS_SIMILITUD["token_sort_ratio"] * s_token_sort
        + PESOS_SIMILITUD["partial_ratio"] * s_partial
    )

    return round(min(score, 1.0), 4)


def calcular_similitud_detalle(a: str, b: str) -> dict:
    """
    Version detallada que devuelve scores parciales (util para debugging/UI).

    Returns:
        {
            "input_a": str, "input_b": str,
            "normalizado_a": str, "normalizado_b": str,
            "token_set_ratio": float, "token_sort_ratio": float,
            "partial_ratio": float, "score_total": float,
        }
    """
    na = _normalizar_texto(a)
    nb = _normalizar_texto(b)

    if not na or not nb:
        return {
            "input_a": a, "input_b": b,
            "normalizado_a": na, "normalizado_b": nb,
            "token_set_ratio": 0.0, "token_sort_ratio": 0.0,
            "partial_ratio": 0.0, "score_total": 0.0,
        }

    s_token_set = fuzz.token_set_ratio(na, nb) / 100.0
    s_token_sort = fuzz.token_sort_ratio(na, nb) / 100.0
    s_partial = fuzz.partial_ratio(na, nb) / 100.0

    score = (
        PESOS_SIMILITUD["token_set_ratio"] * s_token_set
        + PESOS_SIMILITUD["token_sort_ratio"] * s_token_sort
        + PESOS_SIMILITUD["partial_ratio"] * s_partial
    )

    return {
        "input_a": a,
        "input_b": b,
        "normalizado_a": na,
        "normalizado_b": nb,
        "token_set_ratio": round(s_token_set, 4),
        "token_sort_ratio": round(s_token_sort, 4),
        "partial_ratio": round(s_partial, 4),
        "score_total": round(min(score, 1.0), 4),
    }
