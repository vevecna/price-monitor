"""Etapa 4 — Transformações e portão de qualidade."""
from __future__ import annotations

import pandas as pd

class QualidadeError(ValueError):
    """O dado não passou nas regra de qualidade"""

def transformar_cotacoes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")

    #Descarte do que não pode ser convertido
    df = df.dropna(subset=["valor","ts"])

    #Portao de qualidade
    # raise, nao assert: `python -O` remove asserts e a validação sumiria.
    if df.empty:
        raise QualidadeError("nenhuma linha válida após a conversão de tipos")
    if not df["valor"].gt(0).all():
        invalidas = df.loc[df["valor"] <= 0, "par"].tolist()
        raise QualidadeError(f"cotação <= 0 nos pares: {invalidas}")
    if df["par"].isna().any():
        raise QualidadeError("há registro sem o campo 'par'")

    # Remove duplicatas da própria coleta (a API pode repetir o mesmo instante).
    return df.drop_duplicates(subset=["par", "ts"]).reset_index(drop=True)
