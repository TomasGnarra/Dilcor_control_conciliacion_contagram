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

### Seccion 1: Niveles de Match (fila de arriba)

El sistema clasifica cada movimiento bancario en 4 niveles:

| Nivel | Que significa | Color |
|-------|--------------|-------|
| **Match Exacto** | Se identifico al cliente/proveedor Y el monto coincide con una factura especifica | Verde |
| **Probable - Duda de ID** | El nombre es parecido pero no identico (ej: "PRITTY" vs "PRITY"). Requiere que alguien confirme si es el mismo cliente | Amarillo |
| **Probable - Dif. de Cambio** | El cliente/proveedor esta identificado, pero el monto del banco no coincide exactamente con ninguna factura individual. Puede ser un pago que cubre varias facturas, un pago parcial, o una diferencia de redondeo | Naranja |
| **No Match** | El sistema no pudo identificar de quien es el movimiento. Hay que revisar manualmente | Rojo |

**Ejemplo practico:**
- PRITTY transfiere $500,000 por banco. En Contagram, PRITTY tiene 3 facturas: $200K, $180K, $120K.
- El sistema identifica que es PRITTY (match de identidad exacto), pero $500K no coincide con ninguna factura individual.
- Resultado: **Probable - Dif. de Cambio**. El contador sabe que es de PRITTY, pero debe revisar contra que facturas se aplica.

### Seccion 2: Impacto Financiero (fila de abajo)

| KPI | Que muestra | Como se lee |
|-----|------------|-------------|
| **Cobrado en Bancos** | Suma total de creditos (dinero que entro) en los 3 bancos | Es lo que efectivamente se cobro |
| **Facturado en Contagram** | Suma total de las ventas pendientes cargadas en Contagram | Es lo que se esperaba cobrar segun las facturas |
| **Revenue Gap (Banco - Contagram)** | La diferencia entre lo cobrado y lo facturado. Idealmente es $0. Si es negativo, se facturo mas de lo que entro. Si es positivo, entro mas de lo facturado | Un gap chico (ej: -$260) es normal por redondeos. Un gap grande indica facturas no cobradas o cobros sin factura |
| **Pagos a Proveedores** | Total de debitos clasificados como pagos a proveedores | Dinero que salio para pagar a Coca Cola, Quilmes, etc. |
| **Gastos Bancarios** | Total de comisiones, impuestos y cargos bancarios | Costo del sistema bancario (mantenimiento, IVA, comisiones MP) |
| **Diferencias de Cambio (neto)** | Suma neta de las diferencias de monto en los matches "probable_dif_cambio". Muestra "+X / -Y" donde X = cobros de mas, Y = cobros de menos | Si es muy negativo, hay varios clientes pagando menos de lo facturado. Sirve para detectar perdidas |
| **Dinero sin Conciliar** | Monto total de los movimientos "no match" | Plata en el banco que no sabemos de quien es. Requiere revision urgente |

### Seccion 3: Desglose por Banco

Tabla que muestra la distribucion de matches por cada banco. Util para ver si un banco tiene mas problemas que otros (ej: Mercado Pago suele tener mas excepciones por los alias como "MERPAG*").

---

## Estructura del Proyecto

```
├── app.py                          # App Streamlit (interfaz web con branding Dilcor)
├── src/
│   ├── motor_conciliacion.py       # Orquestador: normaliza, clasifica, matchea, genera KPIs
│   ├── normalizador.py             # Convierte CSV de cada banco a formato unificado
│   ├── clasificador.py             # Clasifica: cobranza, pago, gasto bancario
│   ├── matcher.py                  # Motor de matching ternario con umbrales configurables
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

El sistema detecta automaticamente de que banco es cada archivo por los nombres de las columnas. No hace falta indicarlo manualmente.

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
