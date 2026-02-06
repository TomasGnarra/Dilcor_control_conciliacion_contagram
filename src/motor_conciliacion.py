"""
Motor de Conciliacion - Orquesta el proceso completo:
1. Normalizacion de extractos bancarios
2. Clasificacion de movimientos
3. Matching ternario contra datos de Contagram
4. Generacion de outputs (CSVs para importar + excepciones)
5. KPIs de impacto financiero (Money Gap)
"""
import pandas as pd
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
        match_config: dict = None,
    ) -> dict:
        # 1. Normalizar
        extractos_normalizados = []
        for df in extractos_bancarios:
            banco = detectar_banco(df)
            normalizado = normalizar(df, banco)
            extractos_normalizados.append(normalizado)

        extracto_unificado = pd.concat(extractos_normalizados, ignore_index=True)
        extracto_unificado = extracto_unificado.sort_values("fecha").reset_index(drop=True)

        # 2. Clasificar
        extracto_clasificado = clasificar_extracto(extracto_unificado)

        # 3. Matching ternario
        self.resultados = ejecutar_matching(
            extracto_clasificado,
            self.tabla_param,
            ventas_contagram,
            compras_contagram,
            config=match_config,
        )

        # 4. Stats y KPIs
        self._calcular_stats(ventas_contagram, compras_contagram)

        return {
            "resultados": self.resultados,
            "stats": self.stats,
            "cobranzas_csv": self._generar_cobranzas_csv(),
            "pagos_csv": self._generar_pagos_csv(),
            "excepciones": self._generar_excepciones(),
        }

    def _calcular_stats(self, ventas: pd.DataFrame, compras: pd.DataFrame):
        df = self.resultados
        total = len(df)

        # Conteos por nivel ternario
        match_exacto = len(df[df["match_nivel"] == "match_exacto"])
        probable_duda_id = len(df[df["match_nivel"] == "probable_duda_id"])
        probable_dif_cambio = len(df[df["match_nivel"] == "probable_dif_cambio"])
        no_match = len(df[df["match_nivel"] == "no_match"])
        gastos = len(df[df["match_nivel"] == "gasto_bancario"])

        conciliables = max(total - gastos, 1)

        cobranzas = df[df["clasificacion"] == "cobranza"]
        pagos = df[df["clasificacion"] == "pago_proveedor"]

        # --- KPIs de impacto financiero ---
        monto_cobranzas_banco = round(cobranzas["monto"].sum(), 2)
        monto_pagos_banco = round(pagos["monto"].sum(), 2)
        monto_ventas_contagram = round(ventas["Monto Total"].sum(), 2) if "Monto Total" in ventas.columns else 0
        monto_compras_contagram = round(compras["Monto Total"].sum(), 2) if "Monto Total" in compras.columns else 0

        # Diferencias de monto en matches
        dif_cambio_rows = df[df["match_nivel"] == "probable_dif_cambio"]
        monto_dif_cambio_total = 0
        monto_a_favor = 0    # Banco cobro mas de lo facturado
        monto_en_contra = 0  # Banco cobro menos de lo facturado
        if "diferencia_monto" in dif_cambio_rows.columns:
            for _, r in dif_cambio_rows.iterrows():
                dif = r.get("diferencia_monto", 0) or 0
                monto_dif_cambio_total += dif
                if dif > 0:
                    monto_a_favor += dif
                else:
                    monto_en_contra += abs(dif)

        # No match = dinero sin conciliar
        monto_no_match = round(df[df["match_nivel"] == "no_match"]["monto"].sum(), 2)

        # Revenue gap: diferencia entre lo cobrado (banco) y lo facturado (contagram)
        revenue_gap = round(monto_cobranzas_banco - monto_ventas_contagram, 2)

        self.stats = {
            "total_movimientos": total,
            "match_exacto": match_exacto,
            "probable_duda_id": probable_duda_id,
            "probable_dif_cambio": probable_dif_cambio,
            "no_match": no_match,
            "gastos_bancarios": gastos,
            # Tasas
            "tasa_match_exacto": round(match_exacto / conciliables * 100, 1),
            "tasa_probable": round((probable_duda_id + probable_dif_cambio) / conciliables * 100, 1),
            "tasa_no_match": round(no_match / conciliables * 100, 1),
            "tasa_conciliacion_total": round((match_exacto + probable_duda_id + probable_dif_cambio) / conciliables * 100, 1),
            # Montos operativos
            "total_cobranzas": len(cobranzas),
            "monto_cobranzas": monto_cobranzas_banco,
            "total_pagos": len(pagos),
            "monto_pagos": monto_pagos_banco,
            "monto_gastos_bancarios": round(df[df["clasificacion"] == "gasto_bancario"]["monto"].sum(), 2),
            # KPIs financieros (Money Gap)
            "monto_ventas_contagram": monto_ventas_contagram,
            "monto_compras_contagram": monto_compras_contagram,
            "revenue_gap": revenue_gap,
            "monto_dif_cambio_neto": round(monto_dif_cambio_total, 2),
            "monto_a_favor": round(monto_a_favor, 2),
            "monto_en_contra": round(monto_en_contra, 2),
            "monto_no_conciliado": monto_no_match,
            # Por banco
            "por_banco": {},
        }

        for banco in df["banco"].unique():
            db = df[df["banco"] == banco]
            self.stats["por_banco"][banco] = {
                "movimientos": len(db),
                "match_exacto": len(db[db["match_nivel"] == "match_exacto"]),
                "probable_duda_id": len(db[db["match_nivel"] == "probable_duda_id"]),
                "probable_dif_cambio": len(db[db["match_nivel"] == "probable_dif_cambio"]),
                "no_match": len(db[db["match_nivel"] == "no_match"]),
                "monto_creditos": round(db[db["tipo"] == "CREDITO"]["monto"].sum(), 2),
                "monto_debitos": round(db[db["tipo"] == "DEBITO"]["monto"].sum(), 2),
            }

    def _generar_cobranzas_csv(self) -> pd.DataFrame:
        df = self.resultados
        cobranzas = df[
            (df["clasificacion"] == "cobranza") &
            (df["match_nivel"].isin(["match_exacto", "probable_duda_id", "probable_dif_cambio"]))
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
            "Detalle Match": cobranzas.get("match_detalle", ""),
            "Confianza %": cobranzas["confianza"],
            "Diferencia $": cobranzas.get("diferencia_monto", 0),
        })

    def _generar_pagos_csv(self) -> pd.DataFrame:
        df = self.resultados
        pagos = df[
            (df["clasificacion"] == "pago_proveedor") &
            (df["match_nivel"].isin(["match_exacto", "probable_duda_id", "probable_dif_cambio"]))
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
            "Detalle Match": pagos.get("match_detalle", ""),
            "Confianza %": pagos["confianza"],
        })

    def _generar_excepciones(self) -> pd.DataFrame:
        df = self.resultados
        exc = df[df["match_nivel"] == "no_match"].copy()

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
            "Detalle": exc.get("match_detalle", "Sin match"),
            "Accion Sugerida": exc.apply(
                lambda r: "Agregar alias a tabla parametrica" if r["clasificacion"] in ["cobranza", "pago_proveedor"]
                else "Revisar manualmente",
                axis=1
            ),
        })
