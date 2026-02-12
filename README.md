# DILCOR - Conciliacion Bancaria con Contagram

Sistema de conciliacion automatica entre extractos bancarios y el ERP Contagram para **Dilcor**, distribuidora de bebidas.

**Version:** 2.0 - MVP Opcion A (Manual CSV)
**Fecha:** Diciembre 2025

---

## Que es esto?

Es una aplicacion web (Streamlit) que toma los extractos bancarios de los 3 bancos de Dilcor, los cruza contra los datos de Contagram, e identifica automaticamente:

- **Cobranzas**: que clientes pagaron y cuanto
- **Pagos a proveedores**: que pagos salieron y a quien
- **Gastos bancarios**: comisiones, impuestos, mantenimiento de cuenta
- **Excepciones**: movimientos que el sistema no pudo identificar y requieren revision manual

Al final, genera archivos CSV listos para importar en Contagram, como si los hubiera cargado un operador a mano.

---

## Como se usa?

### Paso 1: Instalar

```bash
pip install -r requirements.txt
```

### Paso 2: Generar datos de prueba (solo la primera vez)

```bash
python generar_datos_test.py
```

Esto crea extractos bancarios simulados basados en las ventas reales de diciembre 2025 (252 clientes, $576M).

### Paso 3: Iniciar la aplicacion

```bash
streamlit run app.py
```

Se abre en el navegador en `http://localhost:8501`. No necesitas cuenta ni internet.

### Paso 4: Dentro de la app

1. **Subir extractos**: Hay una pestana por cada banco (Galicia, Santander, Mercado Pago). Subis el CSV de cada uno.
2. **Subir datos de Contagram**: En la pestana "Datos Contagram" subis las ventas y compras pendientes.
3. **Click en "Ejecutar Conciliacion"**: El sistema procesa todo en segundos.
4. **Revisar resultados**: El dashboard muestra el resumen, y las pestanas Cobranzas/Pagos/Excepciones muestran el detalle.
5. **Descargar archivos**: Cada pestana tiene boton de descarga (CSV o Excel).

### Paso 5: Importar en Contagram

Los archivos descargados se importan en los modulos de Contagram:
- `subir_cobranzas_contagram.csv` → Modulo Cobranzas
- `subir_pagos_contagram.csv` → Modulo Pagos a Proveedores
- `excepciones.xlsx` → Para revision manual del contador

---

## Que muestra el Dashboard?

### Resumen General (fila superior)

5 tarjetas con los numeros clave: Total Movimientos, % Conciliacion Total, Match Exacto, Requieren Revision, Sin Identificar.

### 4 Niveles de Match

| Nivel | Que significa | Color |
|-------|--------------|-------|
| **Match Exacto (directo)** | Se identifico al cliente/proveedor Y el monto coincide con una factura 1:1 | Verde |
| **Match Exacto (suma)** | Se identifico al cliente/proveedor Y el monto coincide con la **suma de varias facturas** | Verde |
| **Probable - Duda de ID** | El nombre es parecido pero no identico (ej: "PRITTY" vs "PRITY"). Requiere confirmar si es el mismo cliente | Amarillo |
| **Probable - Dif. de Cambio** | El cliente/proveedor esta identificado, pero el monto no coincide con ninguna factura individual ni con ninguna combinacion. Revisar manualmente | Naranja |
| **No Match** | No se pudo identificar de quien es el movimiento. Revisar manualmente | Rojo |

### Bloque 1: COBROS (Creditos / Ventas)

Header negro. Muestra todo lo relacionado con dinero que **entra** al banco (cobranzas de clientes):

| Fila | KPIs | Que muestra |
|------|------|-------------|
| **Montos principales** | Cobrado en Bancos, Facturado en Contagram, Revenue Gap | Cuanto entro, cuanto se esperaba, y la diferencia. Revenue Gap ideal = $0 |
| **Desglose por nivel** | Match Exacto / Duda ID / Dif. Cambio / Sin Identificar | Cantidad de movimientos y monto en cada nivel. Match Exacto muestra cuantos son 1:1 y cuantos por suma |
| **Resumen de flujo** | Conciliado 100% / Identificado, asignar facturas / Sin identificar | Porcentaje del dinero en cada estado. Verde = listo, Amarillo = falta asignar facturas, Rojo = revisar manualmente |
| **Tipo match + Diferencias** | Match directo / Match por suma / Cobrado de mas / Cobrado de menos | Cuantos matchearon 1:1 vs sumando facturas, y diferencias de dinero a favor o en contra de Dilcor |

### Bloque 2: PAGOS A PROVEEDORES (Debitos)

Header verde. Muestra todo lo relacionado con dinero que **sale** del banco (pagos a proveedores):

