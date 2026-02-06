"""
Motor de Conciliación - Orquesta el proceso completo:
1. Normalización de extractos bancarios
2. Clasificación de movimientos
3. Matching contra datos de Contagram
4. Generación de outputs (CSVs para importar + excepciones)
"""
import pandas as pd
import os
from datetime import datetime

from src.normalizador import normalizar, detectar_banco
from src.clasificador import clasificar_extracto
from src.matcher import ejecutar_matching


class MotorConciliacion:
    def __init__(self, tabla_parametrica: pd.DataFrame):
        self.tabla_param = tabla_parametrica
        self.resultados = None
        self.stats = {}

    def procesar(
        self,
        extractos_bancarios: list[pd.DataFrame],
        ventas_contagram: pd.DataFrame,
        compras_contagram: pd.DataFrame,
    ) -> dict:
        """
        Ejecuta el proceso completo de conciliación.

        Args:
            extractos_bancarios: Lista de DataFrames con extractos de cada banco
            ventas_contagram: DataFrame con facturas de venta pendientes
            compras_contagram: DataFrame con OC pendientes

        Returns:
            dict con resultados y estadísticas
        """
        # 1. Normalizar todos los extractos
        extractos_normalizados = []
        for df in extractos_bancarios:
            banco = detectar_banco(df)
            normalizado = normalizar(df, banco)
            extractos_normalizados.append(normalizado)

        # Unificar
        extracto_unificado = pd.concat(extractos_normalizados, ignore_index=True)
        extracto_unificado = extracto_unificado.sort_values("fecha").reset_index(drop=True)

        # 2. Clasificar
        extracto_clasificado = clasificar_extracto(extracto_unificado)

        # 3. Matching
        self.resultados = ejecutar_matching(
            extracto_clasificado,
            self.tabla_param,
            ventas_contagram,
            compras_contagram,
        )

        # 4. Calcular estadísticas
        self._calcular_stats()

        return {
            "resultados": self.resultados,
            "stats": self.stats,
            "cobranzas_csv": self._generar_cobranzas_csv(),
            "pagos_csv": self._generar_pagos_csv(),
            "excepciones": self._generar_excepciones(),
        }

    def _calcular_stats(self):
        """Calcula estadísticas del proceso de conciliación."""
        df = self.resultados
        total = len(df)
        automaticos = len(df[df["match_nivel"] == "automatico"])
        probables = len(df[df["match_nivel"] == "probable"])
        excepciones = len(df[df["match_nivel"] == "excepcion"])
        gastos = len(df[df["match_nivel"] == "gasto_bancario"])

        cobranzas = df[df["clasificacion"] == "cobranza"]
        pagos = df[df["clasificacion"] == "pago_proveedor"]

        self.stats = {
            "total_movimientos": total,
            "automaticos": automaticos,
            "probables": probables,
            "excepciones": excepciones,
            "gastos_bancarios": gastos,
            "tasa_conciliacion_auto": round(automaticos / max(total - gastos, 1) * 100, 1),
            "tasa_conciliacion_total": round((automaticos + probables) / max(total - gastos, 1) * 100, 1),
            "total_cobranzas": len(cobranzas),
            "monto_cobranzas": round(cobranzas["monto"].sum(), 2),
            "total_pagos": len(pagos),
            "monto_pagos": round(pagos["monto"].sum(), 2),
            "monto_gastos_bancarios": round(df[df["clasificacion"] == "gasto_bancario"]["monto"].sum(), 2),
            "por_banco": {},
        }

        for banco in df["banco"].unique():
            df_banco = df[df["banco"] == banco]
            self.stats["por_banco"][banco] = {
                "movimientos": len(df_banco),
                "automaticos": len(df_banco[df_banco["match_nivel"] == "automatico"]),
                "probables": len(df_banco[df_banco["match_nivel"] == "probable"]),
                "excepciones": len(df_banco[df_banco["match_nivel"] == "excepcion"]),
                "monto_creditos": round(df_banco[df_banco["tipo"] == "CREDITO"]["monto"].sum(), 2),
                "monto_debitos": round(df_banco[df_banco["tipo"] == "DEBITO"]["monto"].sum(), 2),
            }

    def _generar_cobranzas_csv(self) -> pd.DataFrame:
        """
        Genera CSV de cobranzas para importar en Contagram.
        Solo incluye matches automáticos de tipo cobranza.
        """
        df = self.resultados
        cobranzas = df[
            (df["clasificacion"] == "cobranza") &
            (df["match_nivel"].isin(["automatico", "probable"]))
        ].copy()

        if cobranzas.empty:
            return pd.DataFrame()

        return pd.DataFrame({
            "Fecha": cobranzas["fecha"].dt.strftime("%d/%m/%Y"),
            "ID Cliente": cobranzas["id_contagram"],
            "Cliente": cobranzas["nombre_contagram"],
            "CUIT": cobranzas.get("cuit", ""),
            "Monto Cobrado": cobranzas["monto"],
            "Factura Asociada": cobranzas.get("factura_match", ""),
            "Banco Origen": cobranzas["banco"],
            "Referencia Banco": cobranzas["referencia"],
            "Nivel Match": cobranzas["match_nivel"],
            "Confianza %": cobranzas["confianza"],
            "Observaciones": cobranzas.apply(
                lambda r: f"Diferencia ${r.get('diferencia_monto', 0) or 0:.2f}" if r.get("diferencia_monto") else "",
                axis=1
            ),
        })

    def _generar_pagos_csv(self) -> pd.DataFrame:
        """
        Genera CSV de pagos a proveedores para importar en Contagram.
        """
        df = self.resultados
        pagos = df[
            (df["clasificacion"] == "pago_proveedor") &
            (df["match_nivel"].isin(["automatico", "probable"]))
        ].copy()

        if pagos.empty:
            return pd.DataFrame()

        return pd.DataFrame({
            "Fecha": pagos["fecha"].dt.strftime("%d/%m/%Y"),
            "ID Proveedor": pagos["id_contagram"],
            "Proveedor": pagos["nombre_contagram"],
            "CUIT": pagos.get("cuit", ""),
            "Monto Pagado": pagos["monto"],
            "OC Asociada": pagos.get("factura_match", ""),
            "Banco": pagos["banco"],
            "Referencia Banco": pagos["referencia"],
            "Nivel Match": pagos["match_nivel"],
            "Confianza %": pagos["confianza"],
        })

    def _generar_excepciones(self) -> pd.DataFrame:
        """
        Genera reporte de excepciones (movimientos no conciliados).
        """
        df = self.resultados
        exc = df[df["match_nivel"] == "excepcion"].copy()

        if exc.empty:
            return pd.DataFrame()

        return pd.DataFrame({
            "Fecha": exc["fecha"].dt.strftime("%d/%m/%Y"),
            "Banco": exc["banco"],
            "Tipo": exc["tipo"],
            "Clasificacion": exc["clasificacion"],
            "Descripcion Original": exc["descripcion"],
            "Monto": exc["monto"],
            "Referencia": exc["referencia"],
            "Motivo": "Sin match en tabla paramétrica",
            "Accion Sugerida": exc.apply(
                lambda r: "Agregar alias a tabla paramétrica" if r["clasificacion"] in ["cobranza", "pago_proveedor"]
                else "Revisar manualmente",
                axis=1
            ),
        })
