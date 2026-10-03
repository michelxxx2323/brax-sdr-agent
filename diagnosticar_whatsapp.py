"""Confere as credenciais da WhatsApp Cloud API sem enviar nenhuma mensagem.

    .venv\\Scripts\\python.exe diagnosticar_whatsapp.py

Consulta na Meta o número de teste (só leitura): se o token ou o id do número estiverem errados, mostra o motivo.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import httpx  # noqa: E402

from brax_sdr import config  # noqa: E402

for fluxo in (sys.stdout,):
    try:
        fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

faltando = [nome for nome, valor in (
    ("WHATSAPP_ACCESS_TOKEN", config.WHATSAPP_ACCESS_TOKEN),
    ("WHATSAPP_PHONE_NUMBER_ID", config.WHATSAPP_PHONE_NUMBER_ID),
    ("WHATSAPP_APP_SECRET", config.WHATSAPP_APP_SECRET if config.WHATSAPP_MODO == "meta" else "ok"),
) if not valor]
print(f"Modo: {config.WHATSAPP_MODO} | envio real: {'LIGADO' if config.WHATSAPP_ENVIO_HABILITADO else 'desligado'}")
if faltando:
    print(f"Falta preencher no .env: {', '.join(faltando)}")
    sys.exit(1)

url = f"https://graph.facebook.com/{config.WHATSAPP_API_VERSAO}/{config.WHATSAPP_PHONE_NUMBER_ID}"
resposta = httpx.get(
    url,
    params={"fields": "display_phone_number,verified_name,quality_rating"},
    headers={"Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}"},
    timeout=20,
)
if resposta.status_code == 200:
    dados = resposta.json()
    print(f"Credenciais OK. Número de teste da Meta: {dados.get('display_phone_number')} "
          f"| nome: {dados.get('verified_name')} | qualidade: {dados.get('quality_rating')}")
else:
    erro = resposta.json().get("error", {}) if resposta.headers.get("content-type", "").startswith("application/json") else {}
    print(f"A Meta recusou (HTTP {resposta.status_code}): {erro.get('message', resposta.text[:200])}")
    if erro.get("code") == 190:
        print("O token expirou ou é inválido. Gere outro em WhatsApp → Configuração da API (o temporário dura 24h).")
    sys.exit(1)
