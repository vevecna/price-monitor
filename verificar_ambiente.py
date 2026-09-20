"""Diagnóstico do ambiente: diz o que já está pronto e o que falta.

Rode isto sempre que montar o projeto numa máquina nova, ou quando algo parar
de funcionar. Ele NÃO conserta nada — ele te diz onde olhar, com o comando.

    python verificar_ambiente.py

Saída em ASCII de propósito: o console do Windows (cp1252) quebra com emoji.
"""
from __future__ import annotations

import importlib
import os
import shutil
import socket
import subprocess
import sys

OK, FALHA, AVISO = "[ OK ]", "[FALHA]", "[AVISO]"

problemas: list[str] = []


def checar(titulo: str, condicao: bool, detalhe: str = "",
           dica: str = "", critico: bool = True) -> None:
    marca = OK if condicao else (FALHA if critico else AVISO)
    print(f"{marca} {titulo}" + (f" - {detalhe}" if detalhe else ""))
    if not condicao:
        if dica:
            print(f"       -> {dica}")
        if critico:
            problemas.append(titulo)


def secao(nome: str) -> None:
    print(f"\n{'=' * 62}\n{nome}\n{'=' * 62}")


def porta_aberta(host: str, porta: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, porta), timeout=timeout):
            return True
    except OSError:
        return False


# ─────────────────────────────────────────────────────────────
secao("1. Python e dependencias")

v = sys.version_info
checar("Python 3.11+", v >= (3, 11), f"{v.major}.{v.minor}.{v.micro}",
       "instale uma versao mais nova em python.org")

PACOTES = {
    "pandas": "transformacao",
    "requests": "extracao via API",
    "bs4": "scraping estatico (beautifulsoup4)",
    "sqlalchemy": "carga no banco",
    "dotenv": "leitura do .env (python-dotenv)",
    "pyarrow": "arquivos parquet no staging",
    "selenium": "scraping dinamico",
    "psycopg2": "driver do Postgres (psycopg2-binary)",
}
for modulo, para_que in PACOTES.items():
    try:
        importlib.import_module(modulo)
        checar(f"pacote {modulo}", True, para_que)
    except ImportError:
        checar(f"pacote {modulo}", False, para_que,
               "pip install -r requirements.txt")

# ─────────────────────────────────────────────────────────────
secao("2. Configuracao (.env)")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

checar("arquivo .env existe", os.path.exists(".env"), "",
       "cp .env.example .env   (e preencha as credenciais)")

obrigatorias = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
faltando = [k for k in obrigatorias if not os.getenv(k)]
checar("variaveis de banco definidas", not faltando,
       "todas presentes" if not faltando else f"faltam: {faltando}",
       "preencha no .env (veja .env.example)")

# ─────────────────────────────────────────────────────────────
secao("3. Docker")

tem_docker = shutil.which("docker") is not None
checar("docker instalado", tem_docker, "", "instale o Docker Desktop", critico=False)

if tem_docker:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=20)
        checar("docker daemon rodando", r.returncode == 0, "",
               "abra o Docker Desktop e aguarde iniciar", critico=False)
    except (subprocess.TimeoutExpired, OSError):
        checar("docker daemon rodando", False, "sem resposta",
               "abra o Docker Desktop", critico=False)

# ─────────────────────────────────────────────────────────────
secao("4. PostgreSQL (destino dos dados)")

host = os.getenv("DB_HOST", "localhost")
porta = int(os.getenv("DB_PORT", "5432"))

alcancavel = porta_aberta(host, porta)
checar(f"porta {host}:{porta} aberta", alcancavel, "",
       "docker compose -f docker-compose.data.yml up -d postgres")

if alcancavel:
    try:
        from sqlalchemy import text

        from etl.load import get_engine
        with get_engine().connect() as conn:
            versao = conn.execute(text("SELECT version()")).scalar() or ""
            checar("conexao autenticada", True, versao.split(",")[0])

            existe = conn.execute(text(
                "SELECT to_regclass('public.cotacoes') IS NOT NULL")).scalar()
            if existe:
                n = conn.execute(text("SELECT count(*) FROM cotacoes")).scalar()
                checar("tabela cotacoes", True, f"{n} linhas")
                # A constraint e o que garante a idempotencia da carga.
                uq = conn.execute(text("""
                    SELECT count(*) FROM pg_constraint
                    WHERE conname = 'uq_cotacoes_par_ts'
                """)).scalar()
                checar("constraint UNIQUE(par, ts)", bool(uq),
                       "e ela que torna a carga idempotente",
                       "recrie a tabela: DROP TABLE cotacoes; e rode run_local.py")
            else:
                checar("tabela cotacoes", False, "ainda nao existe",
                       "e criada sozinha no primeiro `python run_local.py`",
                       critico=False)
    except Exception as exc:
        checar("conexao autenticada", False, f"{type(exc).__name__}: {exc}",
               "confira usuario/senha/banco no .env")

# ─────────────────────────────────────────────────────────────
secao("5. Selenium / Chrome")

remoto = os.getenv("SELENIUM_REMOTE_URL")
if remoto:
    print(f"       modo remoto configurado: {remoto}")
    checar("servico Selenium acessivel", porta_aberta("localhost", 4444), "",
           "docker compose -f docker-compose.data.yml up -d selenium",
           critico=False)
else:
    chrome = any(shutil.which(n) for n in ("chrome", "google-chrome", "chromium")) or \
        any(os.path.exists(p) for p in (
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "/usr/bin/google-chrome",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ))
    checar("Google Chrome instalado", chrome, "",
           "instale em google.com/chrome OU use o container: "
           "SELENIUM_REMOTE_URL=http://localhost:4444/wd/hub",
           critico=False)

# ─────────────────────────────────────────────────────────────
secao("6. Airflow (opcional nesta fase)")

checar("UI em localhost:8080", porta_aberta("localhost", 8080), "",
       "docker compose up -d   (veja o SETUP.md, Parte 3)", critico=False)

# ─────────────────────────────────────────────────────────────
secao("RESUMO")

if problemas:
    print(f"{len(problemas)} item(ns) critico(s) pendente(s):")
    for p in problemas:
        print(f"  - {p}")
    print("\nResolva os criticos e rode este script de novo.")
    sys.exit(1)

print("Ambiente pronto para o pipeline.")
print("Proximos passos:")
print("  pytest -q")
print("  python run_local.py --dry-run")
print("  python run_local.py          (2x: a contagem nao pode mudar)")
