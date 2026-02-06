"""
Test end-to-end del motor de conciliacion con logica ternaria.
"""
import pandas as pd
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.normalizador import normalizar, detectar_banco
from src.clasificador import clasificar_extracto
from src.motor_conciliacion import MotorConciliacion

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def test_normalizacion():
    print("=" * 60)
    print("TEST 1: Normalizacion de extractos bancarios")
    print("=" * 60)

    bancos = {
        "galicia": "extracto_galicia_dic2025.csv",
        "santander": "extracto_santander_dic2025.csv",
        "mercadopago": "extracto_mercadopago_dic2025.csv",
    }

    for banco_esperado, fname in bancos.items():
        path = os.path.join(DATA_DIR, "test", fname)
        df = pd.read_csv(path)
        banco_detectado = detectar_banco(df)
        assert banco_detectado == banco_esperado, f"FAIL: esperado {banco_esperado}, detectado {banco_detectado}"
        normalizado = normalizar(df, banco_detectado)
        assert len(normalizado) > 0
        assert "fecha" in normalizado.columns
        assert "monto" in normalizado.columns
        assert normalizado["monto"].notna().all(), f"FAIL: montos NaN en {banco_esperado}"
        assert (normalizado["monto"] > 0).all(), f"FAIL: montos <= 0 en {banco_esperado}"
        print(f"  OK {banco_esperado}: {len(normalizado)} movimientos")
    print("  PASSED\n")


def test_clasificacion():
    print("=" * 60)
    print("TEST 2: Clasificacion de movimientos")
    print("=" * 60)

    df = pd.read_csv(os.path.join(DATA_DIR, "test", "extracto_galicia_dic2025.csv"))
    normalizado = normalizar(df, "galicia")
    clasificado = clasificar_extracto(normalizado)
    assert "clasificacion" in clasificado.columns
    categorias = clasificado["clasificacion"].unique()
    assert "cobranza" in categorias
    for cat in categorias:
        print(f"  - {cat}: {len(clasificado[clasificado['clasificacion'] == cat])}")
    print("  PASSED\n")


def test_motor_ternario():
    print("=" * 60)
    print("TEST 3: Motor de conciliacion ternario")
    print("=" * 60)

    extractos = []
    for fname in ["extracto_galicia_dic2025.csv", "extracto_santander_dic2025.csv", "extracto_mercadopago_dic2025.csv"]:
        extractos.append(pd.read_csv(os.path.join(DATA_DIR, "test", fname)))

    ventas = pd.read_csv(os.path.join(DATA_DIR, "contagram", "ventas_pendientes_dic2025.csv"))
    compras = pd.read_csv(os.path.join(DATA_DIR, "contagram", "compras_pendientes_dic2025.csv"))
    tabla_param = pd.read_csv(os.path.join(DATA_DIR, "config", "tabla_parametrica.csv"))

    motor = MotorConciliacion(tabla_param)
    resultado = motor.procesar(extractos, ventas, compras)

    assert resultado is not None
    assert all(k in resultado for k in ["resultados", "stats", "cobranzas_csv", "pagos_csv", "excepciones"])

    stats = resultado["stats"]

    assert "match_exacto" in stats
    assert "probable_duda_id" in stats
    assert "probable_dif_cambio" in stats
    assert "no_match" in stats

    print(f"\n  RESULTADOS TERNARIOS:")
    print(f"  Total movimientos: {stats['total_movimientos']}")
    print(f"  Match Exacto:       {stats['match_exacto']} ({stats['tasa_match_exacto']}%)")
    print(f"  Probable Duda ID:   {stats['probable_duda_id']}")
    print(f"  Probable Dif Cambio:{stats['probable_dif_cambio']}")
    print(f"  No Match:           {stats['no_match']} ({stats['tasa_no_match']}%)")
    print(f"  Gastos bancarios:   {stats['gastos_bancarios']}")
    print(f"  Conciliacion total: {stats['tasa_conciliacion_total']}%")

    print(f"\n  KPIs FINANCIEROS:")
    print(f"  Cobrado (banco):     ${stats['monto_cobranzas']:,.2f}")
    print(f"  Facturado (contagram): ${stats['monto_ventas_contagram']:,.2f}")
    print(f"  Revenue Gap:         ${stats['revenue_gap']:,.2f}")
    print(f"  Dif cambio neto:     ${stats['monto_dif_cambio_neto']:,.2f}")
    print(f"  A favor:             ${stats['monto_a_favor']:,.2f}")
    print(f"  En contra:           ${stats['monto_en_contra']:,.2f}")
    print(f"  No conciliado:       ${stats['monto_no_conciliado']:,.2f}")

    print(f"\n  Por banco:")
    for banco, data in stats["por_banco"].items():
        print(f"    {banco}: {data['movimientos']} mov, {data['match_exacto']} exacto, "
              f"{data['probable_duda_id']} duda_id, {data['probable_dif_cambio']} dif_cambio, "
              f"{data['no_match']} no_match")

    df_cob = resultado["cobranzas_csv"]
    df_pag = resultado["pagos_csv"]
    df_exc = resultado["excepciones"]
    print(f"\n  OUTPUTS:")
    print(f"  subir_cobranzas_contagram.csv: {len(df_cob)} registros")
    print(f"  subir_pagos_contagram.csv: {len(df_pag)} registros")
    print(f"  excepciones.xlsx: {len(df_exc)} registros")

    assert len(df_cob) > 0, "FAIL: no se generaron cobranzas"
    assert stats['tasa_conciliacion_total'] > 80, f"FAIL: tasa total baja ({stats['tasa_conciliacion_total']}%)"
    assert stats['match_exacto'] > 0, "FAIL: no hay matches exactos"

    output_dir = os.path.join(BASE_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)
    df_cob.to_csv(os.path.join(output_dir, "subir_cobranzas_contagram.csv"), index=False, encoding="utf-8-sig")
    df_pag.to_csv(os.path.join(output_dir, "subir_pagos_contagram.csv"), index=False, encoding="utf-8-sig")
    if not df_exc.empty:
        df_exc.to_excel(os.path.join(output_dir, "excepciones.xlsx"), index=False)

    print(f"\n  Archivos guardados en /output/")
    print("  PASSED\n")


if __name__ == "__main__":
    test_normalizacion()
    test_clasificacion()
    test_motor_ternario()
    print("=" * 60)
    print("TODOS LOS TESTS PASARON EXITOSAMENTE")
    print("=" * 60)
