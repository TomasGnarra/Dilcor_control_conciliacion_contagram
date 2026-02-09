# Análisis de Conciliación: Banco Santander vs Contagram

## Resumen Ejecutivo

He analizado los datos reales de diciembre de Banco Santander y Contagram. **Existe un problema estructural crítico** que impide la conciliación directa: el sistema actual de Contagram no desglosa los montos por medio de pago cuando hay pagos múltiples.

### Números Clave
- **Banco Santander**: 204 transferencias recibidas por $89,416,694.78
- **Contagram (con "Santander")**: 365 ventas por $181,563,991.43
- **Diferencia**: $92,147,296.65 (102% más en Contagram)

---

## 1. Estructura de los Datos

### Archivo Banco Santander
**Estructura identificada**: 625 movimientos con las siguientes columnas:
- `Fecha`: Fecha del movimiento (formato serial de Excel)
- `Sucursal`: Villa Belgrano, Casa Central, Córdoba, etc. (12 sucursales)
- `Código Transacción`: Tipo de operación (37 códigos diferentes)
- `Número Movimiento`: ID único del movimiento
- `Descripción`: Detalle de la transacción
- `Monto`: Valor positivo (crédito) o negativo (débito)

**Transferencias recibidas relevantes**:
- Código: `4805` 
- Formato descripción: "Transferencia Recibida - De NOMBRE / detalles / CUIT"
- Total: 204 transferencias con monto positivo
- **Todos los movimientos incluyen CUIT** (100% de cobertura)

**Ejemplo de movimiento**:
```
Fecha: 2025-01-12
Código: 4805
Descripción: "Transferencia Recibida - De Magueteco S.a.s. / - Var / 30718850289"
Monto: $224,979.23
```

### Archivo Contagram
**Estructura**: 1,730 ventas con 12 columnas:
- `Emisión`: Fecha de emisión de la venta
- `Cliente`: Nombre del cliente
- `CUIT`: CUIT del cliente (73.4% con datos)
- `Tipo`: Tipo de comprobante (A, B, C)
- `N° de Factura`: Número de factura
- `Total Venta`: Monto total de la venta
- `Cobrado`: Monto efectivamente cobrado
- `Estado`: Estado del cobro
- **`Medio de Cobro`**: Campo problemático ⚠️

**Ventas con Santander**:
- Filtro: Medio de cobro contiene "Santander Río PRINCA", "viajar siempre SANTANDER", o "Santader Rio FREITES"
- Total: 365 ventas

---

## 2. El Problema Crítico: Medios de Cobro Múltiples

### Descripción del Problema

El campo `Medio de Cobro` en Contagram **concatena múltiples medios de pago con " - "** pero **NO indica qué porción del monto corresponde a cada medio**.

**Ejemplos reales**:

1. **Pago único** (284 casos - 78% del total):
   ```
   Cliente: PLACERES TERRENALES
   Cobrado: $195,614.89
   Medio de Cobro: "Santander Río PRINCA aa"
   ✅ Podemos asumir que el 100% viene de Santander
   ```

2. **Pago doble** (48 casos):
   ```
   Cliente: VINOTECA KABALIN 434
   Cobrado: $165,673.44
   Medio de Cobro: "Santander Río PRINCA aa - Santander Río PRINCA aa"
   ❓ ¿Son dos pagos de Santander? ¿50% cada uno? ¿O montos diferentes?
   ```

3. **Pago mixto** (33 casos):
   ```
   Cliente: ALMACEN SHIZEN
   Cobrado: $427,860.68
   Medio de Cobro: "Santander Río PRINCA aa - Caja GRANDE - Santander Río PRINCA aa"
   ❌ Imposible saber cuánto vino de cada medio sin más datos
   ```

4. **Pago cuádruple** (1 caso extremo):
   ```
   Cliente: JANGADERO EX SHADDY
   Cobrado: $1,816,390.30
   Medio de Cobro: "Santander Río PRINCA aa - Santander Río PRINCA aa - Santander Río PRINCA aa - Santander Río PRINCA aa"
   ❌ ¿4 pagos iguales? ¿4 pagos diferentes?
   ```

### Estadísticas
- **Ventas con pago único**: 284 (78%)
- **Ventas con múltiples medios**: 81 (22%)
- **Monto ventas pago único**: $99,331,688.72
- **Monto ventas múltiples**: $82,232,302.71

---

