"""Acesso à Gmail API: autorização e cliente.

Quem mexe na caixa de e-mail é o CÓDIGO, nunca o modelo (decisão 026): o P.H. recebe só o texto
de um e-mail e devolve só o texto da resposta. Assim, um e-mail malicioso não consegue fazer a IA
ler ou enviar outras mensagens.
"""

import os

from dotenv import set_key
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from brax_sdr import config

_TOKEN_URI = "https://oauth2.googleapis.com/token"


def _client_id_e_secret() -> tuple[str, str]:
    client_id, secret = os.getenv("GMAIL_CLIENT_ID", ""), os.getenv("GMAIL_CLIENT_SECRET", "")
    if not client_id or not secret:
        raise RuntimeError("Preencha GMAIL_CLIENT_ID e GMAIL_CLIENT_SECRET no .env (veja o README).")
    return client_id, secret


def autorizar() -> str:
    """Abre o navegador para autorizar a conta e grava o refresh token no .env. Devolve o e-mail autorizado."""
    client_id, secret = _client_id_e_secret()
    fluxo = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": _TOKEN_URI,
                "redirect_uris": ["http://localhost"],
            }
        },
        config.GMAIL_ESCOPOS,
    )
    # access_type=offline + prompt=consent garantem que o Google devolva o refresh token.
    credenciais = fluxo.run_local_server(port=0, access_type="offline", prompt="consent")
    if not credenciais.refresh_token:
        raise RuntimeError("O Google não devolveu o refresh token. Rode a autorização de novo.")
    set_key(str(config.RAIZ / ".env"), "GMAIL_REFRESH_TOKEN", credenciais.refresh_token, quote_mode="never")
    servico = build("gmail", "v1", credentials=credenciais, cache_discovery=False)
    return servico.users().getProfile(userId="me").execute()["emailAddress"]


def conectar():
    """Cria o cliente da Gmail API a partir do refresh token do .env."""
    client_id, secret = _client_id_e_secret()
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN", "")
    if not refresh_token:
        raise RuntimeError("Falta GMAIL_REFRESH_TOKEN no .env. Rode: .venv\\Scripts\\python.exe autorizar_gmail.py")
    credenciais = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=_TOKEN_URI,
        client_id=client_id,
        client_secret=secret,
        scopes=config.GMAIL_ESCOPOS,
    )
    credenciais.refresh(Request())  # falha aqui se a autorização expirou (7 dias em modo de teste)
    return build("gmail", "v1", credentials=credenciais, cache_discovery=False)
