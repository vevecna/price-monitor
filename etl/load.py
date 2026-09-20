"""Etapa 5 — Carga no PostgreSQL: configurada por ambiente e IDEMPOTENTE."""
from __future__ import annotations

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


DDL_COTACOES = """
CREATE TABLE IF NOT EXISTS cotacoes (
    id     BIGSERIAL PRIMARY KEY,
    par    TEXT          NOT NULL,
    valor  NUMERIC(18,6) NOT NULL,
    ts     TIMESTAMP     NOT NULL,
    -- A chave natural do dado. É ela que torna a carga idempotente.
    CONSTRAINT uq_cotacoes_par_ts UNIQUE (par, ts)
);
"""


UPSERT_COTACOES = """
INSERT INTO cotacoes (par, valor, ts)
VALUES (:par, :valor, :ts)
ON CONFLICT (par, ts) DO NOTHING;
"""



def get_engine() -> Engine:
    """Monta a conexão a partir do ambiente — nunca de credencial no código."""
    faltando = [v for v in ("DB_USER", "DB_PASSWORD", "DB_NAME") if not os.getenv(v)]
    if faltando:
        raise RuntimeError(
            f"variáveis de ambiente ausentes: {faltando} (veja .env.example)"
        )

    url = (
        f"postgresql+psycopg2://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.environ['DB_NAME']}"
    )
    # pool_pre_ping evita erro de conexão morta em pipeline que roda de hora em hora
    return create_engine(url, pool_pre_ping=True)


def carregar(df: pd.DataFrame, tabela: str = "cotacoes") -> int:
    """Insere as cotações ignorando o que já existe. Retorna as linhas enviadas.

    IDEMPOTENTE: rodar duas vezes com o mesmo lote não duplica nada, porque a
    constraint UNIQUE(par, ts) + ON CONFLICT DO NOTHING descartam a repetição.
    Sem isso, o `retries: 2` da DAG duplicaria dados a cada falha parcial.
    """
    if df.empty:
        return 0

    registros = df[["par", "valor", "ts"]].to_dict("records")
    engine = get_engine()
    with engine.begin() as conn:  # begin() = commit no fim, rollback no erro
        conn.execute(text(DDL_COTACOES))
        conn.execute(text(UPSERT_COTACOES), registros)
    return len(registros)
