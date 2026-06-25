from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

# 1. Configuración de argumentos por defecto (Buenas prácticas de producción)
default_args = {
    'owner': 'associate_data_engineer',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# 2. Definición del Contenedor del DAG y su programación (11:30 PM diario)
with DAG(
    'dag_transacciones_fraudulentas',
    default_args=default_args,
    description='ETL Automatizado diario para el procesamiento de transacciones bajo modelo Snowflake',
    schedule_interval='30 23 * * *', # Expresión Cron para las 11:30 PM
    start_date=datetime(2026, 6, 1),
    catchup=False,
) as dag:

    # Tarea 1: Ejecutar la transformación de Python (scrip.py)
    task_etl_snowflake = BashOperator(
    task_id='ejecutar_transformacion_y_carga',
    bash_command='python python_scripts/script.py', 
)
    # Tarea 2: Ejecución de la query analítica (analisis_anomalias.sql)
    task_analisis_fraude = PostgresOperator(
        task_id='ejecutar_query_anomalias',
        postgres_conn_id='supabase_connection',
        sql='analisis_anomalias.sql',
    )

    # 3. Definición de dependencias secuenciales
    task_etl_snowflake >> task_analisis_fraude