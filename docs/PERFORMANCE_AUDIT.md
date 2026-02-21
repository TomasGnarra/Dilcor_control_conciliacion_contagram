# Auditoría de Performance - Dilcor Conciliación Bancaria

## RIESGOS ACTUALES
1.  **Complejidad Algorítmica Explosiva (O(N*M))**: El matching actual iteraba cada movimiento bancario (N) contra cada registro de la tabla paramétrica (M). Si `tabla_parametrica` crece, el tiempo de ejecución aumentará cuadráticamente.
2.  **Reprocesamiento de Strings**: La normalización de texto (`_normalizar_texto`) se ejecutaba en cada comparación dentro del bucle anidado. Para 1000 movimientos y 500 parámetros, se realizan 500,000 normalizaciones redundantes.
3.  **Falta de Vectorización**: El uso de `iterrows()` en `motor_conciliacion.py` y `matcher.py` impide que pandas utilice optimizaciones vectorizadas en C/Cython.
4.  **Carga de Datos Repetitiva**: `pd.read_csv` y `pd.read_excel` se ejecutan en cada interacción que requiera datos, sin aprovechar el sistema de caching de Streamlit (`@st.cache_data`).
5.  **Combinatoria de Sumas (NP-Hard)**: `_match_monto_suma` utiliza fuerza bruta (`itertools.combinations`) para encontrar facturas que sumen un monto. Aunque tiene límites (max 8 facturas), un cliente con muchas facturas pendientes pequeñas podría disparar el tiempo de procesamiento exponencialmente si los límites se relajan.

## CUELLOS DE BOTELLA POTENCIALES
1.  **Fuzzy Matching en Bucle**: `match_por_tabla_parametrica` realiza comparaciones de texto costosas (Levenshtein/Jaro-Winkler via `rapidfuzz`) dentro de un bucle Python puro. Esto es el principal consumidor de CPU.
2.  **Lectura de Excel**: `pd.read_excel` es significativamente más lento que CSV. Archivos grandes (.xlsx > 5MB) bloquearán la interfaz durante la carga.
3.  **Filtrado No Indexado**: La búsqueda de cliente/factura por ID o Alias no usa índices hash rápidos (diccionarios o búsqueda binaria), sino filtrado lineal (`.loc[]` o `.apply()`).

## MEJORAS PROPUESTAS (Sin romper UX ni Reglas de Negocio)
1.  **Pre-cálculo de Hash/Normalización**:
    -   Agregar columnas `norm_descripcion` al extracto y `norm_alias` a la tabla paramétrica *antes* del bucle de matching.
    -   Realizar la normalización vectorizada: `df['norm'] = df['desc'].apply(_normalizar_texto)`.
2.  **Indexación para Match Exacto**:
    -   Crear un diccionario de busqueda rápida `{alias_normalizado: id_contagram}` para O(1) en matches exactos.
    -   Solo recurrir al bucle fuzzy si el lookup exacto falla.
3.  **Optimización de `rapidfuzz`**:
    -   Utilizar `rapidfuzz.process.extractOne` o `cdist` pasando arrays completos en lugar de comparar uno a uno, aprovechando las optimizaciones de bajo nivel de la librería.
4.  **Early Exit en Sumas**:
    -   Ordenar facturas por monto descendente (ya implementado, mantenerlo).
    -   Agregar filtro previo: Si `sum(facturas) < monto_banco`, descartar inmediatamente sin calcular combinaciones.
5.  **Uso Recomendado de Cache (`st.cache_data`)**:
    -   Decorar `load_demo_data`, `load_manual_data` y las lecturas de Excel/CSV internas.
    -   Cachear la tabla paramétrica pre-procesada en memoria (`st.session_state` o cache) para no re-derivar alias normalizados en cada run.

## REGLAS DE ESCALABILIDAD
1.  **Tamaño de Lotes**: Procesar extractos en chunks si superan las 5,000 filas (actualmente improbable, pero buen límite defensivo).
2.  **Límite de Tabla Paramétrica**: Si supera los 2,000 registros, migrar lookup a estructura de árbol (BK-Tree) o índice invertido (TF-IDF) para candidatos fuzzy.
3.  **Facturas Pendientes**: Si un cliente tiene > 50 facturas pendientes, limitar `_match_monto_suma` a un subconjunto más estricto (ej. solo las 20 más recientes o cercanas al monto) para evitar explosión combinatoria.

## SEÑALES DE ALERTA FUTURA
1.  **Degradación en UI**: Si el tiempo de respuesta al hacer click en "Ejecutar" supera los 5-10 segundos para datasets estándar (500 filas).
2.  **Memory Bloat**: Si el uso de RAM del contenedor/servidor supera 1GB, revisar copias innecesarias de dataframes en `extracto_unificado`.
3.  **Timeouts**: Si la búsqueda de combinaciones de facturas causa que la aplicación se congele, reducir `max_size` en `_match_monto_suma`.

## IMPACTO EN OTROS AGENTES
-   **QA Engineer**: Debe incluir tests de estrés con:
    -   Tabla paramétrica grande (5k filas).
    -   Cliente con 100 facturas pendientes (testear combinatoria).
    -   Strings muy largos o con caracteres unicode extraños (testear normalizador).
-   **UX Research**: Si se implementa cache, la UI debe indicar claramente cuándo los datos están "frescos" vs "cacheados" (ej. "Última actualización: hace 5 min").
