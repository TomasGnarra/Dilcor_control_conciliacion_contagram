"""
Asistente de conciliacion bancaria basado en Gemini Flash.
Usa API REST directa (sin SDK pesado) para maxima compatibilidad.

Requiere GOOGLE_API_KEY en secrets o variable de entorno.
"""
import json
import urllib.request
import urllib.error
import time
import random

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

GLOSARIO = """
## Glosario de terminos

- **Match Exacto**: El movimiento bancario coincide con una factura/OC en identidad (alias bancario vs cliente/proveedor)
  Y en monto (dentro del 0.5% de tolerancia). Es la conciliacion perfecta.
- **Match directo (1:1)**: Una transferencia matchea con una unica factura.
- **Match por suma**: Una transferencia matchea con la SUMA de varias facturas del mismo cliente. Ej: cliente paga $150.000
  y tiene facturas de $80.000 + $70.000.
- **Duda de ID (Probable A)**: El monto coincide con alguna factura, pero el nombre/alias bancario no matchea
  con seguridad. Requiere verificacion manual del cliente/proveedor.
- **Dif. de Cambio (Probable B)**: Sabemos de QUIEN es el movimiento (el alias matchea), pero el monto no coincide
  con ninguna factura individual ni con combinaciones de facturas. Falta asignar las facturas correctas en Contagram.
- **Sin Identificar (No Match)**: No se encontro coincidencia ni por identidad ni por monto. Requiere revision manual completa.
- **Revenue Gap**: Diferencia entre lo cobrado en bancos y lo facturado en Contagram. Idealmente cercano a $0.
- **Payment Gap**: Idem pero para pagos a proveedores (pagado vs OCs registradas).
- **Cobrado de mas**: Suma de las diferencias positivas donde el banco recibio mas que lo facturado.
- **Cobrado de menos**: Suma de las diferencias negativas donde el banco recibio menos que lo facturado.
- **Gastos bancarios**: Comisiones, impuestos, mantenimiento de cuenta. Son informativos, no van a Contagram.
- **Conciliacion total**: Porcentaje de movimientos que NO son "Sin Identificar". Incluye match exacto + probables.
- **Tabla parametrica**: Archivo CSV que mapea alias bancarios a clientes/proveedores de Contagram.

## Acciones recomendadas por estado

- **Match Exacto**: Listo para importar. Descargar CSV y subir a Contagram.
- **Duda de ID**: Verificar manualmente si el alias corresponde al cliente sugerido. Si es correcto, actualizar tabla parametrica.
- **Dif. de Cambio**: Ir a Contagram, buscar las facturas pendientes del cliente y asignar manualmente.
- **Sin Identificar**: Revisar el extracto bancario, identificar el deposito, y agregar el alias a la tabla parametrica para futuros matcheos.
- **Cobrado de mas/menos**: Verificar si es un error de facturacion, una nota de credito pendiente, o un pago parcial.
"""


