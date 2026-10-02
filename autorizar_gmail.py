"""Autoriza o P.H. a usar a caixa do Gmail da BRAX.

Rode uma vez (e de novo se a autorização expirar; em modo de teste do Google, ela dura 7 dias):
    .venv\\Scripts\\python.exe autorizar_gmail.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from brax_sdr import config  # noqa: E402
from brax_sdr.gmail import autorizar  # noqa: E402

for fluxo in (sys.stdout,):
    try:
        fluxo.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

print("Vai abrir uma janela do navegador. Entre com a conta da BRAX (não a sua pessoal) e clique em Permitir.")
print('Se aparecer "O Google não verificou este app", clique em Continuar: o app é seu e está em modo de teste.\n')
email = autorizar()
print(f"\nAutorizado: {email}. O token foi salvo no .env.")
if config.GMAIL_REMETENTE and email.lower() != config.GMAIL_REMETENTE.lower():
    print(f"ATENÇÃO: o .env diz GMAIL_REMETENTE={config.GMAIL_REMETENTE}, mas a conta autorizada foi {email}.")
    print("Se autorizou a conta errada, rode este script de novo e escolha a conta da BRAX.")