| Fila | KPIs | Que muestra |
|------|------|-------------|
| **Montos principales** | Pagado en Bancos, OCs en Contagram, Payment Gap | Cuanto se pago, cuanto habia en ordenes de compra, y la diferencia |
| **Desglose por nivel** | Match Exacto / Duda ID / Dif. Cambio / Sin Identificar | Cantidad y monto por nivel para pagos a proveedores. Match Exacto muestra 1:1 vs suma |
| **Resumen de flujo** | Conciliado 100% / Identificado, asignar OCs / Sin identificar | Porcentaje del dinero pagado en cada estado. Verde = conciliado, Amarillo = falta asignar OCs, Rojo = revisar |
| **Tipo match + Diferencias** | Match directo / Match por suma / Pagado de mas / Pagado de menos | Cuantos matchearon 1:1 vs sumando OCs, y diferencias a favor o en contra |

### Gastos Bancarios

Barra informativa al final: total de comisiones, impuestos y mantenimiento de cuenta. No va a Contagram.

### Desglose por Banco

Tabla expandible por banco (Galicia, Santander, Mercado Pago) con la distribucion de matches de cada uno.

---

## Motor de Matching Inteligente (rapidfuzz)

El sistema usa la libreria **rapidfuzz** para identificar clientes y proveedores incluso cuando el banco escribe el nombre de forma distinta a como figura en Contagram.

### Como funciona?

Cuando el banco dice `MERPAG*PRITTY-RET` y en la tabla parametrica el alias es `PRITTY SA`, el sistema:

1. **Normaliza ambos textos**: quita acentos, simbolos, convierte a minusculas, y elimina palabras sin valor (SA, SRL, de, la, etc.)
   - `MERPAG*PRITTY-RET` → `merpag pritty ret`
   - `PRITTY SA` → `pritty`

2. **Calcula 3 scores de similitud** usando algoritmos complementarios:

   | Algoritmo | Peso | Para que sirve | Ejemplo |
   |-----------|------|---------------|---------|
   | **token_set_ratio** | 45% | Ignora orden de palabras y palabras extra | "PRITTY SA" vs "SA PRITTY" → 100% |
   | **token_sort_ratio** | 30% | Compara tokens ordenados alfabeticamente | "DISTRIBUIDORA PRITTY" vs "PRITTY DISTRIBUIDORA" → 100% |
   | **partial_ratio** | 25% | Detecta substrings parciales | "MERPAG*PRITTY" vs "PRITTY" → alto |

3. **Combina los scores** en un promedio ponderado:
   ```
   Score final = (0.45 x token_set) + (0.30 x token_sort) + (0.25 x partial)
   ```

4. **Clasifica segun umbrales**:
   - Score >= 80% → **Match Exacto** (identidad confirmada)
   - Score >= 55% → **Probable - Duda de ID** (parecido pero no seguro)
   - Score < 55% → **No Match** (no se reconoce)

### Boost de confianza

Si alguna palabra significativa (>3 caracteres) de la descripcion bancaria coincide con el nombre del cliente/proveedor, el sistema sube la confianza a 85% automaticamente. Esto captura casos como:
- Banco: `TRANSF PRITTY DISTRIBUIDORA` → la palabra "PRITTY" coincide → boost a 85%

### Por que 3 algoritmos y no 1?

Los extractos bancarios tienen variaciones impredecibles:
- **Orden cambiado**: "COCA COLA" vs "COLA COCA" → `token_set_ratio` lo resuelve
- **Sufijos legales**: "PRITTY SRL" vs "PRITTY SAIC" → la normalizacion los quita
- **Nombres cortados**: "MERPAG*PRIT" vs "PRITTY" → `partial_ratio` lo detecta
- **Prefijos de banco**: "TRANSF DEBIN BONPRIX" vs "BONPRIX" → `token_set_ratio` ignora las palabras extra

La combinacion ponderada de los 3 algoritmos da un score robusto que funciona bien para el 95.8% de los casos reales.

---

## Estructura del Proyecto

```
├── app.py                          # App Streamlit (interfaz web con branding Dilcor)
├── src/
│   ├── motor_conciliacion.py       # Orquestador: normaliza, clasifica, matchea, genera KPIs
│   ├── normalizador.py             # Convierte CSV de cada banco a formato unificado
│   ├── clasificador.py             # Clasifica: cobranza, pago, gasto bancario
│   ├── matcher.py                  # Motor de matching ternario con umbrales configurables
│   ├── fuzzy_matcher.py            # Similitud de texto con rapidfuzz (3 algoritmos ponderados)
│   └── db_connector.py             # Persistencia en TiDB Cloud (opcional)
├── data/
│   ├── test/                       # Extractos bancarios simulados (dic 2025)
│   ├── contagram/                  # Ventas y compras pendientes de Contagram
│   └── config/                     # Tabla parametrica (alias banco → cliente Contagram)
├── .streamlit/
│   ├── config.toml                 # Tema visual (colores Dilcor)
│   └── secrets.toml                # Credenciales TiDB (NO se sube al repo)
├── docs/
│   ├── INFORME_EJECUTIVO.md        # Informe detallado para direccion
│   └── PRESENTACION_EJECUTIVA.md   # Slides para reunion
├── output/                         # Archivos generados por la conciliacion
├── generar_datos_test.py           # Genera datos de prueba desde ventas reales
├── test_conciliacion.py            # Tests end-to-end
└── requirements.txt                # Dependencias Python
```

