# DILCOR - Informe Ejecutivo
## Sistema de Conciliacion Bancaria con Contagram

**Fecha:** Diciembre 2025
**Version:** MVP 2.0 - Opcion A (Manual CSV)
**Preparado para:** Direccion y Contaduria de Dilcor

---

## 1. Resumen Ejecutivo

Se presenta el **MVP funcional** del sistema de conciliacion bancaria automatica para Dilcor. El sistema toma extractos bancarios de **Banco Galicia, Banco Santander y Mercado Pago**, los cruza contra los datos del ERP Contagram (ventas y compras pendientes), y genera archivos listos para importar directamente en Contagram.

### Resultado de la prueba con datos de Diciembre 2025:

| Dato | Valor |
|------|-------|
| Movimientos bancarios procesados | 679 |
| Tasa de identificacion (sabemos de quien es) | 95.8% |
| Match exacto (identidad + monto = factura) | 11.3% |
| Probable - requiere revision parcial | 84.5% |
| Excepciones (revision manual total) | 4.2% (28 movimientos) |
| Facturacion procesada | $576.474.570 |
| Dinero sin conciliar | $58.052.193 |

**En resumen:** de cada 100 movimientos bancarios, el sistema identifica automaticamente 96. Solo 4 requieren que el contador busque manualmente de quien es el dinero.

---

## 2. Problema que Resuelve

### Situacion actual (sin el sistema)

Hoy, la contaduria de Dilcor concilia los bancos a mano:

| Tarea | Tiempo estimado | Frecuencia |
|-------|----------------|------------|
| Bajar extractos de 3 bancos | 15 min | Diario |
| Comparar cada movimiento contra Contagram | 2-4 horas | Diario |
| Registrar cobranzas una por una | 1-2 horas | Diario |
| Registrar pagos a proveedores | 30-60 min | Diario |
| Identificar diferencias y excepciones | 30-60 min | Diario |
| **Total** | **4-8 horas/dia** | |

### Con el sistema

| Tarea | Tiempo estimado | Frecuencia |
|-------|----------------|------------|
| Bajar extractos del home banking | 5 min | Diario |
| Subir archivos al sistema y ejecutar | 2 min | Diario |
| Revisar excepciones (28 movimientos en dic.) | 15-30 min | Diario |
| Importar CSVs en Contagram | 5 min | Diario |
| **Total** | **25-40 min/dia** | |

### Ahorro estimado: 3 a 7 horas por dia

---

## 3. Como funciona paso a paso

```
PASO 1: Descargar extractos del home banking (Galicia, Santander, Mercado Pago)
         Son los CSV que cada banco permite exportar desde su web.
    |
    v
PASO 2: Abrir la app (http://localhost:8501) y subir los archivos
         Hay una pestana por cada banco. Se arrastran los CSV.
    |
    v
PASO 3: Click en "Ejecutar Conciliacion"
         El sistema procesa todo en menos de 10 segundos.
    |
    v
PASO 4: Revisar el dashboard
         Muestra cuantos movimientos se identificaron, cuanto dinero hay
         en cada categoria, y que diferencias existen.
    |
    v
PASO 5: Descargar los archivos generados:
         - subir_cobranzas_contagram.csv  (para el modulo Cobranzas)
         - subir_pagos_contagram.csv      (para el modulo Pagos)
         - excepciones.xlsx               (para revision manual)
    |
    v
PASO 6: Importar los CSV en Contagram
         Se usan los modulos de importacion que ya tiene Contagram.
         Para Contagram, es como si el operador hubiera cargado los datos a mano.
```

**Importante:** No se instala nada en Contagram. No se necesitan APIs ni accesos especiales. Se usa la funcionalidad de importacion CSV que Contagram ya tiene.

---

## 4. Niveles de Match - Que significa cada uno?

El motor de conciliacion clasifica cada movimiento bancario en uno de 4 niveles. Esto determina cuanto trabajo manual necesita el contador.

### Match Exacto

- **Que es:** El sistema identifico al cliente o proveedor Y encontro una factura cuyo monto coincide exactamente (dentro de un 0.5% de tolerancia).
- **Ejemplo:** El banco muestra "TRANSF PRITTY $200,000". En Contagram, PRITTY tiene una factura pendiente por $200,000. Todo cuadra.
- **Accion del contador:** Ninguna. Se puede importar directo a Contagram.

### Probable - Duda de ID

