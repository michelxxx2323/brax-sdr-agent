"""Liga o atendimento por e-mail: o P.H. confere a caixa da BRAX a cada 30s e responde os e-mails novos.

    .venv\\Scripts\\python.exe atender_email.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from brax_sdr.agente import Agente  # noqa: E402
from brax_sdr.atendente_email import AtendenteEmail  # noqa: E402
from brax_sdr.gmail import conectar  # noqa: E402
from brax_sdr.terminal import aprovador_no_terminal  # noqa: E402

for fluxo in (sys.stdout, sys.stdin):
    try:
        fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

try:
    servico = conectar()
except Exception as erro:
    print(f"Não consegui acessar o Gmail: {erro}")
    print("Se a autorização expirou (dura 7 dias em modo de teste), rode: .venv\\Scripts\\python.exe autorizar_gmail.py")
    sys.exit(1)

# A aprovação de executivo continua no terminal (Slack simulado) até a Fase 5.
try:
    AtendenteEmail(servico, Agente(aprovador=aprovador_no_terminal)).rodar()
except KeyboardInterrupt:
    print("\nAtendimento por e-mail encerrado.")
