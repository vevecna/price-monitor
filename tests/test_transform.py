"""Testes das regras de transformação e do portão de qualidade."""
import pandas as pd
import pytest

from etl.transform import QualidadeError, transformar_cotacoes


def _df(**over):
    base = {"par": ["USD-BRL"], "valor": ["5.1"], "ts": ["2026-08-24 10:00:00"]}
    base.update(over)
    return pd.DataFrame(base)


def test_converte_tipos_corretamente():
    out = transformar_cotacoes(_df())
    assert out.iloc[0]["valor"] == 5.1
    assert pd.api.types.is_datetime64_any_dtype(out["ts"])


def test_descarta_valor_nao_numerico():
    df = pd.DataFrame({
        "par": ["USD-BRL", "EUR-BRL"],
        "valor": ["5.1", "abc"],          # 'abc' vira NaN e deve sair
        "ts": ["2026-08-24 10:00:00"] * 2,
    })
    assert len(transformar_cotacoes(df)) == 1


def test_descarta_timestamp_invalido():
    df = pd.DataFrame({
        "par": ["USD-BRL", "EUR-BRL"],
        "valor": ["5.1", "6.2"],
        "ts": ["2026-08-24 10:00:00", "data-invalida"],
    })
    assert len(transformar_cotacoes(df)) == 1


def test_falha_quando_cotacao_nao_positiva():
    with pytest.raises(QualidadeError, match="cotação"):
        transformar_cotacoes(_df(valor=["-1"]))


def test_falha_quando_nada_sobra():
    with pytest.raises(QualidadeError, match="nenhuma linha"):
        transformar_cotacoes(_df(valor=["abc"]))


def test_remove_duplicatas_do_mesmo_instante():
    df = pd.DataFrame({
        "par": ["USD-BRL", "USD-BRL"],
        "valor": ["5.1", "5.1"],
        "ts": ["2026-08-24 10:00:00"] * 2,
    })
    assert len(transformar_cotacoes(df)) == 1


def test_nao_altera_o_dataframe_de_entrada():
    """A transformação deve ser pura: nada de efeito colateral na entrada."""
    entrada = _df()
    copia = entrada.copy()
    transformar_cotacoes(entrada)
    pd.testing.assert_frame_equal(entrada, copia)
