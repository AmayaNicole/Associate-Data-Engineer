# Associate-Data-Engineer
Brenda Nicole Henriquez Amaya


# Pipeline de Prevención de Fraude & Detección de Anomalías de Gasto - Banco MVP

Este repositorio contiene el diseño e implementación de un Producto Mínimo Viable (MVP) para la ingesta, limpieza, transformación y almacenamiento automatizado de transacciones diarias con tarjetas de crédito, optimizado para la detección de anomalías por el equipo de analítica avanzada.

---

### 1. Justificación de Calidad de Datos

Para que el equipo de analítica pueda trabajar correctamente y descubrir patrones o fraudes sin errores, los datos deben estar limpios. Aplicar las reglas de limpieza es obligatorio por tres razones:

* **Evitar cálculos inflados (Manejo de Duplicados):** Si dejamos transacciones repetidas con el mismo ID, los reportes finales mostrarán que se gastó más dinero del real o que hubo más ventas de las que verdaderamente sucedieron, arruinando cualquier análisis.
* **Evitar que los programas se traben (Manejo de Nulos):** Las herramientas de análisis matemático no entienden qué hacer cuando ven un espacio vacío o un valor nulo (`NaN`) en la columna de dinero. Al colocarle un `0.0` a las transacciones que fueron rechazadas y venían vacías, nos aseguramos de que las operaciones matemáticas de los demás compañeros funcionen sin dar errores.
* **Facilitar el trabajo futuro (Clasificación de Montos Inusuales):** Dejar marcado desde el principio si una transacción es internacional y mayor a $1500 ayuda a que los analistas no tengan que hacer filtros pesados cada vez que busquen movimientos sospechosos; el dato ya va listo y etiquetado para ellos.

---

### 2. Arquitectura y Flujo de Datos

El camino que siguen los datos está diseñado para ser seguro y ordenado, dividiéndose en tres sencillos pasos:

```text
[Archivo de Origen] ---> (transacciones_diarias.csv)
                                │
                                ▼
┌────────────────────────────────────────────────────────┐
│               1. LIMPIEZA Y ORDEN (Python)             │
│ - Se usa Pandas para abrir y limpiar el archivo.       │
│ - Se aplican las reglas para quitar duplicados y nulos.│
│ - Se separan los datos en el modelo Snowflake.         │
└────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────┐
│               2. EL PUENTE DE CONEXIÓN                 │
│ - Se usan SQLAlchemy y Psycopg2 para crear un canal   │
│   seguro que envíe los datos encriptados por internet. │
└────────────────────────────────────────────────────────┘
                                │
                                ▼
[Base de Datos Final] ---> (Supabase en la nube)
   ├── dim_clientes  (Lista limpia de clientes)
   ├── dim_comercios (Lista de tipos de negocios con un ID)
   └── fact_transacciones (Historial general conectado a las dos listas)

```

#### Herramientas Utilizadas y por qué se eligieron:

* **Pandas (Estructura en memoria):** Es la herramienta principal en Python para leer archivos CSV. Se eligió porque permite hacer la limpieza, borrar los duplicados y rellenar los datos vacíos de forma muy rápida y con pocas líneas de código.
* **SQLAlchemy y Psycopg2 (Conexión y Envío):** Son los encargados de crear el puente de comunicación hacia Supabase. Se eligieron porque se aseguran de que la información viaje protegida por internet y traducen los datos de Python al lenguaje que entiende la base de datos, creando las uniones y llaves necesarias de manera automática.