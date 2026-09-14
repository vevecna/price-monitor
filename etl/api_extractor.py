import requests, pandas as pd
from .base import Extractor

class CotacaoAPIExtractor(Extractor):
    """cotações de moedas  via AwesomeAPI (publica, sem chave)"""
    URL = 'https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL'
    TIMEOUT = 10

    # Contrato de Dados: é isso que este extrator promete devolver
    schema = ('par','valor','ts')

    def extract(self) -> pd.DataFrame:
        resp = requests.get(self.URL,timeout=self.TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        rows = [{'par': k, 'valor': float(v['bid']),'ts': v['create_date']}for k, v in data.items()]
        return pd.DataFrame(rows)


print()