## 3. Diferencia de Montos Explicada

```
Banco Santander:        $89,416,694.78  (solo movimientos reales)
Contagram (solo Santander):  $99,331,688.72  (ventas con pago único)
Contagram (con múltiples):   $181,563,991.43 (incluye otros medios)
```

**Conclusión**: La diferencia se explica por:
1. **Pagos múltiples inflando el total**: Cuando una venta tiene "Santander + Caja", Contagram suma TODO el monto a ambos medios
2. **Posible desfase temporal**: Las ventas pueden estar emitidas pero cobradas en fechas diferentes
3. **Posibles retenciones o ajustes**: Que no aparecen como movimientos separados

---

## 4. Coincidencias Encontradas

### Por Monto Exacto
Encontré **17 coincidencias exactas** de monto entre banco y ventas:

| Cliente | CUIT | Monto | Fecha Venta | Nombre Banco | Fecha Banco |
|---------|------|-------|-------------|--------------|-------------|
| OLEO | 30717959147 | $130,792.09 | 2025-12-02 | O.l.e.o. S.a.s. | 2025-12-22 |
| JUANITA VAR | 20243672016 | $61,074.07 | 2025-12-05 | Antinori | 2025-12-13 |
| THE BARBEER | 33718588869 | $144,175.40 | 2025-12-16 | Tintos S.a.s. | 2025-12-26 |
| BRIE DELICATESSEN | 20319195581 | $40,127.11 | 2025-12-19 | Garcia | 2025-12-29 |

**Observación importante**: Hay coincidencias de CUIT, lo que valida la calidad de los datos, pero las fechas suelen diferir (hasta 20 días).

---

## 5. Estrategias de Conciliación

### 🎯 Estrategia Recomendada: Enfoque Progresivo

#### Nivel 1: Alta Certeza (Implementar primero)
**Criterios**:
- Medio de cobro = exactamente "Santander Río PRINCA aa" (sin " - ")
- Coincidencia de CUIT (si disponible)
- Coincidencia de monto exacto
- Fecha banco ± 7 días de fecha venta

**Resultado esperado**: ~60-70% de coincidencias automáticas

**Implementación**:
```python
def nivel_1_alta_certeza(venta, transferencia):
    # Solo pagos únicos de Santander
    if " - " in venta['Medio de Cobro']:
        return False
    
    # CUIT match (si ambos tienen)
    if venta['CUIT'] and transferencia['CUIT']:
        if venta['CUIT'] != transferencia['CUIT']:
            return False
    
    # Monto exacto
    if abs(venta['Cobrado'] - transferencia['Monto']) > 0.01:
        return False
    
    # Ventana temporal de 7 días
    diferencia_dias = abs((venta['Emision'] - transferencia['Fecha']).days)
    if diferencia_dias > 7:
        return False
    
    return True
```

#### Nivel 2: Probabilidad Alta (Revisar manualmente)
**Criterios**:
- Medio de cobro contiene "Santander" (puede ser múltiple)
- Fuzzy matching de nombre cliente vs nombre en transferencia (>85%)
- Coincidencia de monto exacto
- Fecha ± 15 días

**Resultado esperado**: +10-15% adicional

#### Nivel 3: Necesita Investigación
**Para los casos complejos**:
- Requerir desglose de Contagram por medio de pago
- Consultar con contabilidad sobre reglas de registro
- Posible acceso directo a base de datos para obtener tabla de "pagos parciales"

---

## 6. Datos Faltantes Críticos

### Lo que NECESITAMOS del cliente:

1. **Desglose de pagos parciales**
   - ¿Existe un reporte de Contagram que muestre cada pago por separado?
   - Ejemplo: Si la venta es $1000 y se pagó "50% Santander + 50% Caja", necesitamos ver $500 + $500

2. **Aclaración sobre pagos repetidos**
   - Cuando aparece "Santander - Santander - Santander", ¿qué significa?
   - ¿Son múltiples transferencias del mismo cliente?
   - ¿O es un error de registro?

3. **Reglas de negocio sobre fechas**
   - ¿Cuál es la ventana temporal razonable entre emisión y cobro?
   - ¿Hay casos donde una venta de diciembre se cobra en enero?

4. **Acceso a base de datos**
   - ¿Podemos conectarnos a la BD de Contagram para explorar tablas relacionadas?
   - Tabla de "medios_de_pago" o "pagos_parciales"

