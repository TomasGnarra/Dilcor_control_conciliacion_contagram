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
from src.normalizador_contagram import normalizar_ventas_contagram
from src.conciliador_real import conciliar_real


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

    def procesar_real(
        self,
        extractos_bancarios: list[pd.DataFrame],
        ventas_contagram: pd.DataFrame,
        match_config: dict = None,
    ) -> dict:
        """Procesa datos reales: usa CUIT + flags de medio de cobro."""
        # 1. Normalizar extracto bancario
        extractos_normalizados = []
        for df in extractos_bancarios:
            banco = detectar_banco(df)
            normalizado = normalizar(df, banco)
            extractos_normalizados.append(normalizado)

        extracto_unificado = pd.concat(extractos_normalizados, ignore_index=True)
        extracto_unificado = extracto_unificado.sort_values("fecha").reset_index(drop=True)

        # 2. Normalizar ventas Contagram (agrega flags de medio de cobro)
        ventas_norm = normalizar_ventas_contagram(ventas_contagram)

        # 3. Conciliar con motor real (CUIT-based, 3 niveles)
        self.resultados = conciliar_real(extracto_unificado, ventas_norm, match_config)

        # 4. Stats
        self._calcular_stats_real(ventas_norm)

        return {
            "resultados": self.resultados,
            "stats": self.stats,
            "cobranzas_csv": self._generar_cobranzas_csv_real(),
            "pagos_csv": pd.DataFrame(),
            "excepciones": self._generar_excepciones_real(),
        }

    def _calcular_stats_real(self, ventas: pd.DataFrame):
        """Calcula stats para conciliacion real con tags de 3 niveles."""
        df = self.resultados
        total = len(df)

        matched = df[df.get("conciliation_status", pd.Series(dtype=str)) == "MATCHED"]
        suggested = df[df.get("conciliation_status", pd.Series(dtype=str)) == "SUGGESTED"]
        excluded = df[df.get("conciliation_status", pd.Series(dtype=str)) == "EXCLUDED"]

        cobranzas = df[df.get("clasificacion", pd.Series(dtype=str)) == "cobranza"]
        gastos = df[df.get("clasificacion", pd.Series(dtype=str)) == "gasto_bancario"]
        pagos_prov = df[df.get("clasificacion", pd.Series(dtype=str)) == "pago_proveedor"]

        # Desglose por nivel
        match_exacto = len(matched)
        probable = len(suggested)
        no_match = len(excluded[excluded.get("clasificacion", pd.Series(dtype=str)) != "gasto_bancario"])
        gastos_count = len(gastos)
        conciliables = max(total - gastos_count, 1)

        # Desglose cobranzas
        cob_matched = cobranzas[cobranzas.get("conciliation_status", pd.Series(dtype=str)) == "MATCHED"]
        cob_suggested = cobranzas[cobranzas.get("conciliation_status", pd.Series(dtype=str)) == "SUGGESTED"]
        cob_excluded = cobranzas[cobranzas.get("conciliation_status", pd.Series(dtype=str)) == "EXCLUDED"]

        # Stats cobros
        cobros_stats = {
            "total": len(cobranzas),
            "match_exacto": len(cob_matched),
            "match_exacto_monto": round(cob_matched["monto"].sum(), 2) if not cob_matched.empty else 0,
            "match_directo": len(cob_matched[cob_matched.get("tipo_match_monto", pd.Series(dtype=str)) == "directo"]) if not cob_matched.empty else 0,
            "match_directo_monto": round(cob_matched[cob_matched.get("tipo_match_monto", pd.Series(dtype=str)) == "directo"]["monto"].sum(), 2) if not cob_matched.empty else 0,
            "match_suma": len(cob_matched[cob_matched.get("tipo_match_monto", pd.Series(dtype=str)).isin(["suma_total", "suma_parcial"])]) if not cob_matched.empty else 0,
            "match_suma_monto": round(cob_matched[cob_matched.get("tipo_match_monto", pd.Series(dtype=str)).isin(["suma_total", "suma_parcial"])]["monto"].sum(), 2) if not cob_matched.empty else 0,
            "probable_duda_id": len(cob_suggested),
            "probable_duda_id_monto": round(cob_suggested["monto"].sum(), 2) if not cob_suggested.empty else 0,
            "probable_dif_cambio": 0,
            "probable_dif_cambio_monto": 0,
            "no_match": len(cob_excluded),
            "no_match_monto": round(cob_excluded["monto"].sum(), 2) if not cob_excluded.empty else 0,
            "conciliados": len(cob_matched) + len(cob_suggested),
            "tasa_conciliacion": round((len(cob_matched) + len(cob_suggested)) / max(len(cobranzas), 1) * 100, 1),
            "monto_total": round(cobranzas["monto"].sum(), 2),
            "monto_conciliado": round(cob_matched["monto"].sum() + cob_suggested["monto"].sum(), 2),
            "de_mas": 0, "de_menos": 0, "diferencia_neta": 0,
        }

        # Pagos (solo informativos para real data)
        pagos_stats = {
            "total": len(pagos_prov), "match_exacto": 0, "match_exacto_monto": 0,
            "match_directo": 0, "match_directo_monto": 0,
            "match_suma": 0, "match_suma_monto": 0,
            "probable_duda_id": 0, "probable_duda_id_monto": 0,
            "probable_dif_cambio": 0, "probable_dif_cambio_monto": 0,
            "no_match": len(pagos_prov),
            "no_match_monto": round(pagos_prov["monto"].sum(), 2) if not pagos_prov.empty else 0,
            "conciliados": 0, "tasa_conciliacion": 0,
            "monto_total": round(pagos_prov["monto"].sum(), 2) if not pagos_prov.empty else 0,
            "monto_conciliado": 0,
            "de_mas": 0, "de_menos": 0, "diferencia_neta": 0,
        }

        # Monto ventas contagram (solo Santander cobrado)
        ventas_santander = ventas[ventas.get("contiene_santander", pd.Series(dtype=bool)) == True]
        monto_ventas = round(ventas_santander["Monto Total"].sum(), 2) if not ventas_santander.empty else 0

        self.stats = {
            "total_movimientos": total,
            "match_exacto": match_exacto,
            "probable_duda_id": probable,
            "probable_dif_cambio": 0,
            "no_match": no_match,
            "gastos_bancarios": gastos_count,
            "tasa_match_exacto": round(match_exacto / conciliables * 100, 1),
            "tasa_probable": round(probable / conciliables * 100, 1),
            "tasa_no_match": round(no_match / conciliables * 100, 1),
            "tasa_conciliacion_total": round((match_exacto + probable) / conciliables * 100, 1),
            "total_cobranzas": len(cobranzas),
            "monto_cobranzas": round(cobranzas["monto"].sum(), 2),
            "total_pagos": len(pagos_prov),
            "monto_pagos": round(pagos_prov["monto"].sum(), 2) if not pagos_prov.empty else 0,
            "monto_gastos_bancarios": round(gastos["monto"].sum(), 2) if not gastos.empty else 0,
            "monto_ventas_contagram": monto_ventas,
            "monto_compras_contagram": 0,
            "revenue_gap": round(cobranzas["monto"].sum() - monto_ventas, 2),
            "payment_gap": 0,
            "monto_dif_cambio_neto": 0, "monto_a_favor": 0, "monto_en_contra": 0,
            "monto_no_conciliado": round(cob_excluded["monto"].sum(), 2) if not cob_excluded.empty else 0,
            "cobros": cobros_stats,
            "pagos_prov": pagos_stats,
            "por_banco": {},
            # Stats especificos real
            "matched_count": len(matched),
            "matched_monto": round(matched["monto"].sum(), 2) if not matched.empty else 0,
            "suggested_count": len(suggested),
            "suggested_monto": round(suggested["monto"].sum(), 2) if not suggested.empty else 0,
            "excluded_count": len(excluded),
        }

        for banco in df["banco"].unique():
            db = df[df["banco"] == banco]
            self.stats["por_banco"][banco] = {
                "movimientos": len(db),
                "match_exacto": len(db[db.get("conciliation_status", pd.Series(dtype=str)) == "MATCHED"]),
                "probable_duda_id": len(db[db.get("conciliation_status", pd.Series(dtype=str)) == "SUGGESTED"]),
                "probable_dif_cambio": 0,
                "no_match": len(db[db.get("conciliation_status", pd.Series(dtype=str)) == "EXCLUDED"]),
                "monto_creditos": round(db[db["tipo"] == "CREDITO"]["monto"].sum(), 2),
                "monto_debitos": round(db[db["tipo"] == "DEBITO"]["monto"].sum(), 2),
            }

    def _generar_cobranzas_csv_real(self) -> pd.DataFrame:
        """Genera CSV de cobranzas para datos reales."""
        df = self.resultados
        cobranzas = df[
            (df.get("clasificacion", pd.Series(dtype=str)) == "cobranza") &
            (df.get("conciliation_status", pd.Series(dtype=str)).isin(["MATCHED", "SUGGESTED"]))
        ].copy()

        if cobranzas.empty:
            return pd.DataFrame()

        return pd.DataFrame({
            "Fecha": cobranzas["fecha"].dt.strftime("%d/%m/%Y") if hasattr(cobranzas["fecha"], "dt") else cobranzas["fecha"],
            "Cliente": cobranzas.get("nombre_contagram", ""),
            "CUIT Banco": cobranzas.get("cuit_banco", ""),
            "Monto Cobrado": cobranzas["monto"],
            "Factura": cobranzas.get("factura_match", ""),
            "Status": cobranzas.get("conciliation_status", ""),
            "Tag": cobranzas.get("conciliation_tag", ""),
            "Confianza": cobranzas.get("conciliation_confidence", ""),
            "Razon": cobranzas.get("conciliation_reason", ""),
            "Tipo Match": cobranzas.get("tipo_match_monto", "").fillna("—") if "tipo_match_monto" in cobranzas.columns else "—",
            "Cant Facturas": cobranzas.get("facturas_count", 0),
            "Diferencia $": cobranzas.get("diferencia_monto", 0),
            "Banco": cobranzas["banco"],
            "Referencia": cobranzas["referencia"],
        })

    def _generar_excepciones_real(self) -> pd.DataFrame:
        """Genera excepciones para datos reales."""
        df = self.resultados
        exc = df[
            (df.get("conciliation_status", pd.Series(dtype=str)) == "EXCLUDED") &
            (df.get("clasificacion", pd.Series(dtype=str)) != "gasto_bancario")
        ].copy()

        if exc.empty:
            return pd.DataFrame()

        return pd.DataFrame({
            "Fecha": exc["fecha"].dt.strftime("%d/%m/%Y") if hasattr(exc["fecha"], "dt") else exc["fecha"],
            "Tipo": exc["tipo"],
            "Descripcion": exc["descripcion"],
            "Monto": exc["monto"],
            "CUIT Banco": exc.get("cuit_banco", ""),
            "Tag": exc.get("conciliation_tag", ""),
            "Razon": exc.get("conciliation_reason", ""),
            "Referencia": exc["referencia"],
        })

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

        # --- Helper para desglose por clasificacion ---
        def _desglose(subset):
            """Calcula stats de match + diferencias para un subset (cobranzas o pagos)."""
            n = len(subset)
            me = subset[subset["match_nivel"] == "match_exacto"]
            di = subset[subset["match_nivel"] == "probable_duda_id"]
            dc = subset[subset["match_nivel"] == "probable_dif_cambio"]
            nm = subset[subset["match_nivel"] == "no_match"]

            conciliados = len(me) + len(di) + len(dc)

            # Desglose match exacto: directo (1:1) vs suma
            has_tipo = "tipo_match_monto" in subset.columns
            if has_tipo and not me.empty:
                me_directo = me[me["tipo_match_monto"] == "directo"]
                me_suma = me[me["tipo_match_monto"].isin(["suma_total", "suma_parcial"])]
            else:
                me_directo = me
                me_suma = me.iloc[0:0]  # empty

            # Cobrado/pagado de mas y de menos (solo match_exacto con diferencia)
            de_mas = 0.0
            de_menos = 0.0
            if not me.empty and "diferencia_monto" in me.columns:
                for _, r in me.iterrows():
                    dif = r.get("diferencia_monto", 0) or 0
                    if dif > 0:
                        de_mas += dif
                    elif dif < 0:
                        de_menos += abs(dif)

            return {
                "total": n,
                "match_exacto": len(me),
                "match_exacto_monto": round(me["monto"].sum(), 2) if not me.empty else 0,
                "match_directo": len(me_directo),
                "match_directo_monto": round(me_directo["monto"].sum(), 2) if not me_directo.empty else 0,
                "match_suma": len(me_suma),
                "match_suma_monto": round(me_suma["monto"].sum(), 2) if not me_suma.empty else 0,
                "probable_duda_id": len(di),
                "probable_duda_id_monto": round(di["monto"].sum(), 2) if not di.empty else 0,
                "probable_dif_cambio": len(dc),
                "probable_dif_cambio_monto": round(dc["monto"].sum(), 2) if not dc.empty else 0,
                "no_match": len(nm),
                "no_match_monto": round(nm["monto"].sum(), 2) if not nm.empty else 0,
                "conciliados": conciliados,
                "tasa_conciliacion": round(conciliados / max(n, 1) * 100, 1),
                "monto_total": round(subset["monto"].sum(), 2),
                "monto_conciliado": round((me["monto"].sum() + di["monto"].sum() + dc["monto"].sum()), 2) if conciliados > 0 else 0,
                "de_mas": round(de_mas, 2),
                "de_menos": round(de_menos, 2),
                "diferencia_neta": round(de_mas - de_menos, 2),
            }

        cobros_stats = _desglose(cobranzas)
        pagos_stats = _desglose(pagos)

        # Diferencias globales
        dif_cambio_rows = df[df["match_nivel"] == "probable_dif_cambio"]
        monto_dif_cambio_total = 0
        monto_a_favor = 0
        monto_en_contra = 0
        if "diferencia_monto" in dif_cambio_rows.columns:
            for _, r in dif_cambio_rows.iterrows():
                dif = r.get("diferencia_monto", 0) or 0
                monto_dif_cambio_total += dif
                if dif > 0:
                    monto_a_favor += dif
                else:
                    monto_en_contra += abs(dif)

        monto_no_match = round(df[df["match_nivel"] == "no_match"]["monto"].sum(), 2)
        revenue_gap = round(monto_cobranzas_banco - monto_ventas_contagram, 2)
        payment_gap = round(monto_pagos_banco - monto_compras_contagram, 2)

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
            # KPIs financieros globales
            "monto_ventas_contagram": monto_ventas_contagram,
            "monto_compras_contagram": monto_compras_contagram,
            "revenue_gap": revenue_gap,
            "payment_gap": payment_gap,
            "monto_dif_cambio_neto": round(monto_dif_cambio_total, 2),
            "monto_a_favor": round(monto_a_favor, 2),
            "monto_en_contra": round(monto_en_contra, 2),
            "monto_no_conciliado": monto_no_match,
            # Desglose por bloque
            "cobros": cobros_stats,
            "pagos_prov": pagos_stats,
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
            "Tipo Match": cobranzas.get("tipo_match_monto", "").fillna("—"),
            "Cant Facturas": cobranzas.get("facturas_count", 0).fillna(0).astype(int),
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
            "Tipo Match": pagos.get("tipo_match_monto", "").fillna("—"),
            "Cant Facturas": pagos.get("facturas_count", 0).fillna(0).astype(int),
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
