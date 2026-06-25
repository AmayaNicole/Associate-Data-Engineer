import pandas as pd
import psycopg2

# Cadena de conexión exacta con tus credenciales de Supabase
DATABASE_URL = "postgresql://postgres:basededatos123@db.pzlknfqpntvljoduxegk.supabase.co:5432/postgres?sslmode=require"

def procesar_y_normalizar_snowflake(filepath):
    """
    Lee el archivo CSV, aplica las reglas de calidad y negocio,
    y estructura los datos bajo un modelo relacional Snowflake.
    """
    print(">>> 1. Iniciando lectura del archivo crudo 'transacciones_diarias.csv'...")
    df = pd.read_csv(filepath)
    
    # REGLA DE NEGOCIO 1: Eliminar registros duplicados usando 'id_transaccion'
    print(">>> 2. Aplicando Regla 1: Eliminando duplicados por id_transaccion...")
    df = df.drop_duplicates(subset=['id_transaccion'], keep='first')
    
    # REGLA DE NEGOCIO 2: Si monto_usd es nulo y estado_transaccion es 'rechazada' -> Asignar 0.0
    print(">>> 3. Aplicando Regla 2: Imputando nulos en transacciones rechazadas...")
    condicion_nulo_rechazado = (df['monto_usd'].isna()) & (df['estado_transaccion'] == 'rechazada')
    df.loc[condicion_nulo_rechazado, 'monto_usd'] = 0.0
    
    # REGLA DE NEGOCIO 3: Clasificación de Montos Inusuales (> 1500 USD y tipo_comercio internacional)
    print(">>> 4. Aplicando Regla 3: Clasificando montos inusuales (Monto > 1500 e Internacional)...")
    df['es_monto_inusual'] = (df['monto_usd'] > 1500) & (df['tipo_comercio'] == 'internacional')
    
    print(">>> 5. Normalizando estructura para el esquema Snowflake...")
    # Dimensión 1: Clientes (Valores únicos de id_cliente)
    dim_clientes = df[['id_cliente']].drop_duplicates().reset_index(drop=True)
    
    # Dimensión 2: Comercios (Generamos un ID numérico secuencial)
    dim_comercios = df[['tipo_comercio']].drop_duplicates().reset_index(drop=True)
    dim_comercios['id_comercio'] = dim_comercios.index + 1
    
    # Mapeamos el ID de comercio generado hacia nuestro DataFrame base para la Fact Table
    df_fact = df.merge(dim_comercios, on='tipo_comercio', how='left')
    
    # Tabla de Hechos (Fact Table) seleccionando llaves y métricas calculadas
    fact_transacciones = df_fact[[
        'id_transaccion', 
        'id_cliente', 
        'id_comercio', 
        'fecha_hora', 
        'monto_usd', 
        'estado_transaccion', 
        'es_monto_inusual'
    ]]
    
    return dim_clientes, dim_comercios, fact_transacciones

def cargar_a_supabase_snowflake(dim_cli, dim_com, fact_trans):
    """
    Se conecta a Supabase de forma nativa con psycopg2, limpia y carga datos
    usando conectores puros para evitar conflictos de SQLAlchemy.
    """
    print(">>> 6. Estableciendo conexión segura nativa con Supabase...")
    
    try:
        # Abrimos conexión directa con la base de datos usando el driver nativo de Postgres
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print(">>> 7. Limpiando tablas previas si existen (Evita conflictos)...")
        cursor.execute("DROP TABLE IF EXISTS fact_transacciones CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS dim_clientes CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS dim_comercios CASCADE;")
        
        # Para evitar problemas con to_sql, usamos un truco nativo de pandas rápido
        print(">>> 8. Cargando datos a la dimensión 'dim_clientes'...")
        # Creamos la estructura base
        cursor.execute("CREATE TABLE dim_clientes (id_cliente TEXT);")
        for val in dim_cli['id_cliente']:
            cursor.execute("INSERT INTO dim_clientes (id_cliente) VALUES (%s);", (str(val),))
        cursor.execute("ALTER TABLE dim_clientes ADD PRIMARY KEY (id_cliente);")
        
        print(">>> 9. Cargando datos a la dimensión 'dim_comercios'...")
        cursor.execute("CREATE TABLE dim_comercios (tipo_comercio TEXT, id_comercio INT);")
        for _, row in dim_com.iterrows():
            cursor.execute("INSERT INTO dim_comercios (tipo_comercio, id_comercio) VALUES (%s, %s);", (str(row['tipo_comercio']), int(row['id_comercio'])))
        cursor.execute("ALTER TABLE dim_comercios ADD PRIMARY KEY (id_comercio);")
        
        print(">>> 10. Cargando datos a la tabla de hechos 'fact_transacciones'...")
        cursor.execute("""
            CREATE TABLE fact_transacciones (
                id_transaccion TEXT, id_cliente TEXT, id_comercio INT, 
                fecha_hora TEXT, monto_usd NUMERIC, estado_transaccion TEXT, es_monto_inusual BOOLEAN
            );
        """)
        for _, row in fact_trans.iterrows():
            cursor.execute("""
                INSERT INTO fact_transacciones (id_transaccion, id_cliente, id_comercio, fecha_hora, monto_usd, estado_transaccion, es_monto_inusual)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (str(row['id_transaccion']), str(row['id_cliente']), int(row['id_comercio']), str(row['fecha_hora']), float(row['monto_usd']), str(row['estado_transaccion']), bool(row['es_monto_inusual'])))
        cursor.execute("ALTER TABLE fact_transacciones ADD PRIMARY KEY (id_transaccion);")
        
        print(">>> 11. Creando llaves foráneas (Relaciones del Esquema Snowflake)...")
        cursor.execute("""
            ALTER TABLE fact_transacciones 
            ADD CONSTRAINT fk_cliente FOREIGN KEY (id_cliente) REFERENCES dim_clientes(id_cliente),
            ADD CONSTRAINT fk_comercio FOREIGN KEY (id_comercio) REFERENCES dim_comercios(id_comercio);
        """)
        
        # Confirmamos todos los cambios en la BD y cerramos canales
        conn.commit()
        cursor.close()
        conn.close()
        
        print("¡ÉXITO EN EL PIPELINE! El modelo Snowflake fue estructurado y poblado correctamente en Supabase.")
    except Exception as e:
        print(f"❌ Error crítico durante la carga en la base de datos: {e}")

if __name__ == "__main__":
    # ruta
    archivo_origen = "../datos/transacciones_diarias.csv"
    
    # Ejecución completa del proceso ETL
    dim_cli, dim_com, fact_trans = procesar_y_normalizar_snowflake(archivo_origen)
    cargar_a_supabase_snowflake(dim_cli, dim_com, fact_trans)