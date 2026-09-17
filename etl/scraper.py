"""Etapa 03 - scraper estático com BeatifulSoup.

Regra prática: se o HTML já vem pronto no corpo da resposta, use requests+BS4.
Selenium só quando o conteúdo depende de Javascript (ver selenium_scraper.py)"""

from __future__ import annotations


import pandas as pd
import requests
from bs4 import BeautifulSoup

from .base import Extractor


class NoticiasScraper(Extractor):
    URL = "https://news.ycombinator.com/"
    TIMEOUT = 10

    HEADERS = {"User-Agent": "price-monitor/1.0 (projeto de estudo)"}

    schema = ("titulo", "link")

    def extract(self) -> pd.DataFrame:
        resp = requests.get(self.URL, timeout=self.TIMEOUT, headers=self.HEADERS)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        itens = soup.select(".titleline > a")
        return pd.DataFrame(
            [{"titulo": a.get_text(strip=True), "link": a.get("href")} for a in itens],
            columns=list(self.schema),
        )