def _build_system_prompt(stats: dict) -> str:
    """Construye el system prompt inyectando los KPIs de la sesion actual."""
    cb = stats.get("cobros", {})
    pg = stats.get("pagos_prov", {})

    contexto_sesion = f"""
## Datos de la conciliacion actual

### Resumen general
- Total movimientos bancarios: {stats.get('total_movimientos', 'N/A')}
- Tasa conciliacion total: {stats.get('tasa_conciliacion_total', 'N/A')}%
- Match Exacto: {stats.get('match_exacto', 'N/A')} movimientos
- Requieren revision: {stats.get('probable_duda_id', 0) + stats.get('probable_dif_cambio', 0)} movimientos
- Sin identificar: {stats.get('no_match', 'N/A')} movimientos

### Cobros (creditos/ventas)
- Total movimientos: {cb.get('total', 'N/A')}
- Cobrado en bancos: ${cb.get('monto_total', 0):,.0f}
- Match Exacto: {cb.get('match_exacto', 0)} mov (directo: {cb.get('match_directo', 0)}, por suma: {cb.get('match_suma', 0)})
- Duda de ID: {cb.get('probable_duda_id', 0)} mov (${cb.get('probable_duda_id_monto', 0):,.0f})
- Dif. de Cambio: {cb.get('probable_dif_cambio', 0)} mov (${cb.get('probable_dif_cambio_monto', 0):,.0f})
- Sin identificar: {cb.get('no_match', 0)} mov (${cb.get('no_match_monto', 0):,.0f})
- Revenue Gap: ${stats.get('revenue_gap', 0):,.0f}
- Cobrado de mas: ${cb.get('de_mas', 0):,.0f}
- Cobrado de menos: ${cb.get('de_menos', 0):,.0f}

### Pagos a proveedores (debitos)
- Total movimientos: {pg.get('total', 'N/A')}
- Pagado en bancos: ${pg.get('monto_total', 0):,.0f}
- Match Exacto: {pg.get('match_exacto', 0)} mov (directo: {pg.get('match_directo', 0)}, por suma: {pg.get('match_suma', 0)})
- Duda de ID: {pg.get('probable_duda_id', 0)} mov
- Dif. de Cambio: {pg.get('probable_dif_cambio', 0)} mov
- Sin identificar: {pg.get('no_match', 0)} mov (${pg.get('no_match_monto', 0):,.0f})
- Payment Gap: ${stats.get('payment_gap', 0):,.0f}

### Gastos bancarios
- {stats.get('gastos_bancarios', 0)} movimientos por ${stats.get('monto_gastos_bancarios', 0):,.0f}
"""

    return f"""Sos el asistente de conciliacion bancaria de Dilcor, una distribuidora mayorista de bebidas.
Tu rol es explicar los resultados de la conciliacion de forma clara y concisa, y recomendar acciones.

Reglas:
- Responde SOLO sobre conciliacion bancaria, los KPIs del dashboard y las acciones a tomar.
- Usa los datos reales de la sesion actual (abajo) para dar respuestas contextuales.
- Se breve y directo. Usa bullets cuando sea util.
- Usa formato de moneda argentino ($xxx.xxx sin decimales).
- Si te preguntan algo fuera de conciliacion, indica amablemente que solo podes ayudar con ese tema.
- Habla en espanol rioplatense (vos, podes, etc.) pero profesional.

{GLOSARIO}

{contexto_sesion}
"""


def crear_cliente(api_key: str) -> str:
    """Retorna la API key (compatibilidad con la interfaz anterior)."""
    return api_key


def chat_responder(api_key: str, stats: dict, historial: list, pregunta: str) -> str:
    """
    Envia una pregunta al asistente via API REST y devuelve la respuesta.

    Args:
        api_key: Google API key
        stats: Diccionario de estadisticas de la conciliacion actual
        historial: Lista de dicts con {"role": "user"|"model", "parts": [{"text": "..."}]}
        pregunta: Pregunta del usuario

    Returns:
        Texto de la respuesta del asistente
    """
    system_prompt = _build_system_prompt(stats)

    # Limitar historial a los ultimos 5 mensajes para ahorrar tokens y evitar 429
    historial_reciente = historial[-5:] if len(historial) > 5 else historial

    # Construir contenido del chat
    contents = []
    for msg in historial_reciente:
        contents.append({
            "role": msg["role"],
            "parts": [{"text": msg["parts"][0]["text"]}]
        })

    # Agregar pregunta actual
    contents.append({
        "role": "user",
        "parts": [{"text": pregunta}]
    })

    # Payload para la API REST
    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        }
    }

    url = f"{GEMINI_URL}?key={api_key}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    # Retry logic con exponential backoff agresivo
    # 2^0 * 2 = 2s
    # 2^1 * 2 = 4s
    # 2^2 * 2 = 8s
    # 2^3 * 2 = 16s
    # 2^4 * 2 = 32s
    # Total wait: ~62s (suficiente para cubrir los 30s que pide la API)
    max_retries = 5
    base_delay = 2
    
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                break # Exito, salir del loop
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries:
                # Calcular delay con jitter: (base_delay * 2^attempt) + random
                delay = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                time.sleep(delay)
                continue
            
            # Si no es 429 o se acabaron los intentos, propagar error
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API error {e.code}: {body}") from e
    
    # Extraer texto de la respuesta
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, UnboundLocalError):
        # UnboundLocalError si result no se definio (caso raro de fallo silencioso en loop)
        raise RuntimeError(f"Respuesta inesperada de Gemini: {json.dumps(result, indent=2) if 'result' in locals() else 'No data'}")
