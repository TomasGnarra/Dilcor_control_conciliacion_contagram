# DILCOR - Conciliación Bancaria con Contagram

Sistema de conciliación automática entre extractos bancarios y Contagram (ERP) para Dilcor, distribuidora de bebidas.

## MVP - Opción A (Manual CSV)

El sistema toma extractos bancarios de **Banco Galicia, Banco Santander y Mercado Pago**, los cruza contra datos de Contagram, y genera archivos CSV listos para importar.

### Flujo

```
Extractos Bancarios (CSV) → Motor de Conciliación → CSVs para Contagram
```

### Outputs
- `subir_cobranzas_contagram.csv` → Módulo Cobranzas de Contagram
- `subir_pagos_contagram.csv` → Módulo Pagos a Proveedores de Contagram
- `excepciones.xlsx` → Movimientos que requieren revisión manual

## Estructura del Proyecto

```
├── app.py                          # App Streamlit (interfaz web)
├── src/
│   ├── motor_conciliacion.py       # Orquestador principal
│   ├── normalizador.py             # Normalización multi-banco
│   ├── clasificador.py             # Clasificación de movimientos
│   └── matcher.py                  # Motor de matching inteligente
├── data/
│   ├── test/                       # Extractos bancarios de prueba
│   ├── contagram/                  # Datos de Contagram (ventas/compras)
│   └── config/                     # Tabla paramétrica
├── docs/
│   ├── INFORME_EJECUTIVO.md        # Informe para dirección
│   └── PRESENTACION_EJECUTIVA.md   # Presentación para reunión
├── output/                         # Archivos generados
├── generar_datos_test.py           # Generador de datos de prueba
├── test_conciliacion.py            # Tests end-to-end
└── requirements.txt                # Dependencias Python
```

## Instalación y Uso

```bash
# Instalar dependencias
pip install -r requirements.txt

# Generar datos de prueba (basados en ventas reales de dic 2025)
python generar_datos_test.py

# Ejecutar tests
python test_conciliacion.py

# Iniciar la app
streamlit run app.py
```

## Resultados de la Prueba (Diciembre 2025)

| Métrica | Valor |
|---------|-------|
| Movimientos procesados | 676 |
| Conciliación automática | 96.2% |
| Excepciones | 25 (3.8%) |
| Clientes activos | 250 |
| Facturación procesada | $576.474.570 |

## Bancos Soportados

- **Banco Galicia**: CSV con Fecha, Descripción, Débito, Crédito, Saldo
- **Banco Santander**: CSV con Fecha Operación, Concepto, Importe, Saldo
- **Mercado Pago**: CSV con Monto Bruto, Comisión MP, IVA, Monto Neto

## Documentación

- [Informe Ejecutivo](docs/INFORME_EJECUTIVO.md)
- [Presentación Ejecutiva](docs/PRESENTACION_EJECUTIVA.md)
