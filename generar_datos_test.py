"""
Generador de datos de prueba para el MVP de Conciliación Bancaria Dilcor.
Genera extractos bancarios simulados de Galicia, Santander y Mercado Pago
basados en los datos reales de ventas de diciembre 2025.

Simula 3 tipos de escenario para testing:
  - ~82% match exacto (alias correcto + monto exacto)
  - ~8% probable - duda de ID (nombre mal escrito / alias diferente)
  - ~5% probable - diferencia de cambio (alias ok, monto con centavos dif)
  - ~5% no match (sin referencia clara)
"""
import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

random.seed(42)
np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# --- Leer datos reales de ventas ---
df_ventas = pd.read_excel(os.path.join(BASE_DIR, "Ventas dilcor por cliente dic 2025.xlsx"))
df_ventas.columns = ["cliente", "monto_total"]
df_ventas = df_ventas.iloc[1:-1].copy()
df_ventas["monto_total"] = (
    df_ventas["monto_total"]
    .astype(str)
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
    .astype(float)
)
df_ventas = df_ventas[df_ventas["monto_total"] > 0].reset_index(drop=True)

# --- Helpers ---
def random_date_dec():
    day = random.randint(1, 30)
    return datetime(2025, 12, day)

def gen_cbu():
    return "".join([str(random.randint(0, 9)) for _ in range(22)])

def gen_cuit():
    tipo = random.choice(["20", "23", "27", "30", "33"])
    num = "".join([str(random.randint(0, 9)) for _ in range(8)])
    dig = str(random.randint(0, 9))
    return f"{tipo}-{num}-{dig}"