- **Que es:** El sistema encontro un nombre parecido pero no identico. Puede ser que el banco escriba el nombre de forma ligeramente distinta.
- **Ejemplo:** El banco muestra "MERPAG*PRITY" (sin la doble T). El sistema cree que puede ser PRITTY pero no esta 100% seguro.
- **Accion del contador:** Verificar si "PRITY" es efectivamente PRITTY. Si lo es, agregar el alias "PRITY" a la tabla parametrica para que la proxima vez matchee automatico.

### Probable - Diferencia de Cambio

- **Que es:** El sistema identifico al cliente/proveedor con certeza (el nombre coincide), pero el monto del banco no coincide exactamente con ninguna factura individual en Contagram.
- **Por que pasa:** Es comun que un cliente pague varias facturas juntas en una sola transferencia, o que haga un pago parcial, o que haya diferencias de redondeo o retenciones.
- **Ejemplo:** El banco muestra "TRANSF PRITTY $500,000". PRITTY tiene facturas por $200K + $180K + $120K = $500K total, pero ninguna individual es $500K.
- **Accion del contador:** Sabe que la plata es de PRITTY. Solo necesita indicar contra que facturas se aplica el pago.

### No Match (Excepcion)

- **Que es:** El sistema no pudo identificar de quien es el movimiento. No encontro ningun nombre parecido en la tabla parametrica.
- **Por que pasa:** Puede ser un cliente nuevo, un alias que el banco usa por primera vez, o una transferencia con descripcion poco clara.
- **Ejemplo:** El banco muestra "TRANSF TERCEROS CBU 6008350583". No hay forma de saber de quien es sin revisar.
- **Accion del contador:** Identificar manualmente de quien es. Si lo identifica, agregar el alias a la tabla parametrica.
- **En la app:** Estos movimientos aparecen en la pestana "Excepciones" con la accion sugerida "Agregar alias a tabla parametrica".

---

## 5. KPIs de Impacto Financiero - Que muestran?

El dashboard incluye una seccion de "Impacto Financiero" con 8 indicadores clave. Aca se explica cada uno:

### Fila superior (Cobranzas)

| KPI | Que muestra | Como se lee |
|-----|------------|-------------|
| **Cobrado en Bancos** | Suma total del dinero que entro por los 3 bancos (solo creditos clasificados como cobranzas) | Es lo que efectivamente se cobro en el periodo. En diciembre: $576.474.310,88 |
| **Facturado en Contagram** | Suma total de las ventas pendientes que figuran en el ERP | Es lo que se esperaba cobrar segun las facturas emitidas. En diciembre: $576.474.570,80 |
| **Revenue Gap** | La resta: Cobrado - Facturado. Mide si la plata que entro al banco coincide con lo que se facturo | En diciembre: -$259,92 (es decir, se facturo $260 mas de lo que entro al banco). Un numero cercano a $0 es ideal. Si el gap es muy grande, indica facturas emitidas pero no cobradas, o cobros que no tienen factura asociada |

### Fila inferior (Operativo)

| KPI | Que muestra | Como se lee |
|-----|------------|-------------|
| **Pagos a Proveedores** | Total de dinero que salio de los bancos hacia proveedores (Coca Cola, Quilmes, etc.) | En diciembre: $170.350.000 en 26 pagos |
| **Gastos Bancarios** | Total de comisiones, mantenimiento de cuenta, IVA comisiones, impuestos bancarios | En diciembre: $1.236.860 en 16 movimientos. Es el costo de operar con los bancos |
| **Diferencias de Cambio (neto)** | Suma neta de todas las diferencias de monto detectadas en los matches tipo "dif. de cambio". Muestra un desglose +X / -Y | +X = clientes que pagaron de mas (a favor de Dilcor). -Y = clientes que pagaron de menos (en contra). El neto indica si Dilcor esta cobrando mas o menos de lo facturado |
| **Dinero sin Conciliar** | Monto total de los movimientos "no match" (excepciones) | Es plata que esta en el banco pero no sabemos de quien es. Requiere revision urgente. En diciembre: $58.052.194 en 28 movimientos |

---

## 6. Pestanas de Resultados

### Pestana "Por Banco"
Muestra un resumen de como quedo la conciliacion por cada banco. Util para ver si un banco en particular tiene mas problemas (por ejemplo, Mercado Pago suele tener mas excepciones porque sus alias son crípticos como "MERPAG*").

