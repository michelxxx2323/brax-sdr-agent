r"""Liga o P.H. completo num só programa (decisão 034): WhatsApp (webhook) + e-mail + Slack + HubSpot.

    .venv\Scripts\python.exe iniciar_brax.py

Liga só o que estiver configurado no .env. Ctrl+C para parar.
"""

import os
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import uvicorn  # noqa: E402

from brax_sdr import config  # noqa: E402
from brax_sdr.agente import Agente  # noqa: E402
from brax_sdr.canal_whatsapp import RegistroDeMensagens, criar_envio  # noqa: E402
from brax_sdr.crm import criar_crm  # noqa: E402
from brax_sdr.webhook_whatsapp import criar_app  # noqa: E402

for fluxo in (sys.stdout, sys.stdin):
    try:
        fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

crm = criar_crm()
envio_whatsapp = criar_envio()
print("P.H. da BRAX")
print(f"  HubSpot: {'ligado' if crm else 'desligado (sem HUBSPOT_ACCESS_TOKEN)'}")

# --- E-mail (opcional) ---
gmail = None
if os.getenv("GMAIL_REFRESH_TOKEN"):
    try:
        from brax_sdr.gmail import conectar

        gmail = conectar()
    except Exception as erro:
        print(f"  E-mail: desligado (não consegui acessar o Gmail: {erro}). Autorização expirada? Rode autorizar_gmail.py")
else:
    print("  E-mail: desligado (sem autorização do Gmail)")

# --- Slack (opcional) ---
slack = None
if config.SLACK_BOT_TOKEN and config.SLACK_APP_TOKEN and config.SLACK_CANAL_APROVACAO:
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    from brax_sdr.slack_brax import Entregador, SlackBrax, processar_decisao, registrar_acoes

    app_slack = App(token=config.SLACK_BOT_TOKEN)
    slack = SlackBrax(app_slack.client, crm=crm)
else:
    print("  Slack: desligado (faltam SLACK_BOT_TOKEN, SLACK_APP_TOKEN ou SLACK_CANAL_APROVACAO)")
    print("         As aprovações de executivo vão aparecer AQUI no terminal.")

if slack:
    agente = Agente(aprovador=slack.aprovador, crm=crm, alerta_humano=slack.alerta_humano)
    entregador = Entregador(gmail=gmail, envio_whatsapp=envio_whatsapp)

    def ao_decidir(lead_id: str, decisao: str, observacao: str, usuario: str) -> None:
        try:
            print(f"[Slack] {lead_id}: {decisao} → {processar_decisao(lead_id, decisao, observacao, usuario, agente, entregador, slack)}", flush=True)
        except Exception as erro:
            print(f"[Slack] ERRO ao processar a decisão para {lead_id}: {type(erro).__name__}: {erro}", flush=True)

    registrar_acoes(app_slack, ao_decidir)
    SocketModeHandler(app_slack, config.SLACK_APP_TOKEN).connect()  # conecta em segundo plano
    print(f"  Slack: ligado (canal {config.SLACK_CANAL_APROVACAO})")
else:
    from brax_sdr.terminal import aprovador_no_terminal

    agente = Agente(aprovador=aprovador_no_terminal, crm=crm)

if gmail:
    from brax_sdr.atendente_email import AtendenteEmail

    threading.Thread(target=AtendenteEmail(gmail, agente).rodar, daemon=True, name="email").start()
    print("  E-mail: ligado")

print(f"  WhatsApp: modo {config.WHATSAPP_MODO} em http://127.0.0.1:{config.WHATSAPP_PORTA}/webhook")
if config.WHATSAPP_MODO == "meta" and not config.WHATSAPP_ENVIO_HABILITADO:
    print("            envio DESLIGADO: as respostas só aparecem no terminal")
print()
try:
    uvicorn.run(criar_app(agente, envio_whatsapp, RegistroDeMensagens()), host="127.0.0.1", port=config.WHATSAPP_PORTA, log_level="warning")
except KeyboardInterrupt:
    pass