def mutate_name(nombre):
    """Genera variación realista de un nombre (typos, abreviaciones, etc.)."""
    mutations = [
        lambda s: s.replace(" ", ""),               # Sin espacios
        lambda s: s[:len(s)//2],                     # Truncado
        lambda s: s.replace("S.A", "SA").replace("S.R.L", "SRL"),
        lambda s: s[0] + s[1:].lower(),             # Solo 1ra mayúscula
        lambda s: s.replace("E", "3").replace("A", "4") if len(s) > 5 else s,
        lambda s: s + " CORDOBA",                    # Sufijo ciudad
        lambda s: "SR " + s[:15],                    # Prefijo formal
        lambda s: s.replace(" ", "."),               # Puntos por espacios
    ]
    return random.choice(mutations)(nombre.upper().strip())

# --- Asignar banco principal a cada cliente ---
clientes = df_ventas.to_dict("records")

banco_assignment = {}
for i, c in enumerate(clientes):
    if i < 5:
        banco_assignment[c["cliente"]] = "mercadopago"
    elif i < 15:
        banco_assignment[c["cliente"]] = random.choice(["galicia", "santander"])
    else:
        banco_assignment[c["cliente"]] = random.choices(
            ["mercadopago", "galicia", "santander"],
            weights=[0.40, 0.35, 0.25]
        )[0]

# --- Generar alias bancarios realistas ---
def gen_alias_banco(cliente, banco):
    nombre = cliente.upper().strip()
    if banco == "mercadopago":
        prefijos = ["MERPAG*", "MP*", "MERCPAGO*", "MERPAGO "]
        return random.choice(prefijos) + nombre[:20]
    elif banco == "galicia":
        prefijos = ["TRANSF ", "TRF CR ", "ACRED.TRANSF ", "CR.TRANSF "]
        return random.choice(prefijos) + nombre[:25]
    else:
        prefijos = ["TRANSF.RECIB ", "TRANSF CR ", "ACRED TRANSF ", "CR TRANSF "]
        return random.choice(prefijos) + nombre[:25]

# --- Generar CUITs y IDs Contagram ---
tabla_parametrica = []
for i, c in enumerate(clientes):
    cuit = gen_cuit()
    id_contagram = 1000 + i
    banco = banco_assignment[c["cliente"]]
    alias = gen_alias_banco(c["cliente"], banco)
    tabla_parametrica.append({
        "tipo": "Cliente",
        "nombre_contagram": c["cliente"],
        "alias_banco": alias,
        "cuit": cuit,
        "id_contagram": id_contagram,
        "banco_principal": banco,
        "monto_mensual": c["monto_total"]
    })

# Agregar proveedores ficticios
proveedores = [
    {"nombre": "COCA COLA ANDINA", "cuit": "30-50001234-5", "id": 5001, "monto_aprox": 45000000},
    {"nombre": "CERVECERIA QUILMES", "cuit": "30-50005678-9", "id": 5002, "monto_aprox": 38000000},
    {"nombre": "FERNET BRANCA", "cuit": "30-50009012-3", "id": 5003, "monto_aprox": 22000000},
    {"nombre": "CAMPARI ARGENTINA", "cuit": "30-50003456-7", "id": 5004, "monto_aprox": 18000000},
    {"nombre": "BODEGA NORTON", "cuit": "30-50007890-1", "id": 5005, "monto_aprox": 15000000},
    {"nombre": "CCU ARGENTINA", "cuit": "30-50002345-6", "id": 5006, "monto_aprox": 12000000},
    {"nombre": "PERNOD RICARD", "cuit": "30-50006789-0", "id": 5007, "monto_aprox": 9500000},
    {"nombre": "DIAGEO ARGENTINA", "cuit": "30-50004567-8", "id": 5008, "monto_aprox": 8000000},
    {"nombre": "EPEC (ELECTRICIDAD)", "cuit": "30-99001234-5", "id": 5050, "monto_aprox": 850000},
    {"nombre": "ECOGAS", "cuit": "30-99005678-9", "id": 5051, "monto_aprox": 420000},
    {"nombre": "CLARO TELECOM", "cuit": "30-99009012-3", "id": 5052, "monto_aprox": 380000},
    {"nombre": "SEGUROS SANCOR", "cuit": "30-99003456-7", "id": 5053, "monto_aprox": 1200000},
]

for p in proveedores:
    tabla_parametrica.append({
        "tipo": "Proveedor",
        "nombre_contagram": p["nombre"],
        "alias_banco": p["nombre"][:20].upper(),
        "cuit": p["cuit"],
        "id_contagram": p["id"],
        "banco_principal": random.choice(["galicia", "santander"]),
        "monto_mensual": p["monto_aprox"]
    })

# Guardar tabla parametrica
df_param = pd.DataFrame(tabla_parametrica)
df_param.to_csv(os.path.join(DATA_DIR, "config", "tabla_parametrica.csv"), index=False)

# --- Generar transacciones bancarias ---
def split_into_payments(monto_total, cliente_nombre):
    payments = []
    remaining = monto_total
    day = 1
    while remaining > 10000:
        if remaining > 5000000:
            pago = random.uniform(remaining * 0.1, remaining * 0.4)
        elif remaining > 500000:
            pago = random.uniform(remaining * 0.2, remaining * 0.6)
        else:
            pago = remaining
        pago = round(pago, 2)
        if pago > remaining:
            pago = remaining
        fecha = datetime(2025, 12, min(random.randint(day, min(day + 7, 30)), 30))
        payments.append({"fecha": fecha, "monto": pago})
        remaining -= pago
        day = min(fecha.day + 1, 28)
        if len(payments) >= 8:
            if remaining > 0:
                payments.append({"fecha": datetime(2025, 12, min(day + 2, 30)), "monto": round(remaining, 2)})
            break
    if remaining > 10000 and len(payments) < 8:
        payments.append({"fecha": datetime(2025, 12, random.randint(20, 30)), "monto": round(remaining, 2)})
    return payments

# Crear extractos por banco
extractos = {"galicia": [], "santander": [], "mercadopago": []}

# ─── COBRANZAS con distribución de escenarios ───
#  82% exacto, 8% duda_id (fuzzy name), 5% dif_cambio (monto diff), 5% no match
for item in tabla_parametrica:
    if item["tipo"] != "Cliente":
        continue
    banco = item["banco_principal"]
    payments = split_into_payments(item["monto_mensual"], item["nombre_contagram"])

    for pay in payments:
        match_type = random.choices(
            ["exacto", "duda_id", "dif_cambio", "sin_ref"],
            weights=[0.82, 0.08, 0.05, 0.05]
        )[0]

        descripcion = item["alias_banco"]
        monto = pay["monto"]

        if match_type == "duda_id":
            # Nombre mutado/mal escrito en el extracto bancario
            nombre_mutado = mutate_name(item["nombre_contagram"])
            if banco == "mercadopago":
                descripcion = f"MERPAG*{nombre_mutado[:20]}"
            elif banco == "galicia":
                descripcion = f"TRANSF {nombre_mutado[:25]}"
            else:
                descripcion = f"TRANSF CR {nombre_mutado[:25]}"

        elif match_type == "dif_cambio":
            # Monto con pequeña diferencia (redondeo, comisión, retención)
            variacion = random.choice([
                round(random.uniform(-0.99, -0.01), 2),     # Centavos menos
                round(random.uniform(0.01, 0.99), 2),       # Centavos más
                round(random.uniform(-200, -10), 2),         # Retención chica
                round(random.uniform(10, 150), 2),           # Redondeo a favor
            ])
            monto = round(monto + variacion, 2)
            descripcion = descripcion + " -RET" if variacion < 0 else descripcion

        elif match_type == "sin_ref":
            # Sin referencia identificable
            if banco == "mercadopago":
                descripcion = f"LIQUIDACION MP {random.randint(100000, 999999)}"
            else:
                descripcion = f"TRANSF TERCEROS CBU {gen_cbu()[:10]}"

        extractos[banco].append({
            "fecha": pay["fecha"],
            "tipo": "CREDITO",
            "descripcion": descripcion,
            "monto": monto,
            "referencia": f"REF{random.randint(100000, 999999)}",
            "match_type_test": match_type,
            "cliente_origen": item["nombre_contagram"]
        })

# --- PAGOS a proveedores ---
for item in tabla_parametrica:
    if item["tipo"] != "Proveedor":
        continue
    banco = random.choice(["galicia", "santander"])
    monto_total = item["monto_mensual"]
    n_pagos = random.randint(1, 4)
    montos = []
    remaining = monto_total
    for _ in range(n_pagos - 1):
        m = round(random.uniform(remaining * 0.2, remaining * 0.5), 2)
        montos.append(m)
        remaining -= m
    montos.append(round(remaining, 2))

    for m in montos:
        fecha = datetime(2025, 12, random.randint(1, 30))
        extractos[banco].append({
            "fecha": fecha,
            "tipo": "DEBITO",
            "descripcion": f"PAG {item['nombre_contagram'][:25].upper()}",
            "monto": m,
            "referencia": f"PAG{random.randint(100000, 999999)}",
            "match_type_test": "exacto",
            "cliente_origen": item["nombre_contagram"]
        })

# --- Comisiones bancarias ---
for banco in extractos:
    for _ in range(random.randint(3, 8)):
        fecha = datetime(2025, 12, random.randint(1, 30))
        tipo_gasto = random.choice([
            "COMISION MANTENIMIENTO CTA",
            "IMP DEBITOS Y CREDITOS",
            "COMISION TRANSFERENCIA",
            "SELLADO PROVINCIAL",
            "IVA COMISIONES",
            "COMISION MP" if banco == "mercadopago" else "COMISION BANCARIA",
        ])
        extractos[banco].append({
            "fecha": fecha,
            "tipo": "DEBITO",
            "descripcion": tipo_gasto,
            "monto": round(random.uniform(5000, 150000), 2),
            "referencia": f"COM{random.randint(100000, 999999)}",
            "match_type_test": "gasto_bancario",
            "cliente_origen": "BANCO"
        })

# --- Formatear y guardar extractos ---

# GALICIA
rows_galicia = []
saldo = 15000000.0
for tx in sorted(extractos["galicia"], key=lambda x: x["fecha"]):
    if tx["tipo"] == "CREDITO":
        debito = 0
        credito = tx["monto"]
        saldo += credito
    else:
        debito = tx["monto"]
        credito = 0
        saldo -= debito
    rows_galicia.append({
        "Fecha": tx["fecha"].strftime("%d/%m/%Y"),
        "Fecha Valor": tx["fecha"].strftime("%d/%m/%Y"),
        "Descripcion": tx["descripcion"],
        "Referencia": tx["referencia"],
        "Debito": round(debito, 2) if debito > 0 else "",
        "Credito": round(credito, 2) if credito > 0 else "",
        "Saldo": round(saldo, 2)
    })

df_galicia = pd.DataFrame(rows_galicia)
df_galicia.to_csv(os.path.join(DATA_DIR, "test", "extracto_galicia_dic2025.csv"), index=False, encoding="utf-8-sig")

# SANTANDER
rows_santander = []
saldo = 12000000.0
for tx in sorted(extractos["santander"], key=lambda x: x["fecha"]):
    if tx["tipo"] == "CREDITO":
        importe = tx["monto"]
        saldo += importe
    else:
        importe = -tx["monto"]
        saldo += importe
    rows_santander.append({
        "Fecha Operacion": tx["fecha"].strftime("%d/%m/%Y"),
        "Fecha Valor": tx["fecha"].strftime("%d/%m/%Y"),
        "Concepto": tx["descripcion"],
        "Nro Comprobante": tx["referencia"],
        "Importe": round(importe, 2),
        "Saldo": round(saldo, 2)
    })

df_santander = pd.DataFrame(rows_santander)
df_santander.to_csv(os.path.join(DATA_DIR, "test", "extracto_santander_dic2025.csv"), index=False, encoding="utf-8-sig")

# MERCADO PAGO
rows_mp = []
for tx in sorted(extractos["mercadopago"], key=lambda x: x["fecha"]):
    monto = tx["monto"]
    if tx["tipo"] == "CREDITO":
        comision = round(monto * 0.045, 2)
        neto = round(monto - comision, 2)
    else:
        comision = 0
        neto = -monto
    rows_mp.append({
        "Fecha": tx["fecha"].strftime("%d/%m/%Y"),
        "Tipo Operacion": "Cobro" if tx["tipo"] == "CREDITO" else "Pago",
        "Detalle": tx["descripcion"],
        "Nro Operacion": tx["referencia"],
        "Monto Bruto": round(monto, 2),
        "Comision MP": round(comision, 2),
        "IVA Comision": round(comision * 0.21, 2),
        "Monto Neto": round(neto - (comision * 0.21) if tx["tipo"] == "CREDITO" else neto, 2),
    })

df_mp = pd.DataFrame(rows_mp)
df_mp.to_csv(os.path.join(DATA_DIR, "test", "extracto_mercadopago_dic2025.csv"), index=False, encoding="utf-8-sig")

# --- Generar ventas pendientes Contagram ---
ventas_contagram = []
factura_num = 1
for item in tabla_parametrica:
    if item["tipo"] != "Cliente":
        continue
    monto = item["monto_mensual"]
    n_facturas = max(1, int(monto / 5000000) + random.randint(0, 2))
    remaining = monto
    for j in range(n_facturas):
        if j < n_facturas - 1:
            m = round(random.uniform(remaining * 0.2, remaining * 0.5), 2)
        else:
            m = round(remaining, 2)
        remaining -= m
        fecha = datetime(2025, 12, random.randint(1, 28))
        ventas_contagram.append({
            "Nro Factura": f"A-{factura_num:05d}",
            "Fecha": fecha.strftime("%d/%m/%Y"),
            "Cliente": item["nombre_contagram"],
            "ID Cliente": item["id_contagram"],
            "CUIT": item["cuit"],
            "Monto Total": round(m, 2),
            "IVA": round(m * 0.21 / 1.21, 2),
            "Neto": round(m / 1.21, 2),
            "Estado": "Pendiente",
            "Condicion Venta": random.choice(["Contado", "Cta Cte 15 dias", "Cta Cte 30 dias"]),
        })
        factura_num += 1
        if remaining <= 0:
            break

df_ventas_contagram = pd.DataFrame(ventas_contagram)
df_ventas_contagram.to_csv(os.path.join(DATA_DIR, "contagram", "ventas_pendientes_dic2025.csv"), index=False, encoding="utf-8-sig")

# --- Generar compras pendientes Contagram ---
compras_contagram = []
oc_num = 1
for item in tabla_parametrica:
    if item["tipo"] != "Proveedor":
        continue
    monto = item["monto_mensual"]
    n_oc = random.randint(1, 4)
    remaining = monto
    for j in range(n_oc):
        if j < n_oc - 1:
            m = round(random.uniform(remaining * 0.3, remaining * 0.5), 2)
        else:
            m = round(remaining, 2)
        remaining -= m
        fecha = datetime(2025, 12, random.randint(1, 25))
        compras_contagram.append({
            "Nro OC": f"OC-{oc_num:04d}",
            "Fecha": fecha.strftime("%d/%m/%Y"),
            "Proveedor": item["nombre_contagram"],
            "ID Proveedor": item["id_contagram"],
            "CUIT": item["cuit"],
            "Monto Total": round(m, 2),
            "IVA": round(m * 0.21 / 1.21, 2),
            "Neto": round(m / 1.21, 2),
            "Estado": "Pendiente",
        })
        oc_num += 1
        if remaining <= 0:
            break

df_compras_contagram = pd.DataFrame(compras_contagram)
df_compras_contagram.to_csv(os.path.join(DATA_DIR, "contagram", "compras_pendientes_dic2025.csv"), index=False, encoding="utf-8-sig")

# --- Resumen ---
# Contar tipos de test generados
type_counts = {}
for banco_txs in extractos.values():
    for tx in banco_txs:
        t = tx["match_type_test"]
        type_counts[t] = type_counts.get(t, 0) + 1

total_txs = sum(type_counts.values())
print("=" * 60)
print("DATOS DE TEST GENERADOS EXITOSAMENTE")
print("=" * 60)
print(f"\nExtracto Galicia:     {len(df_galicia)} movimientos")
print(f"Extracto Santander:   {len(df_santander)} movimientos")
print(f"Extracto Mercado Pago:{len(df_mp)} movimientos")
print(f"Ventas Contagram:     {len(df_ventas_contagram)} facturas pendientes")
print(f"Compras Contagram:    {len(df_compras_contagram)} OC pendientes")
print(f"Tabla Parametrica:    {len(df_param)} registros")

print(f"\nDistribucion de escenarios de test:")
for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
    pct = c / total_txs * 100
    print(f"  {t:20s}: {c:4d} ({pct:.1f}%)")

total_creditos = sum(tx["monto"] for banco in extractos.values() for tx in banco if tx["tipo"] == "CREDITO")
total_debitos = sum(tx["monto"] for banco in extractos.values() for tx in banco if tx["tipo"] == "DEBITO")
print(f"\nTotal creditos bancarios: ${total_creditos:,.2f}")
print(f"Total debitos bancarios:  ${total_debitos:,.2f}")
print(f"Total ventas Contagram:   ${df_ventas_contagram['Monto Total'].sum():,.2f}")
