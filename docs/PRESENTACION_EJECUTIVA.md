# DILCOR
## Conciliación Bancaria Automática

---

### Slide 1: El Problema

**Hoy, la conciliación bancaria de Dilcor es 100% manual.**

- Se revisan 3 bancos por separado (Galicia, Santander, Mercado Pago)
- Se cruzan manualmente contra Contagram
- Se cargan cobranzas y pagos uno por uno
- Se buscan diferencias a mano

**Tiempo estimado: 4 a 8 horas diarias**

---

### Slide 2: La Solución

**Un sistema que hace la conciliación automática.**

```
Extractos Bancarios (CSV) → Sistema → Archivos listos para Contagram
```

El operador solo necesita:
1. Bajar los extractos del home banking
2. Subirlos al sistema
3. Descargar los CSVs generados
4. Importarlos en Contagram

**Tiempo estimado: 25 a 40 minutos diarios**

---

### Slide 3: Demo en Vivo

**Procesamiento de Diciembre 2025:**

| Métrica | Valor |
|---------|-------|
| Movimientos procesados | 678 |
| Clientes conciliados | 250 |
| Tasa de conciliación automática | ~85% |
| Facturación procesada | $576.474.570 |
| Archivos generados | 3 (cobranzas, pagos, excepciones) |

*Se ejecuta la demo en vivo con Streamlit*

---

### Slide 4: Qué Genera el Sistema

| Archivo | Destino en Contagram | Contenido |
|---------|---------------------|-----------|
| `subir_cobranzas_contagram.csv` | Módulo Cobranzas | Cobros identificados con cliente, factura y monto |
| `subir_pagos_contagram.csv` | Módulo Pagos | Pagos a proveedores con OC asociada |
| `excepciones.xlsx` | Revisión manual | Movimientos sin match para resolver |

---

### Slide 5: No se Toca Contagram

El sistema **trabaja por fuera** de Contagram.

- No se instala nada en Contagram
- No se necesitan APIs ni accesos especiales
- Se usa la funcionalidad de importación CSV que ya tiene Contagram
- Para Contagram, es como si el usuario cargara los datos manualmente

**Riesgo: CERO**

---

### Slide 6: Inteligencia del Motor

**El sistema aprende los patrones de cada banco:**

| Banco dice... | El sistema entiende... |
|---------------|----------------------|
| `MERPAG*PRITTY` | Cobranza de cliente PRITTY vía Mercado Pago |
| `TRANSF BONPRIX` | Cobranza de cliente BONPRIX vía transferencia |
| `PAG COCA COLA ANDINA` | Pago a proveedor Coca Cola |
| `COMISION MANTENIMIENTO` | Gasto bancario (no va a Contagram) |

Se usa una **tabla paramétrica** que encapsula el conocimiento del negocio y se puede actualizar sin tocar código.

---

### Slide 7: 3 Niveles de Match

| Nivel | Confianza | Qué pasa |
|-------|-----------|----------|
| **Automático** | Alta (>80%) | Va directo al CSV de importación |
| **Probable** | Media (55-80%) | Se incluye pero marcado para revisión |
| **Excepción** | Baja (<55%) | Va al Excel de excepciones |

El objetivo es que con el tiempo, cada vez más movimientos sean automáticos.

---

### Slide 8: Ahorro Concreto

| Concepto | Sin sistema | Con sistema |
|----------|------------|-------------|
| Tiempo diario | 4-8 horas | 25-40 min |
| Errores humanos | Frecuentes | Mínimos |
| Trazabilidad | Parcial | 100% |
| Escalabilidad | No escala | Escala con volumen |

**Ahorro mensual estimado: 60 a 140 horas de trabajo administrativo**

---

### Slide 9: Evolución del Producto

```
HOY                    PRÓXIMO PASO              VISIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Opción A               Opción B                  Opción C
MVP Manual             Scraping Bancario         Integración Total

• Subir CSVs           • Descarga automática     • API Contagram
• Conciliación auto    • Sin intervención         • Asientos contables
• Export Contagram     • Multi-banco auto         • 100% automático

Implementación:        Implementación:           Implementación:
48-72 horas            2-3 semanas               1-2 meses
```

---

### Slide 10: Próximos Pasos

1. **Validar** el MVP con un mes real completo
2. **Ajustar** la tabla paramétrica con datos reales de los bancos
3. **Capacitar** al operador en el flujo de trabajo
4. **Medir** el ahorro real de tiempo durante 2-4 semanas
5. **Decidir** si avanzar a Opción B (scraping automático)

---

### Slide 11: Inversión y Retorno

| Item | Detalle |
|------|---------|
| Implementación MVP | 48-72 horas de desarrollo |
| Mantenimiento | Actualizar tabla paramétrica cuando cambian clientes |
| Retorno esperado | Ahorro de 60-140 hs/mes de trabajo administrativo |
| Riesgo | Bajo - No modifica sistemas existentes |

---

*Dilcor - Distribución de Bebidas*
*Sistema de Conciliación Bancaria con Contagram*
*MVP Opción A - Diciembre 2025*
