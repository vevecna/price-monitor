"""Etapa 3 — Scraping dinâmico com Selenium (páginas que dependem de JS).

Funciona nos dois ambientes, sem mudar o código:
  • LOCAL     -> Chrome instalado na máquina (Selenium Manager acha o driver)
  • CONTAINER -> Chrome como serviço, via Remote WebDriver
                 (defina SELENIUM_REMOTE_URL=http://localhost:4444/wd/hub)

Boas práticas demonstradas (todas caem em entrevista):
  • espera EXPLÍCITA (WebDriverWait) em vez de time.sleep()
  • driver.quit() no finally — senão fica processo Chrome órfão
  • flags de container (--no-sandbox, --disable-dev-shm-usage)
"""
from __future__ import annotations

import logging
import os

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .base import Extractor

logger = logging.getLogger(__name__)


def criar_driver() -> webdriver.Remote | webdriver.Chrome:
    """Devolve um driver local ou remoto, conforme o ambiente.

    A imagem do Airflow não tem navegador instalado. Em vez de construir uma
    imagem customizada com Chrome (pesada e lenta), sobe-se um container
    `selenium/standalone-chrome` e conecta-se nele pela rede.
    """

    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")            # sem janela
    opts.add_argument("--no-sandbox")              # necessário em container
    opts.add_argument("--disable-dev-shm-usage")   # evita crash por /dev/shm pequeno
    opts.add_argument("--window-size=1920,1080")

    remoto = os.getenv("SELENIUM_REMOTE_URL")

    if remoto:
        logger.info("Usando Selenium remoto: %s", remoto)
        return webdriver.Remote(command_executor=remoto, options=opts)


class PrecoDinamicoScraper(Extractor):
    # Alvo de treino que REALMENTE renderiza via JS (example.com é HTML puro
    # e não exercita nada do Selenium).
    URL = "https://quotes.toscrape.com/js/"
    SELETOR = ".quote .text"
    ESPERA_S = 20

    schema = ("texto",)

    def extract(self) -> pd.DataFrame:
        driver = criar_driver()
        try:
            driver.get(self.URL)
            # Espera o elemento EXISTIR, em vez de dormir um tempo fixo:
            # segue assim que aparece, com teto de ESPERA_S segundos.
            WebDriverWait(driver, self.ESPERA_S).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, self.SELETOR))
            )
            els = driver.find_elements(By.CSS_SELECTOR, self.SELETOR)
            return pd.DataFrame(
                {"texto": [e.text for e in els]}, columns=list(self.schema)
            )
        finally:
            driver.quit() #sempre no finally: driver orfão vaza processo