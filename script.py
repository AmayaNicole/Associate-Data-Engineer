import pandas as pd
from sqlalchemy import create_engine, text

# Cadena de conexión exacta con tus credenciales de Supabase (con SSL habilitado)
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
    Se conecta a la instancia de Supabase, crea las tablas con sus llaves
    primarias y establece las restricciones de llaves foráneas (Snowflake).
    """
    print(">>> 6. Estableciendo conexión segura con Supabase...")
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.begin() as connection:
            print(">>> 7. Limpiando tablas previas si existen (Evita conflictos)...")
            connection.execute(text("DROP TABLE IF EXISTS fact_transacciones CASCADE;"))
            connection.execute(text("DROP TABLE IF EXISTS dim_clientes CASCADE;"))
            connection.execute(text("DROP TABLE IF EXISTS dim_comercios CASCADE;"))
            
            print(">>> 8. Cargando datos a la dimensión 'dim_clientes'...")
            dim_cli.to_sql('dim_clientes', connection, if_exists='replace', index=False)
            connection.execute(text("ALTER TABLE dim_clientes ADD PRIMARY KEY (id_cliente);"))
            
            print(">>> 9. Cargando datos a la dimensión 'dim_comercios'...")
            dim_com.to_sql('dim_comercios', connection, if_exists='replace', index=False)
            connection.execute(text("ALTER TABLE dim_comercios ADD PRIMARY KEY (id_comercio);"))
            
            print(">>> 10. Cargando datos a la tabla de hechos 'fact_transacciones'...")
            fact_trans.to_sql('fact_transacciones', connection, if_exists='replace', index=False)
            connection.execute(text("ALTER TABLE fact_transacciones ADD PRIMARY KEY (id_transaccion);"))
            
            print(">>> 11. Creando llaves foráneas (Relaciones del Esquema Snowflake)...")
            connection.execute(text("""
                ALTER TABLE fact_transacciones 
                ADD CONSTRAINT fk_cliente FOREIGN KEY (id_cliente) REFERENCES dim_clientes(id_cliente),
                ADD CONSTRAINT fk_comercio FOREIGN KEY (id_comercio) REFERENCES dim_comercios(id_comercio);
            """))
            
        print("¡ÉXITO EN EL PIPELINE! El modelo Snowflake fue estructurado y poblado correctamente.")
    except Exception as e:
        print(f"❌ Error crítico durante la carga en la base de datos: {e}")

if __name__ == "__main__":
    # Ruta del archivo CSV en la raíz de tu proyecto
    archivo_origen = "transacciones_diarias.csv"
    
    # Ejecución completa del proceso ETL
    dim_cli, dim_com, fact_trans = procesar_y_normalizar_snowflake(archivo_origen)
    cargar_a_supabase_snowflake(dim_cli, dim_com, fact_trans)