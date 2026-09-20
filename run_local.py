"""Roda o pipeline ponta a ponta SEM Airflow — útil para desenvolver e depurar.

Uso:
    python run_local.py --dry-run     # extrai e transforma, não grava no banco
    python run_local.py               # pipeline completo (precisa do Postgres)
    python run_local.py --fonte noticias
"""
from __future__ import annotations

import argparse
import logging
import sys

from etl.api_extractor import CotacaoAPIExtractor
from etl.transform import transformar_cotacoes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run_local")


def rodar_cotacoes(dry_run: bool) -> int:
    # .run() valida o schema declarado e registra a extração no log
    df = CotacaoAPIExtractor().run()
    df = transformar_cotacoes(df)

    print("\n--- dados transformados ---")
    print(df.to_string(index=False))
    print()

    if dry_run:
        log.info("--dry-run: carga no banco foi pulada")
        return 0

    from etl.load import carregar  # import tardio: só aqui precisa do banco

    linhas = carregar(df, "cotacoes")
    log.info("carga concluída: %d linhas enviadas (upsert ignora duplicatas)", linhas)
    return linhas


def rodar_noticias(dry_run: bool) -> int:
    from etl.scraper import NoticiasScraper

    df = NoticiasScraper().run()
    print(df.head(10).to_string(index=False))
    if dry_run:
        log.info("--dry-run: nada foi gravado")
    return len(df)


def rodar_dinamico(dry_run: bool) -> int:
    """Scraping com Selenium — exige Chrome local OU SELENIUM_REMOTE_URL."""
    from etl.selenium_scraper import PrecoDinamicoScraper

    df = PrecoDinamicoScraper().run()
    print(df.head(10).to_string(index=False))
    if dry_run:
        log.info("--dry-run: nada foi gravado")
    return len(df)


FONTES = {
    "cotacoes": rodar_cotacoes,
    "noticias": rodar_noticias,
    "dinamico": rodar_dinamico,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline local (sem Airflow)")
    parser.add_argument("--fonte", choices=list(FONTES), default="cotacoes")
    parser.add_argument("--dry-run", action="store_true",
                        help="não grava no banco (não precisa de Postgres)")
    args = parser.parse_args()

    try:
        FONTES[args.fonte](args.dry_run)
    except Exception as exc:
        log.error("pipeline falhou: %s: %s", type(exc).__name__, exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
