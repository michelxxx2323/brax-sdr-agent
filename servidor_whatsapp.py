"""Liga o servidor do webhook do WhatsApp (porta 8000). Ctrl+C para parar.

    .venv\\Scripts\\python.exe servidor_whatsapp.py

Modo simulado (padrão): teste com simular_whatsapp.py, sem número de telefone.
Modo meta: WHATSAPP_MODO=meta no .env, com o endereço público (túnel ou hospedagem) cadastrado na Meta.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import uvicorn  # noqa: E402

from brax_sdr import config  # noqa: E402
from brax_sdr.agente import Agente  # noqa: E402
from brax_sdr.canal_whatsapp import RegistroDeMensagens, criar_envio  # noqa: E402
from brax_sdr.terminal import aprovador_no_terminal  # noqa: E402
from brax_sdr.webhook_whatsapp import criar_app  # noqa: E402

for fluxo in (sys.stdout, sys.stdin):
    try:
        fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

if not config.WHATSAPP_APP_SECRET:
    print("Modo meta: preencha WHATSAPP_APP_SECRET no .env (sem ela, não dá para conferir que os avisos vêm da Meta).")
    sys.exit(1)

print(f"Servidor do WhatsApp | modo: {config.WHATSAPP_MODO} | http://127.0.0.1:{config.WHATSAPP_PORTA}/webhook")
if config.WHATSAPP_MODO == "meta":
    print("Envio REAL ligado: as respostas vão para o WhatsApp." if config.WHATSAPP_ENVIO_HABILITADO
          else "Envio DESLIGADO: nenhuma mensagem sai; o terminal mostra o que teria sido enviado.")
print("Aprovações de executivo aparecem AQUI (Slack simulado, até a Fase 5).\n")
# A aprovação de executivo continua no terminal (Slack simulado) até a Fase 5.
app = criar_app(Agente(aprovador=aprovador_no_terminal), criar_envio(), RegistroDeMensagens())
uvicorn.run(app, host="127.0.0.1", port=config.WHATSAPP_PORTA, log_level="warning")
