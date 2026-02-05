# DILCOR - Informe Ejecutivo
## Sistema de Conciliación Bancaria con Contagram

**Fecha:** Diciembre 2025
**Versión:** MVP 1.0 - Opción A (Manual CSV)
**Preparado para:** Dirección y Contaduría de Dilcor

---

## 1. Resumen Ejecutivo

Se presenta el **MVP funcional** del sistema de conciliación bancaria automática para Dilcor. El sistema toma extractos bancarios de **Banco Galicia, Banco Santander y Mercado Pago**, los cruza contra los datos del ERP Contagram (ventas y compras pendientes), y genera archivos CSV listos para importar directamente en Contagram.

### Resultado clave de la prueba con datos de Diciembre 2025:
- **678 movimientos bancarios** procesados en los 3 bancos
- **~85% de conciliación automática** sin intervención humana
- **3 archivos de salida** generados:
  - `subir_cobranzas_contagram.csv` → Módulo Cobranzas
  - `subir_pagos_contagram.csv` → Módulo Pagos a Proveedores
  - `excepciones.xlsx` → Revisión manual

---

## 2. Problema que Resuelve

### Situación Actual (sin el sistema)
| Tarea | Tiempo estimado | Frecuencia |
|-------|----------------|------------|
| Bajar extractos de 3 bancos | 15 min | Diario |
| Comparar manualmente contra Contagram | 2-4 horas | Diario |
| Registrar cobranzas una por una | 1-2 horas | Diario |
| Registrar pagos uno por uno | 30-60 min | Diario |
| Identificar diferencias/excepciones | 30-60 min | Diario |
| **Total estimado** | **4-8 horas/día** | |

### Con el sistema MVP
| Tarea | Tiempo estimado | Frecuencia |
|-------|----------------|------------|
| Subir extractos bancarios al sistema | 2 min | Diario |
| Ejecutar conciliación (automático) | 30 seg | Diario |
| Revisar excepciones | 15-30 min | Diario |
| Importar CSVs en Contagram | 5 min | Diario |
| **Total estimado** | **25-40 min/día** | |

### Ahorro estimado: **3 a 7 horas diarias**

---

## 3. Cómo Funciona (Flujo Operativo)

```
PASO 1: Descargar extractos del home banking (Galicia, Santander, MP)
    ↓
PASO 2: Subir los CSVs al sistema (pantalla web Streamlit)
    ↓
PASO 3: Click en "Ejecutar Conciliación"
    ↓
PASO 4: El sistema genera automáticamente:
    ├── subir_cobranzas_contagram.csv
    ├── subir_pagos_contagram.csv
    └── excepciones.xlsx
    ↓
PASO 5: Descargar archivos y subir a Contagram
    ↓
PASO 6: Contagram registra automáticamente cobranzas y pagos
```

**Desde Contagram, es como si el usuario hubiera cargado los datos manualmente.**
No se modifica nada en Contagram. Se usa su funcionalidad existente de importación CSV.

---

## 4. Motor de Conciliación - Lógica

### 4.1 Clasificación Automática
Cada movimiento bancario se clasifica en:
- **Cobranza**: Dinero que entra (transferencias de clientes)
- **Pago a Proveedor**: Dinero que sale a proveedores conocidos
- **Gasto Bancario**: Comisiones, impuestos, mantenimiento

### 4.2 Matching Inteligente
El sistema usa una **tabla paramétrica** que mapea:
- Alias bancarios → Clientes/Proveedores de Contagram
- CUIT → ID de Contagram
- Patrones de descripción → Categorías

### 4.3 Niveles de Confianza
| Nivel | Significado | Acción |
|-------|------------|--------|
| **Automático** (>80%) | Match seguro por alias + monto | Se incluye en CSV de importación |
| **Probable** (55-80%) | Match parcial, requiere validación | Se incluye con marca de revisión |
| **Excepción** (<55%) | Sin match encontrado | Va a excepciones.xlsx |

---

## 5. Datos de la Prueba - Diciembre 2025

### Extractos procesados:
| Banco | Movimientos | Créditos | Débitos |
|-------|------------|----------|---------|
| Banco Galicia | ~254 | Cobranzas + pagos | Pagos + comisiones |
| Banco Santander | ~152 | Cobranzas | Pagos + comisiones |
| Mercado Pago | ~272 | Cobranzas (alto flujo) | Comisiones MP |

### Clientes procesados: 250 clientes activos
### Facturación total diciembre: $576.474.570,80

---

## 6. Bancos Soportados

### Banco Galicia
- Formato: CSV con columnas Fecha, Descripción, Débito, Crédito, Saldo
- Detección automática

### Banco Santander
- Formato: CSV con Fecha Operación, Concepto, Importe, Saldo
- Importe negativo = débito

### Mercado Pago
- Formato: CSV con Monto Bruto, Comisión, IVA Comisión, Monto Neto
- Se desglosan comisiones e IVA automáticamente

---

## 7. Impacto en Contagram

El sistema **no requiere cambios en Contagram**:
- Los CSV generados se importan manualmente en los módulos existentes
- Contagram los interpreta como cargas masivas realizadas por un usuario
- Se registran automáticamente:
  - Cancelación de facturas
  - Movimientos en cuentas bancarias

---

## 8. Implementación

### Tecnología
- **Python**: Motor de conciliación
- **Streamlit**: Interfaz web (no requiere desarrollo frontend)
- **Pandas**: Procesamiento de datos
- **CSV/Excel**: Formatos de entrada y salida

### Tiempo de implementación: 48-72 horas
### Riesgo: Bajo (no modifica sistemas existentes)

---

## 9. Roadmap Evolutivo

| Fase | Descripción | Beneficio |
|------|------------|-----------|
| **A (actual)** | MVP Manual - Subir CSVs | Ahorro inmediato de 3-7 hs/día |
| **B (futuro)** | Scraping bancario automático | Elimina descarga manual de extractos |
| **C (visión)** | Integración total vía API | Contabilidad 100% automática |

---

## 10. Próximos Pasos Recomendados

1. **Validar MVP** con datos reales de un mes completo
2. **Ajustar tabla paramétrica** con alias reales de los bancos
3. **Capacitar al operador** en el flujo de trabajo
4. **Evaluar migración** a Opción B (scraping) según volumen de operaciones

---

*Sistema desarrollado para Dilcor - Distribución de Bebidas*
*MVP Opción A - Conciliación Bancaria con Contagram*