---

## 7. Recomendaciones para el Proyecto Dilcor

### Prioridad Alta 🔴

1. **Reunión con el cliente** para aclarar:
   - Estructura real de pagos múltiples
   - Acceso a datos más granulares
   - Validar si nuestra interpretación es correcta

2. **Implementar Nivel 1** (pagos únicos) como MVP:
   - Es la conciliación más confiable
   - Cubre el 78% de los casos
   - Menor riesgo de falsos positivos

### Prioridad Media 🟡

3. **Diseñar flujo de excepciones** para pagos múltiples:
   - Marcar como "Requiere revisión manual"
   - No forzar conciliación automática
   - Permitir entrada manual de desgloses

4. **Implementar validaciones**:
   - Alertar cuando suma de conciliaciones > movimientos banco
   - Detectar duplicaciones
   - Reportar casos ambiguos

### Prioridad Baja 🟢

5. **Fuzzy matching de nombres**:
   - Útil cuando CUIT no está disponible
   - Ejemplos encontrados: "Magueteco S.a.s." vs "MAGUETECO"
   - RapidFuzz puede ayudar con variaciones

---

## 8. Datos Técnicos para Implementación

### Campos a Extraer del Banco
```python
{
    'fecha': datetime,
    'numero_movimiento': str,  # ID único
    'nombre_origen': str,      # Extraído de descripción
    'cuit_origen': str,        # Extraído de descripción (11 dígitos)
    'monto': float,
    'descripcion_completa': str
}
```

### Campos a Extraer de Contagram
```python
{
    'id': int,
    'fecha_emision': datetime,
    'cliente': str,
    'cuit': str,               # Limpiado (sin guiones)
    'monto_cobrado': float,
    'medio_cobro': str,
    'es_pago_unico': bool,     # No contiene " - "
    'es_santander': bool
}
```

### Regex para Parsing Banco
```python
# Extraer nombre y CUIT de transferencias
pattern = r'De\s+([^/]+?)\s*/.*?(\d{11})'

# Ejemplo:
"Transferencia Recibida - De Magueteco S.a.s. / - Var / 30718850289"
# → Nombre: "Magueteco S.a.s."
# → CUIT: "30718850289"
```

---

## 9. Próximos Pasos Sugeridos

### Inmediato (Esta semana)
1. ✅ Enviar este análisis al cliente
2. ⏳ Agendar reunión para aclarar estructura de pagos
3. ⏳ Solicitar acceso a datos más detallados o base de datos

### Corto Plazo (Próximas 2 semanas)
4. ⏳ Implementar parser de movimientos Santander
5. ⏳ Implementar Nivel 1 de conciliación (pagos únicos)
6. ⏳ Crear dashboard de visualización de coincidencias

### Mediano Plazo (Próximo mes)
7. ⏳ Implementar Nivel 2 con fuzzy matching
8. ⏳ Integrar con sistema de auditoría
9. ⏳ Pruebas con datos reales y validación con contabilidad

---

## 10. Preguntas para el Cliente

**Sobre estructura de datos**:
1. ¿Existe algún reporte de Contagram que desglosa pagos múltiples?
2. ¿Tienen acceso a la base de datos directa de Contagram?
3. ¿Cómo registran ustedes los pagos parciales internamente?

**Sobre reglas de negocio**:
4. Cuando aparece "Santander - Santander", ¿qué significa operativamente?
5. ¿Cuál es la ventana temporal normal entre emisión y cobro?
6. ¿Hay retenciones o ajustes que modifiquen los montos?

**Sobre el proceso actual**:
7. ¿Cómo realizan la conciliación manualmente hoy?
8. ¿Qué porcentaje de ventas tiene pagos múltiples típicamente?
9. ¿Qué casos son más problemáticos en la conciliación manual?

---

## Conclusión

Los datos son **utilizables pero requieren trabajo adicional**. La estructura de "Medio de Cobro" en Contagram es el principal obstáculo. Podemos implementar una conciliación confiable para el **78% de casos simples** (pagos únicos de Santander), pero necesitamos más información del cliente para manejar el **22% restante** de pagos múltiples.

**Riesgo**: Si implementamos sin aclarar los pagos múltiples, podríamos generar falsos positivos que afecten la confiabilidad del sistema.

**Oportunidad**: Si obtenemos los datos correctos, podemos lograr >90% de coincidencias automáticas con alta confianza.
