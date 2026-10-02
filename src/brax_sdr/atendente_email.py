"""Atendente de e-mail: confere a caixa do Gmail periodicamente e responde cada e-mail novo com o P.H.

Uso (na pasta do projeto):
    .venv\\Scripts\\python.exe atender_email.py
"""

import time
from datetime import datetime

from brax_sdr import config, memoria
from brax_sdr.agente import Agente
from brax_sdr.canal_email import ler_mensagem, montar_resposta, motivo_para_ignorar, texto_para_o_agente


# Na busca do Gmail, "BRAX/processado" vira "brax-processado".
_ETIQUETA_NA_BUSCA = config.GMAIL_ETIQUETA_PROCESSADO.lower().replace("/", "-").replace(" ", "-")


def _log(texto: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {texto}", flush=True)


class AtendenteEmail:
    def __init__(self, servico, agente: Agente):
        self.servico = servico  # cliente da Gmail API (ou um falso, nos testes)
        self.agente = agente
        self._etiqueta_id: str | None = None

    # --- Gmail ---

    def etiqueta_processado(self) -> str:
        """Id da etiqueta "BRAX/processado"; cria a etiqueta na primeira vez."""
        if self._etiqueta_id:
            return self._etiqueta_id
        etiquetas = self.servico.users().labels().list(userId="me").execute().get("labels", [])
        for etiqueta in etiquetas:
            if etiqueta["name"] == config.GMAIL_ETIQUETA_PROCESSADO:
                self._etiqueta_id = etiqueta["id"]
                return self._etiqueta_id
        nova = self.servico.users().labels().create(
            userId="me",
            body={"name": config.GMAIL_ETIQUETA_PROCESSADO, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
        ).execute()
        self._etiqueta_id = nova["id"]
        return self._etiqueta_id

    def _marcar_processado(self, mensagem_id: str) -> None:
        self.servico.users().messages().modify(
            userId="me", id=mensagem_id, body={"addLabelIds": [self.etiqueta_processado()], "removeLabelIds": ["UNREAD"]}
        ).execute()

    def buscar_novos(self) -> list[str]:
        """Ids dos e-mails da caixa de entrada ainda não processados, do mais antigo para o mais novo."""
        resultado = self.servico.users().messages().list(
            userId="me", q=f"in:inbox newer_than:2d -from:me -label:{_ETIQUETA_NA_BUSCA}", maxResults=25
        ).execute()
        return [m["id"] for m in reversed(resultado.get("messages", []))]

    # --- Atendimento ---

    def processar(self, mensagem_id: str) -> str:
        """Processa um e-mail. Devolve o que aconteceu (para o log e para os testes)."""
        bruto = self.servico.users().messages().get(userId="me", id=mensagem_id, format="full").execute()
        if self.etiqueta_processado() in bruto.get("labelIds", []):
            return "já processado"
        email = ler_mensagem(bruto)

        motivo = motivo_para_ignorar(email)
        if motivo:
            self._marcar_processado(mensagem_id)
            return f"ignorado ({motivo})"

        primeiro_contato = not memoria.carregar(email.remetente, canal="email", pasta=self.agente.pasta_leads).mensagens
        resposta = self.agente.responder(email.remetente, texto_para_o_agente(email, primeiro_contato), canal="email")

        # Etiqueta ANTES de enviar: se o envio falhar, o lead fica sem resposta (e o log avisa),
        # mas nunca recebe a mesma resposta duas vezes.
        self._marcar_processado(mensagem_id)
        if not resposta.texto:
            return f"sem resposta ({resposta.motivo_silencio})"
        self.servico.users().messages().send(userId="me", body=montar_resposta(email, resposta.texto)).execute()
        return "respondido"

    def rodar_uma_vez(self) -> None:
        for mensagem_id in self.buscar_novos():
            try:
                resultado = self.processar(mensagem_id)
            except Exception as erro:  # um e-mail com problema não pode derrubar o atendimento dos outros
                _log(f"ERRO no e-mail {mensagem_id}: {type(erro).__name__}: {erro}")
                continue
            if resultado != "já processado":
                _log(f"E-mail {mensagem_id}: {resultado}")

    def rodar(self) -> None:
        _log(f"Atendendo {config.GMAIL_REMETENTE or 'a caixa da BRAX'} a cada {config.EMAIL_INTERVALO_SEGUNDOS}s. Ctrl+C para parar.")
        if config.EMAIL_REMETENTES_PERMITIDOS:
            _log(f"Só respondo a: {', '.join(sorted(config.EMAIL_REMETENTES_PERMITIDOS))}")
        while True:
            self.rodar_uma_vez()
            time.sleep(config.EMAIL_INTERVALO_SEGUNDOS)