### Pestana "Cobranzas"
Lista de todas las cobranzas identificadas, con: cliente, CUIT, monto cobrado, factura asociada, banco, nivel de match, y porcentaje de confianza. Este archivo se descarga y se importa en el modulo Cobranzas de Contagram.

### Pestana "Pagos"
Lista de todos los pagos a proveedores identificados, con: proveedor, CUIT, monto pagado, OC asociada, banco, nivel de match. Se descarga y se importa en el modulo Pagos a Proveedores de Contagram.

### Pestana "Excepciones"
Los movimientos que el sistema no pudo identificar. Muestra: fecha, banco, monto, descripcion original del banco, y la accion sugerida (generalmente "Agregar alias a tabla parametrica"). Se descarga como Excel para que el contador los revise.

### Pestana "Detalle Completo"
Vista completa de todos los movimientos con todos los campos. Util para buscar un movimiento especifico o hacer analisis detallado.

---

## 7. La Tabla Parametrica

La tabla parametrica (`data/config/tabla_parametrica.csv`) es el "cerebro" del sistema. Es un archivo simple que dice:

> "Cuando el banco diga X, eso corresponde al cliente/proveedor Y de Contagram"

| Lo que dice el banco | Lo que el sistema entiende |
|---------------------|---------------------------|
| MERPAG*PRITTY | Cobranza del cliente PRITTY SA (ID 1042) |
| TRANSF BONPRIX | Cobranza del cliente BONPRIX (ID 1089) |
| PAG COCA COLA ANDINA | Pago al proveedor Coca Cola Andina (ID 5001) |
| COMISION MANTENIMIENTO | Gasto bancario (no va a Contagram) |

**Esta tabla la mantiene el contador.** Cada vez que aparece una excepcion nueva, se agrega una linea y listo. No hace falta tocar codigo ni llamar a sistemas.

Con el tiempo, la tabla crece y cada vez hay menos excepciones. El objetivo es llegar a 0 excepciones.

---

## 8. Impacto en Contagram

El sistema **no modifica nada en Contagram**:

- No se instala nada dentro de Contagram
- No se necesitan APIs, plugins, ni accesos especiales
- Se usa la funcionalidad de importacion CSV que Contagram ya tiene
- Para Contagram, es como si el usuario hubiera cargado los datos manualmente

Cuando se importan los CSV, Contagram:
- Cancela las facturas correspondientes
- Registra los movimientos en las cuentas bancarias
- Genera los asientos contables como siempre

---

## 9. Tecnologia

| Componente | Tecnologia | Por que |
|-----------|-----------|---------|
| Motor de conciliacion | Python 3 + Pandas | Robusto, rapido para procesar miles de filas |
| Interfaz web | Streamlit | App web profesional sin necesidad de desarrollo frontend |
| Persistencia (opcional) | TiDB Cloud | Base de datos para guardar historico de conciliaciones |
| Formatos | CSV, Excel | Compatibles con Contagram y cualquier herramienta |

### Requerimientos minimos:
- PC con Python 3.9 o superior
- Navegador web (Chrome, Firefox, Edge)
- No necesita internet (excepto para TiDB Cloud, que es opcional)

---

## 10. Roadmap - Siguiente pasos

| Fase | Que es | Beneficio | Tiempo |
|------|--------|-----------|--------|
| **A (actual)** | MVP Manual: subir CSVs, ejecutar, importar | Ahorro inmediato de 3-7 hs/dia | Listo |
| **B (futuro)** | Scraping bancario: descarga automatica de extractos | Elimina la descarga manual de los extractos | 2-3 semanas |
| **C (vision)** | Integracion API con Contagram | Conciliacion 100% automatica, sin archivos CSV | 1-2 meses |

### Proximos pasos recomendados:

1. **Validar** el MVP con un mes completo de datos reales
2. **Ajustar la tabla parametrica** con los alias reales de los bancos (los de prueba son simulados)
3. **Capacitar** al operador en el flujo de trabajo (subir → ejecutar → descargar → importar)
4. **Medir** el ahorro real de tiempo durante 2-4 semanas
5. **Decidir** si avanzar a la Opcion B (scraping bancario automatico)

---

*Sistema desarrollado para Dilcor - Distribucion de Bebidas*
*MVP 2.0 Opcion A - Conciliacion Bancaria con Contagram*
*Diciembre 2025*
