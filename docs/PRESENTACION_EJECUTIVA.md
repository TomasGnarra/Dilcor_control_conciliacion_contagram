# DILCOR
## Conciliacion Bancaria Automatica con Contagram
### MVP 2.0 - Diciembre 2025

---

### Slide 1: El Problema

**Hoy, la conciliacion bancaria de Dilcor es 100% manual.**

- Se revisan 3 bancos por separado (Galicia, Santander, Mercado Pago)
- Se cruzan movimientos contra Contagram uno por uno
- Se cargan cobranzas y pagos manualmente
- Se buscan diferencias a mano

**Tiempo estimado: 4 a 8 horas diarias**

---

### Slide 2: La Solucion

**Un sistema que identifica automaticamente cada movimiento bancario.**

```
Extractos Bancarios (CSV)  -->  Sistema  -->  Archivos listos para Contagram
  (Galicia, Santander, MP)                     (Cobranzas, Pagos, Excepciones)
```

El operador solo necesita:
1. Bajar los extractos del home banking (5 min)
2. Subirlos a la app y ejecutar (2 min)
3. Revisar excepciones (15-30 min)
4. Importar los CSV en Contagram (5 min)

**Tiempo estimado: 25 a 40 minutos diarios**

---

### Slide 3: Demo en Vivo - Datos Diciembre 2025

| Metrica | Valor |
|---------|-------|
| Movimientos procesados | 679 |
| Tasa de identificacion | 95.8% |
| Match exacto (ID + monto) | 11.3% |
| Identificados pero revisar monto | 84.5% |
| Excepciones (revision manual) | 4.2% (28 mov.) |
| Facturacion procesada | $576.474.570 |
| Revenue Gap | -$259 (casi perfecto) |

*Se ejecuta la demo en Streamlit*

---

### Slide 4: 4 Niveles de Match

| Nivel | Que significa | Que hace el contador |
|-------|--------------|---------------------|
| **Match Exacto** | Sabemos quien es Y el monto coincide con una factura | Nada. Importar directo |
| **Probable - Duda ID** | Nombre parecido pero no identico | Confirmar si es el mismo cliente |
| **Probable - Dif. Cambio** | Sabemos quien es, pero el monto no coincide con ninguna factura individual | Asignar contra que facturas aplica |
| **No Match** | No se pudo identificar | Revisar manualmente |

**El 95.8% de los movimientos se identifican automaticamente.** Solo el 4.2% requiere revision manual completa.

---

### Slide 5: Ejemplo Practico

**En el banco aparece:**
> TRANSF PRITTY $500.000

**El sistema:**
1. Busca "PRITTY" en la tabla parametrica → Encuentra: PRITTY SA, ID 1042
2. Busca facturas de PRITTY en Contagram → Encuentra 3: $200K, $180K, $120K
3. Ninguna factura individual es $500K → **Probable - Dif. de Cambio**

**Resultado:** El contador sabe que la plata es de PRITTY (no tiene que buscarlo). Solo necesita indicar contra que facturas se aplica.

**Sin el sistema:** El contador tendria que abrir el extracto, buscar "PRITTY", ir a Contagram, buscar las facturas, comparar montos, cargar la cobranza manualmente.

---

### Slide 6: Que Genera el Sistema

| Archivo | Para que sirve | Donde se importa en Contagram |
|---------|---------------|-------------------------------|
| `subir_cobranzas_contagram.csv` | Cobros identificados con cliente, factura y monto | Modulo Cobranzas |
| `subir_pagos_contagram.csv` | Pagos a proveedores con OC asociada | Modulo Pagos a Proveedores |
| `excepciones.xlsx` | Movimientos sin identificar, para revision manual | No se importa, es para el contador |

---

### Slide 7: Dashboard de Impacto Financiero

El dashboard se organiza en **dos bloques**:

**Bloque 1: COBROS (Creditos / Ventas)**
| KPI | Que muestra |
|-----|------------|
| Cobrado en Bancos | Total de plata que entro por los 3 bancos |
| Facturado en Contagram | Total de facturas pendientes en el ERP |
| Revenue Gap | Diferencia entre cobrado y facturado. Ideal = $0 |
| Desglose por nivel | Match Exacto (X directo + Y suma) / Duda ID / Dif. Cambio / Sin Identificar |
| Resumen de flujo | Conciliado 100% / Identificado, asignar facturas / Sin identificar (porcentaje) |
| Tipo match + Diferencias | Match directo / Match por suma / Cobrado de mas / Cobrado de menos |

**Bloque 2: PAGOS A PROVEEDORES (Debitos)**
| KPI | Que muestra |
|-----|------------|
| Pagado en Bancos | Total pagado a proveedores |
| OCs en Contagram | Ordenes de compra registradas |
| Payment Gap | Diferencia entre pagado y OCs |
| Desglose por nivel | Idem cobros, para pagos a proveedores (1:1 vs suma) |
| Tipo match + Diferencias | Match directo / Match por suma / Pagado de mas / Pagado de menos |

**Gastos Bancarios:** Barra informativa con comisiones e impuestos (no va a Contagram)

---

### Slide 8: La Tabla Parametrica (el "cerebro")

Es un archivo simple que el contador mantiene:

| El banco dice... | El sistema entiende... |
|-----------------|----------------------|
| MERPAG*PRITTY | Cobranza de PRITTY SA (ID 1042) |
| TRANSF BONPRIX | Cobranza de BONPRIX (ID 1089) |
| PAG COCA COLA ANDINA | Pago a proveedor Coca Cola (ID 5001) |

**Cuando aparece una excepcion nueva:**
1. El contador identifica de quien es
2. Agrega una linea a la tabla
3. La proxima vez, el sistema lo reconoce solo

Con el tiempo, cada vez menos excepciones. El sistema "aprende" por agregado de alias.

---

### Slide 9: No se Toca Contagram

- No se instala nada en Contagram
- No se necesitan APIs ni accesos especiales
- Se usa la importacion CSV que Contagram ya tiene
- Para Contagram, es como si el operador cargara datos a mano

**Riesgo: CERO**

---

### Slide 10: Ahorro Concreto

| Concepto | Sin sistema | Con sistema |
|----------|------------|-------------|
| Tiempo diario | 4-8 horas | 25-40 min |
| Errores humanos | Frecuentes | Minimos |
| Trazabilidad | Parcial | 100% |
| Escalabilidad | No escala | Escala con volumen |

**Ahorro mensual estimado: 60 a 140 horas de trabajo administrativo**

---

### Slide 11: Evolucion del Producto

```
HOY                    PROXIMO PASO              VISION
------------------------------------------------------------------------

Opcion A               Opcion B                  Opcion C
MVP Manual             Scraping Bancario         Integracion Total

- Subir CSVs           - Descarga automatica     - API Contagram
- Conciliacion auto    - Sin intervencion         - Asientos contables
- Export Contagram     - Multi-banco auto         - 100% automatico

Estado: LISTO          Tiempo: 2-3 semanas       Tiempo: 1-2 meses
```

---

### Slide 12: Proximos Pasos

1. **Validar** el MVP con un mes real completo
2. **Ajustar** la tabla parametrica con datos reales de los bancos
3. **Capacitar** al operador en el flujo de trabajo
4. **Medir** el ahorro real de tiempo durante 2-4 semanas
5. **Decidir** si avanzar a Opcion B (scraping automatico)

---

*Dilcor - Distribucion de Bebidas*
*Sistema de Conciliacion Bancaria con Contagram*
*MVP 2.0 - Diciembre 2025*
