"""
Conector a TiDB Cloud para persistencia de resultados de conciliación.
Usa st.secrets para credenciales (nunca hardcodeadas).
"""
import pandas as pd

try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False


def _get_connection(secrets: dict):
    """Crea conexión a TiDB Cloud usando credenciales de st.secrets."""
    if not PYMYSQL_AVAILABLE:
        raise ImportError(
            "pymysql no está instalado. Ejecute: pip install pymysql"
        )
    return pymysql.connect(
        host=secrets["host"],
        port=int(secrets["port"]),
        user=secrets["user"],
        password=secrets["password"],
        database=secrets["database"],
        ssl={"ca": None},
        ssl_verify_cert=False,
        ssl_verify_identity=False,
    )


def _crear_tabla_si_no_existe(conn):
    """Crea la tabla historico_conciliaciones si no existe."""
    sql = """
    CREATE TABLE IF NOT EXISTS historico_conciliaciones (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        fecha_ejecucion DATETIME NOT NULL,
        fecha_movimiento DATE,
        banco VARCHAR(100),
        tipo VARCHAR(20),
        clasificacion VARCHAR(50),
        descripcion TEXT,
        monto DECIMAL(18, 2),
        match_nivel VARCHAR(50),
        match_detalle TEXT,
        confianza DECIMAL(5, 1),
        nombre_contagram VARCHAR(200),
        id_contagram INT,
        cuit VARCHAR(20),
        factura_match VARCHAR(50),
        monto_factura DECIMAL(18, 2),
        diferencia_monto DECIMAL(18, 2),
        diferencia_pct DECIMAL(8, 2),
        referencia VARCHAR(100),
        INDEX idx_fecha_ejecucion (fecha_ejecucion),
        INDEX idx_match_nivel (match_nivel),
        INDEX idx_banco (banco)
    );
    """
    with conn.cursor() as cursor:
        cursor.execute(sql)
    conn.commit()


def guardar_conciliacion(df: pd.DataFrame, secrets: dict) -> dict:
    """
    Guarda el DataFrame de resultados en TiDB Cloud.
    Hace append a la tabla historico_conciliaciones.

    Args:
        df: DataFrame con resultados de la conciliación
        secrets: dict con credenciales TiDB (de st.secrets["tidb"])

    Returns:
        dict con status y cantidad de registros insertados
    """
    conn = None
    try:
        conn = _get_connection(secrets)
        _crear_tabla_si_no_existe(conn)

        from datetime import datetime
        fecha_ejecucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        columnas_map = {
            "fecha": "fecha_movimiento",
            "banco": "banco",
            "tipo": "tipo",
            "clasificacion": "clasificacion",
            "descripcion": "descripcion",
            "monto": "monto",
            "match_nivel": "match_nivel",
            "match_detalle": "match_detalle",
            "confianza": "confianza",
            "nombre_contagram": "nombre_contagram",
            "id_contagram": "id_contagram",
            "cuit": "cuit",
            "factura_match": "factura_match",
            "monto_factura": "monto_factura",
            "diferencia_monto": "diferencia_monto",
            "diferencia_pct": "diferencia_pct",
            "referencia": "referencia",
        }

        insert_sql = """
        INSERT INTO historico_conciliaciones
        (fecha_ejecucion, fecha_movimiento, banco, tipo, clasificacion,
         descripcion, monto, match_nivel, match_detalle, confianza,
         nombre_contagram, id_contagram, cuit, factura_match,
         monto_factura, diferencia_monto, diferencia_pct, referencia)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        rows_inserted = 0
        with conn.cursor() as cursor:
            for _, row in df.iterrows():
                fecha_mov = None
                if pd.notna(row.get("fecha")):
                    try:
                        fecha_mov = pd.to_datetime(row["fecha"]).strftime("%Y-%m-%d")
                    except Exception:
                        fecha_mov = None

                def safe_val(key, default=None):
                    v = row.get(key, default)
                    if pd.isna(v) if isinstance(v, float) else v is None:
                        return default
                    return v

                values = (
                    fecha_ejecucion,
                    fecha_mov,
                    safe_val("banco", ""),
                    safe_val("tipo", ""),
                    safe_val("clasificacion", ""),
                    str(safe_val("descripcion", ""))[:500],
                    safe_val("monto", 0),
                    safe_val("match_nivel", ""),
                    str(safe_val("match_detalle", ""))[:500],
                    safe_val("confianza", 0),
                    safe_val("nombre_contagram", ""),
                    safe_val("id_contagram"),
                    safe_val("cuit", ""),
                    safe_val("factura_match", ""),
                    safe_val("monto_factura"),
                    safe_val("diferencia_monto"),
                    safe_val("diferencia_pct"),
                    safe_val("referencia", ""),
                )
                cursor.execute(insert_sql, values)
                rows_inserted += 1

        conn.commit()
        return {"status": "ok", "registros_insertados": rows_inserted}

    except ImportError as e:
        return {"status": "error", "mensaje": str(e)}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}
    finally:
        if conn:
            conn.close()


def test_conexion(secrets: dict) -> dict:
    """Testea la conexión a TiDB Cloud."""
    try:
        conn = _get_connection(secrets)
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
        conn.close()
        return {"status": "ok", "mensaje": "Conexion exitosa a TiDB Cloud"}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}
