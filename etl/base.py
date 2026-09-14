from __future__ import annotations

from abc import ABC, abstractmethod
import logging

import pandas as pd


logger = logging.getLogger(__name__)

class Extractor(ABC):
    schema: tuple[str, ...] = ()

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        ...

    def run(self) -> pd.DataFrame:
        nome =self.__class__.__name__
        logger.info("Iniciando extração: %s", nome)
        df = self.extract()

        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"{nome}.extract() deve retornar um DataFrame()")

        faltando = set(self.schema) - set(df.columns)
        if faltando:
            raise ValueError(
                f"{nome}: colunas ausentes no retirno {sorted(faltando)}"
                )
        if df.empty:
            logger.warning("%s retornou 0 linhas - verifique a fonte", nome)

            
        logger.info("Extração concluída: %s -> %d linhas", nome, len(df))
        return df