"""Testes do contrato de extração (etl/base.py).

Estes testes usam extratores FALSOS: validam o contrato, sem depender de rede.
Teste que precisa de internet é frágil e não serve para CI.
"""
import logging

import pandas as pd
import pytest

from etl.base import ExtractionError, Extractor


class ExtratorOk(Extractor):
    schema = ("a", "b")

    def extract(self) -> pd.DataFrame:
        return pd.DataFrame({"a": [1], "b": [2]})


class ExtratorSemColuna(Extractor):
    schema = ("a", "b", "c")   # promete 'c'...

    def extract(self) -> pd.DataFrame:
        return pd.DataFrame({"a": [1], "b": [2]})   # ...mas não entrega


class ExtratorTipoErrado(Extractor):
    schema = ("a",)

    def extract(self):
        return {"a": [1]}      # dict, não DataFrame


class ExtratorVazio(Extractor):
    schema = ("a",)

    def extract(self) -> pd.DataFrame:
        return pd.DataFrame({"a": []})


def test_run_devolve_dataframe_quando_contrato_cumprido():
    df = ExtratorOk().run()
    assert list(df.columns) == ["a", "b"]
    assert len(df) == 1


def test_run_falha_quando_falta_coluna_do_schema():
    with pytest.raises(ExtractionError, match="colunas ausentes"):
        ExtratorSemColuna().run()


def test_run_falha_quando_retorno_nao_e_dataframe():
    with pytest.raises(ExtractionError, match="DataFrame"):
        ExtratorTipoErrado().run()


def test_run_avisa_quando_fonte_vem_vazia(caplog):
    """Fonte que seca em silêncio é o incidente mais difícil de achar."""
    with caplog.at_level(logging.WARNING, logger="etl.base"):
        ExtratorVazio().run()
    assert "0 linhas" in caplog.text


def test_extractor_e_abstrato():
    """Não deve ser possível instanciar a classe base."""
    with pytest.raises(TypeError):
        Extractor()
