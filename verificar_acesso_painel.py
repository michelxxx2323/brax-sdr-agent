"""Confere, de fora, o que o painel consegue ou não fazer no Supabase (Fase 7, decisão 046).

    .venv\\Scripts\\python.exe verificar_acesso_painel.py

Testa como um visitante com a chave pública (sem login) e como um usuário logado (a conta demo, somente leitura).
Precisa no .env: SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, SUPABASE_DEMO_EMAIL e SUPABASE_DEMO_SENHA.
Não altera nada no banco: as tentativas de gravar usam um id que não existe e devem ser recusadas.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import httpx  # noqa: E402

from brax_sdr import config  # noqa: E402

VISOES = ("painel_leads", "painel_mensagens", "painel_eventos", "painel_evals", "painel_evals_baterias")
TABELAS = ("leads", "evals")  # só o servidor (chave secreta) acessa


def ler(rest: str, cabecalhos: dict, alvo: str) -> tuple[int, int | None]:
    """(código HTTP, quantidade de linhas ou None se recusado)."""
    r = httpx.get(f"{rest}/{alvo}", params={"select": "*"}, headers=cabecalhos, timeout=20)
    return r.status_code, (len(r.json()) if r.status_code == 200 else None)


def gravar(rest: str, cabecalhos: dict) -> int:
    r = httpx.post(f"{rest}/leads", headers={**cabecalhos, "Prefer": "return=minimal"},
                   json={"id": "teste-invasor-nao-existe", "canal": "x", "estado": {}}, timeout=20)
    return r.status_code


def main() -> None:
    publica = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    email, senha = os.getenv("SUPABASE_DEMO_EMAIL", ""), os.getenv("SUPABASE_DEMO_SENHA", "")
    if not (config.SUPABASE_URL and publica and email and senha):
        sys.exit("Faltam no .env: SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, SUPABASE_DEMO_EMAIL ou SUPABASE_DEMO_SENHA.")
    base = config.SUPABASE_URL.rstrip("/")
    rest = f"{base}/rest/v1"
    resultados: list[tuple[str, bool, str]] = []

    def conferir(descricao: str, ok: bool, detalhe: str) -> None:
        resultados.append((descricao, ok, detalhe))

    # 1. Visitante: chave pública, sem login.
    anonimo = {"apikey": publica}
    for alvo in (*VISOES, *TABELAS):
        codigo, linhas = ler(rest, anonimo, alvo)
        conferir(f"visitante não lê {alvo}", not linhas, f"HTTP {codigo}, {linhas if linhas is not None else 'recusado'}")
    codigo = gravar(rest, anonimo)
    conferir("visitante não grava em leads", codigo >= 400, f"HTTP {codigo}")
    r = httpx.post(f"{base}/auth/v1/signup", headers=anonimo,
                   json={"email": "teste-cadastro-bloqueado@example.com", "password": "Senha-de-teste-123!"}, timeout=20)
    conferir("cadastro público desligado", r.status_code == 422 and "signup_disabled" in r.text, f"HTTP {r.status_code}")

    # 2. Usuário logado (conta demo).
    login = httpx.post(f"{base}/auth/v1/token", params={"grant_type": "password"}, headers=anonimo,
                       json={"email": email, "password": senha}, timeout=20)
    if login.status_code != 200:
        conferir("conta demo consegue entrar", False, f"HTTP {login.status_code}: {login.text[:120]}")
    else:
        logado = {"apikey": publica, "Authorization": f"Bearer {login.json()['access_token']}"}
        for alvo in VISOES:
            codigo, linhas = ler(rest, logado, alvo)
            conferir(f"logado lê {alvo}", bool(linhas), f"HTTP {codigo}, {linhas if linhas is not None else 'recusado'}")
        for tabela in TABELAS:
            codigo, linhas = ler(rest, logado, tabela)
            conferir(f"logado NÃO lê a tabela {tabela}", not linhas, f"HTTP {codigo}, {linhas if linhas is not None else 'recusado'}")
        codigo = gravar(rest, logado)
        conferir("logado não grava em leads", codigo >= 400, f"HTTP {codigo}")

    for descricao, ok, detalhe in resultados:
        print(f"{'✅' if ok else '❌'} {descricao:<50} {detalhe}")
    falhas = sum(not ok for _, ok, _ in resultados)
    print(f"\n{len(resultados) - falhas}/{len(resultados)} verificações ok.")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
