"""Uma trava por lead, compartilhada por todos os canais e pelo Slack.

Com o programa único (decisão 034), uma mensagem de WhatsApp, um e-mail e um clique no Slack podem chegar ao mesmo
tempo para o mesmo lead. A trava garante que só um deles mexe na memória do lead por vez.
"""

import threading

_travas: dict[str, threading.Lock] = {}
_trava_do_dicionario = threading.Lock()


def trava_do_lead(lead_id: str) -> threading.Lock:
    with _trava_do_dicionario:
        return _travas.setdefault(lead_id, threading.Lock())
