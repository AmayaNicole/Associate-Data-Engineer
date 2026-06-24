# Associate-Data-Engineer
Brenda Nicole Henriquez Amaya


# Pipeline de Prevención de Fraude & Detección de Anomalías de Gasto - Banco MVP

Este repositorio contiene el diseño e implementación de un Producto Mínimo Viable (MVP) para la ingesta, limpieza, transformación y almacenamiento automatizado de transacciones diarias con tarjetas de crédito, optimizado para la detección de anomalías por el equipo de analítica avanzada.

---

## Fase 1: Diseño del Flujo y Toma de Decisiones

### 1. Justificación de Calidad de Datos
Para un equipo de analítica avanzada y modelos de prevención de fraude, la materia prima de sus algoritmos es el histórico de transacciones. Introducir datos crudos sin procesar invalida cualquier análisis posterior ("Garbage In, Garbage Out"). Las reglas de negocio aplicadas mitigan riesgos financieros y operativos críticos:

* **Regla 1 - Eliminación de Duplicados (`id_transaccion`):** Los duplicados artificiales (ocasionados por reintentos en la pasarela de pagos o fallos de red en las terminales) inflan falsamente el volumen total transaccionado y el ticket promedio de los clientes. Eliminar los duplicados evita falsos positivos en las alertas de fraude y asegura que las métricas contables del banco sean exactas.
* **Regla 2 - Tratamiento de Valores Faltantes en Rechazos:** En una pasarela de pagos, una transacción con estado `"rechazada"` que no llegó a procesar fondos suele quedar registrada con un monto nulo (`NaN` o vacío). Dejar este campo vacío interrumpe los cálculos aritméticos automáticos en SQL o Python. Al imputar un valor estandarizado de `0.0`, mantenemos la integridad analítica sin inventar transacciones monetarias ficticias.
* **Regla 3 - Clasificación de Montos Inusuales (`es_monto_inusual`):** Etiquetar transacciones internacionales de alto impacto (> $1,500 USD) mediante una columna booleana precalculada en la ingesta (Capa Silver) reduce la carga computacional en las consultas posteriores. El equipo de fraude no tendrá que recalcular condiciones lógicas en cada reporte diario; el criterio corporativo ya queda unificado desde la base de datos.
* **Regla 4 - Aislamiento de Transacciones Aprobadas:** Para modelar "saltos bruscos" de dinero entre operaciones consecutivas de un mismo usuario, el histórico cronológico debe reflejar transacciones de fondos reales que alteraron la línea de crédito o saldo. Incluir transacciones rechazadas o pendientes corrompería el cálculo analítico de variaciones de gasto reales.

---

### 2. Arquitectura de Datos y Modelo de Almacenamiento (Snowflake Schema)

Para garantizar la escalabilidad de la solución analítica, los datos procesados no se almacenarán en una tabla plana, sino en un modelo relacional en **Snowflake Schema** dentro de Supabase. Esto permite una normalización estricta, eliminando la redundancia y optimizando el rendimiento de las consultas analíticas del equipo de fraude.

#### Mapeo del Modelo de Snowflake Schema:

* **`fact_transacciones` (Tabla de Hechos Central):** Almacena las llaves foráneas de las dimensiones, el atributo cuantitativo `monto_usd` (con la **Regla 2** ya aplicada) y la métrica lógica calculada `es_monto_inusual` (de la **Regla 3**).
* **`dim_clientes`:** Tabla normalizada con los identificadores únicos de los clientes (`id_cliente`).
* **`dim_estados`:** Contiene los estados únicos de las transacciones (`aprobada`, `rechazada`, `pendiente`), garantizando la integridad de los datos para el aislamiento de la **Regla 4**.
* **`dim_comercios`:** Contiene el catálogo de comercios, la cual se normaliza abriéndose en una sub-dimensión llamada **`dim_tipos_comercio`** (`nacional`, `internacional`), cumpliendo la estructura clásica de Snowflake Schema
* **`dim_tiempo`:** Descompone la columna `fecha_hora` en `año`, `mes`, `día` y `hora` para facilitar análisis cronológicos avanzados.

### Librerías a utilizar 
**Pandas:**
En lugar de procesar el archivo fila por fila lo que degradaría el rendimiento en producción, Pandas trabaja en memoria utilizando operaciones vectorizadas. Esto permite que la eliminación de duplicados, la imputación de nulos a 0.0 en transacciones rechazadas y el cálculo del flag es_monto_inusual ocurran de manera casi instantánea y limpia mediante código altamente legible y modular.

**SQLAlchemy:**
 Actúa como el Object-Relational Mapper (ORM) y el motor de conexión entre el script de Python y la base de datos PostgreSQL de Supabase. Permite definir de forma estricta los tipos de datos nativos de la base de datos (TEXT, TIMESTAMP, BOOLEAN, FLOAT) desde el código y asegura cargas atómicas (to_sql con if_exists='replace'), lo que facilita la idempotencia del pipeline en fases tempranas de un MVP.

**Dataframe In-Memory:**
Al ser un flujo de tipo Batch diario de tamaño moderado, no requerimos escribir archivos temporales (como Parquet o Avro) en un almacenamiento local o en S3 antes de cargarlo a la base de datos. Mantener las dimensiones descompuestas en Dataframes en la memoria RAM antes de inyectarlas en Supabase minimiza la latencia de Entrada/Salida (I/O) y simplifica la infraestructura.