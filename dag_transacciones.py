"""
ACLARACION: El siguiente código representa un diseño conceptual y una simulación de cómo se 
automatizaría este flujo en un servidor real usando Apache Airflow. Debido a que 
en el entorno local de desarrollo se priorizó la estabilidad para ejecutar el 
script principal sin conflictos de librerías, este archivo NO se ejecuta en la 
computadora local, funciona  como una propuesta de arquitectura.

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

default_args = {
    'owner': 'associate_data_engineer',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'dag_transacciones_fraudulentas',
    default_args=default_args,
    description='ETL Automatizado diario para el procesamiento de transacciones bajo modelo Snowflake',
    schedule_interval='30 23 * * *', # Diario a las 11:30 PM
    start_date=datetime(2026, 6, 1),
    catchup=False,
) as dag:

    # Tarea 1: Ejecutar la transformación de Python (scrip.py)
    task_etl_snowflake = BashOperator(
        task_id='ejecutar_transformacion_y_carga',
        bash_command='python scrip.py',
    )

    # Tarea 2: Ejecución de la query analítica (analisis_anomalias.sql) si la carga fue exitosa
    task_analisis_fraude = PostgresOperator(
        task_id='ejecutar_query_anomalias',
        postgres_conn_id='supabase_connection',
        sql='analisis_anomalias.sql',
    )

    # Definición de dependencias
    task_etl_snowflake >> task_analisis_fraude

"""