---

## Bancos Soportados

| Banco | Formato CSV esperado | Deteccion |
|-------|---------------------|-----------|
| **Banco Galicia** | Fecha, Descripcion, Debito, Credito, Saldo | Automatica por columnas |
| **Banco Santander** | Fecha Operacion, Concepto, Importe (+/-), Saldo | Automatica por columnas |
| **Mercado Pago** | Fecha, Descripcion, Monto Bruto, Comision MP, IVA, Monto Neto | Automatica por columnas |

El sistema detecta automaticamente de que banco es cada archivo por los nombres de las columnas. Opcionalmente, al subir un extracto en modo Manual, se puede elegir el banco explicitamente con un selector.

### Filtro por Medio de Pago (Modo Manual)

Cuando se suben ventas de Contagram en modo Manual, el sistema detecta la columna "Medio de Cobro" y muestra un `multiselect` con todos los medios de pago encontrados en el archivo.

Si se eligio un banco en el paso anterior, el sistema **pre-selecciona automaticamente** los medios de pago relevantes usando el mapeo definido en `data/config/mapeo_banco_medio_pago.json`:

```json
{
  "Banco Santander": ["Santander Río PRINCA", "Santander"],
  "Banco Galicia": ["Galicia", "Banco Galicia"],
  "Mercado Pago": ["Mercado Pago PEREYRA", "MercadoPago", "MERPAG"]
}
```

El matching es **parcial y case-insensitive**: si el medio de cobro del archivo *contiene* algun valor del mapeo, se pre-selecciona. El usuario puede ajustar la seleccion manualmente antes de ejecutar la conciliacion.

**Si no se selecciona ningun medio de pago**, la conciliacion se ejecuta contra todas las ventas (comportamiento original).

El archivo JSON es editable sin tocar codigo. Para agregar un nuevo banco o medio de pago, simplemente editarlo y reiniciar la app.

---

## Umbrales Configurables

Desde el sidebar de la app se pueden ajustar los umbrales del matching:

| Parametro | Default | Para que sirve |
|-----------|---------|---------------|
| Umbral ID Exacto | 80% | Minima similitud de alias para considerarlo match exacto |
| Umbral ID Probable | 55% | Minima similitud para considerarlo "duda de ID" |
| Tolerancia Monto Exacto | 0.5% | Diferencia maxima de monto para match exacto |
| Tolerancia Monto Probable | 1.0% | Diferencia maxima de monto para "diferencia de cambio" |
| Tolerancia Monto Absoluta | $500 | Diferencia absoluta maxima (para montos chicos) |

---

## Tabla Parametrica

El archivo `data/config/tabla_parametrica.csv` es la "inteligencia" del sistema. Mapea:

```
alias_banco → nombre_contagram, id_contagram, cuit, tipo
```

Ejemplo:
| alias_banco | nombre_contagram | id_contagram | cuit | tipo |
|-------------|-----------------|--------------|------|------|
| PRITTY | PRITTY SA | 1042 | 30-50012345-6 | Cliente |
| COCA COLA ANDINA | COCA COLA ANDINA SA | 5001 | 30-50001234-5 | Proveedor |

**Cuando un movimiento cae en "Excepciones", la accion sugerida es agregar el alias a esta tabla.** Asi, la proxima vez el sistema lo reconoce automaticamente. Con el tiempo, cada vez menos movimientos caen en excepciones.

---

## Persistencia TiDB Cloud (opcional)

Si se configura `.streamlit/secrets.toml` con las credenciales de TiDB Cloud, el sistema guarda cada corrida de conciliacion en la tabla `historico_conciliaciones`. Esto permite:
- Ver el historial de conciliaciones
- Comparar meses
- Auditar cambios

Si no se configura, la app funciona igual pero sin persistencia.

---

## Documentacion

- [Informe Ejecutivo](docs/INFORME_EJECUTIVO.md) - Explicacion detallada para direccion y contaduria
- [Presentacion Ejecutiva](docs/PRESENTACION_EJECUTIVA.md) - Slides para reunion de presentacion
