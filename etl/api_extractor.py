import requests, pandas as pd
from .base import Extractor

class CotacaoAPIExtractor(Extractor):
    URL = 'https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL'

#    schema = ('par','valor','ts')

    def extract(self) -> pd.DataFrame:
        resp = requests.get(self.URL,timeout=10)
        resp.raise_for_status()
        data = resp.json()
        rows = [{'par': k, 'valor': float(v['bid']),'ts': v['create_date']}for k, v in data.items()]
        return pd.DataFrame(rows)


print()