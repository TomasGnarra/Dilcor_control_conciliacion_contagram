"""
Test end-to-end del motor de conciliación.
Simula el flujo completo: carga de datos -> conciliación -> generación de outputs.
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
    """Test: normalización de cada banco."""
    print("=" * 60)
    print("TEST 1: Normalización de extractos bancarios")
    print("=" * 60)

    bancos = {
        "galicia": "extracto_galicia_dic2025.csv",
        "santander": "extracto_santander_dic2025.csv",
        "mercadopago": "extracto_mercadopago_dic2025.csv",
    }

    for banco_esperado, fname in bancos.items():
        path = os.path.join(DATA_DIR, "test", fname)
        df = pd.read_csv(path)

        # Detección automática
        banco_detectado = detectar_banco(df)
        assert banco_detectado == banco_esperado, f"FAIL: esperado {banco_esperado}, detectado {banco_detectado}"

        # Normalización
        normalizado = normalizar(df, banco_detectado)
        assert len(normalizado) > 0, f"FAIL: {banco_esperado} sin datos"
        assert "fecha" in normalizado.columns
        assert "monto" in normalizado.columns
        assert "tipo" in normalizado.columns
        assert all(normalizado["monto"] > 0), f"FAIL: montos negativos en {banco_esperado}"

        print(f"  OK {banco_esperado}: {len(normalizado)} movimientos normalizados")

    print("  PASSED\n")


def test_clasificacion():
    """Test: clasificación de movimientos."""
    print("=" * 60)
    print("TEST 2: Clasificación de movimientos")
    print("=" * 60)

    df = pd.read_csv(os.path.join(DATA_DIR, "test", "extracto_galicia_dic2025.csv"))
    normalizado = normalizar(df, "galicia")
    clasificado = clasificar_extracto(normalizado)

    assert "clasificacion" in clasificado.columns
    categorias = clasificado["clasificacion"].unique()
    print(f"  Categorías encontradas: {categorias.tolist()}")
    assert "cobranza" in categorias, "FAIL: no se detectaron cobranzas"

    for cat in categorias:
        count = len(clasificado[clasificado["clasificacion"] == cat])
        print(f"  - {cat}: {count} movimientos")

    print("  PASSED\n")


def test_motor_completo():
    """Test: motor de conciliación end-to-end."""
    print("=" * 60)
    print("TEST 3: Motor de conciliación completo")
    print("=" * 60)

    # Cargar datos
    extractos = []
    for fname in ["extracto_galicia_dic2025.csv", "extracto_santander_dic2025.csv", "extracto_mercadopago_dic2025.csv"]:
        extractos.append(pd.read_csv(os.path.join(DATA_DIR, "test", fname)))

    ventas = pd.read_csv(os.path.join(DATA_DIR, "contagram", "ventas_pendientes_dic2025.csv"))
    compras = pd.read_csv(os.path.join(DATA_DIR, "contagram", "compras_pendientes_dic2025.csv"))
    tabla_param = pd.read_csv(os.path.join(DATA_DIR, "config", "tabla_parametrica.csv"))

    print(f"  Extractos: {sum(len(e) for e in extractos)} movimientos en {len(extractos)} bancos")
    print(f"  Ventas: {len(ventas)} facturas")
    print(f"  Compras: {len(compras)} OC")
    print(f"  Tabla param: {len(tabla_param)} registros")

    # Ejecutar
    motor = MotorConciliacion(tabla_param)
    resultado = motor.procesar(extractos, ventas, compras)

    # Validar resultados
    assert resultado is not None
    assert "resultados" in resultado
    assert "stats" in resultado
    assert "cobranzas_csv" in resultado
    assert "pagos_csv" in resultado
    assert "excepciones" in resultado

    stats = resultado["stats"]
    print(f"\n  RESULTADOS:")
    print(f"  Total movimientos: {stats['total_movimientos']}")
    print(f"  Automáticos: {stats['automaticos']}")
    print(f"  Probables: {stats['probables']}")
    print(f"  Excepciones: {stats['excepciones']}")
    print(f"  Gastos bancarios: {stats['gastos_bancarios']}")
    print(f"  Tasa conciliación automática: {stats['tasa_conciliacion_auto']}%")
    print(f"  Tasa conciliación total: {stats['tasa_conciliacion_total']}%")
    print(f"  Monto cobranzas: ${stats['monto_cobranzas']:,.2f}")
    print(f"  Monto pagos: ${stats['monto_pagos']:,.2f}")

    print(f"\n  Por banco:")
    for banco, data in stats["por_banco"].items():
        print(f"    {banco}: {data['movimientos']} mov, {data['automaticos']} auto, {data['excepciones']} exc")

    # Validar outputs
    df_cob = resultado["cobranzas_csv"]
    df_pag = resultado["pagos_csv"]
    df_exc = resultado["excepciones"]

    print(f"\n  OUTPUTS:")
    print(f"  subir_cobranzas_contagram.csv: {len(df_cob)} registros")
    print(f"  subir_pagos_contagram.csv: {len(df_pag)} registros")
    print(f"  excepciones.xlsx: {len(df_exc)} registros")

    assert len(df_cob) > 0, "FAIL: no se generaron cobranzas"
    assert len(df_pag) > 0, "FAIL: no se generaron pagos"
    assert stats["tasa_conciliacion_auto"] > 50, f"FAIL: tasa muy baja ({stats['tasa_conciliacion_auto']}%)"

    # Guardar outputs de ejemplo
    output_dir = os.path.join(BASE_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)
    df_cob.to_csv(os.path.join(output_dir, "subir_cobranzas_contagram.csv"), index=False, encoding="utf-8-sig")
    df_pag.to_csv(os.path.join(output_dir, "subir_pagos_contagram.csv"), index=False, encoding="utf-8-sig")
    df_exc.to_excel(os.path.join(output_dir, "excepciones.xlsx"), index=False)

    print(f"\n  Archivos de salida guardados en /output/")
    print("  PASSED\n")


if __name__ == "__main__":
    test_normalizacion()
    test_clasificacion()
    test_motor_completo()
    print("=" * 60)
    print("TODOS LOS TESTS PASARON EXITOSAMENTE")
    print("=" * 60)
