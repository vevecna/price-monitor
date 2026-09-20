"""Etapa 6 — DAG de ETL de cotações: extrair → transformar → carregar.

Padrão importante: o XCom carrega apenas o CAMINHO do arquivo, nunca o
DataFrame. O XCom vive no banco de metadados do Airflow — mandar dado por ali
incha o banco e estoura quando o volume cresce.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator

from etl.api_extractor import CotacaoAPIExtractor
from etl.load import carregar
from etl.transform import transformar_cotacoes


STAGING = Path(os.getenv("STAGING_DIR", "/opt/airflow/staging"))


default_args = {
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}

def _caminho(nome: str, ts_nodash: str) -> Path:
    """Arquivo de staging determinístico por execução.

    Ser determinístico é o que mantém o retry idempotente: a nova tentativa
    sobrescreve o MESMO arquivo, em vez de criar um novo.
    """
    STAGING.mkdir(parents=True, exist_ok=True)
    return STAGING / f"{nome}_{ts_nodash}.parquet"

def _extrair(**ctx):
    # .run() valida o schema declarado e registra a extração no log
    df = CotacaoAPIExtractor().run()
    destino = _caminho("raw", ctx["ts_nodash"])
    df.to_parquet(destino, index=False)
    # No XCom vai só o CAMINHO (poucos bytes), nunca o DataFrame.
    ctx["ti"].xcom_push(key="raw_path", value=str(destino))


def _transformar(**ctx):
    origem = ctx["ti"].xcom_pull(key="raw_path", task_ids="extrair")
    df = transformar_cotacoes(pd.read_parquet(origem))
    destino = _caminho("clean", ctx["ts_nodash"])
    df.to_parquet(destino, index=False)
    ctx["ti"].xcom_push(key="clean_path", value=str(destino))


def _carregar(**ctx):
    origem = ctx["ti"].xcom_pull(key="clean_path", task_ids="transformar")
    linhas = carregar(pd.read_parquet(origem), "cotacoes")
    print(f"[load] {linhas} linhas enviadas (duplicatas ignoradas pelo upsert)")


with DAG(
    dag_id="pipeline_cotacoes",
    description="Coleta cotações via API, valida e carrega no PostgreSQL",
    schedule="@hourly",
    start_date=datetime(2026, 1, 1),
    catchup=False,       # não reprocessa todo o histórico ao ligar a DAG
    max_active_runs=1,   # evita duas execuções disputando a tabela
    default_args=default_args,
    tags=["etl", "cotacoes"],
) as dag:

    extrair = PythonOperator(task_id="extrair", python_callable=_extrair)
    transformar = PythonOperator(task_id="transformar", python_callable=_transformar)
    carga = PythonOperator(task_id="carregar", python_callable=_carregar)

    extrair >> transformar >> carga
