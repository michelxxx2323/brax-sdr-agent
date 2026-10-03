"""Slack: pedido de aprovação de executivo com botões, alertas de "transferir para humano" e o retorno ao lead.

Socket Mode (decisão 034): a conexão sai do computador para o Slack, sem endereço público.
A aprovação é ASSÍNCRONA: o P.H. diz ao lead que vai confirmar, e o retorno sai quando alguém clica no botão.
"""

from brax_sdr import config, memoria
from brax_sdr.crm import criar_nota, sincronizar_com_seguranca
from brax_sdr.memoria import Lead
from brax_sdr.resumo import gerar_resumo
from brax_sdr.travas import trava_do_lead

ACAO_APROVAR = "brax_aprovar"
ACAO_NOVO_HORARIO = "brax_novo_horario"
ACAO_INDICAR_APP = "brax_indicar_app"
JANELA_HORARIO = "brax_janela_horario"
ACAO_DEVOLVER = "brax_devolver"


# --- Mensagens do Slack (Block Kit) ------------------------------------------------------------

def _rotulo_do_lead(lead: Lead) -> str:
    return f"{lead.dados.get('empresa') or 'Empresa não informada'} ({lead.dados.get('nome_contato') or lead.id})"


def blocos_de_aprovacao(lead: Lead, resumo: str, disponibilidade: str) -> list[dict]:
    return [
        {"type": "header", "text": {"type": "plain_text", "text": f"🟢 Lead para executivo: {lead.dados.get('empresa') or lead.id}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": resumo}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": (
            f"*Motivo da faixa:* {lead.motivo_faixa or '-'} · *Prioridade:* {lead.prioridade} · *Canal:* {lead.canal}"
        )}]},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*Disponibilidade do lead:* {disponibilidade or 'não informada'}"}},
        {"type": "actions", "elements": [
            {"type": "button", "action_id": ACAO_APROVAR, "style": "primary", "value": lead.id,
             "text": {"type": "plain_text", "text": "Aprovar"}},
            {"type": "button", "action_id": ACAO_NOVO_HORARIO, "value": lead.id,
             "text": {"type": "plain_text", "text": "Sugerir outro horário"}},
            {"type": "button", "action_id": ACAO_INDICAR_APP, "style": "danger", "value": lead.id,
             "text": {"type": "plain_text", "text": "Indicar o app"}},
        ]},
    ]


def blocos_de_atendimento(lead: Lead, motivo: str) -> list[dict]:
    return [
        {"type": "section", "text": {"type": "mrkdwn", "text": (
            f"🙋 *Atendimento humano necessário*\n*Lead:* {_rotulo_do_lead(lead)} · *Canal:* {lead.canal} · "
            f"*Contato:* {lead.id}\n*Motivo:* {motivo}"
        )}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": (
            "O P.H. está *pausado* para este lead. As mensagens que ele mandar aparecem na thread desta mensagem."
        )}]},
        {"type": "actions", "elements": [
            {"type": "button", "action_id": ACAO_DEVOLVER, "value": lead.id,
             "text": {"type": "plain_text", "text": "Devolver ao P.H."}},
        ]},
    ]


def janela_de_horario(lead_id: str) -> dict:
    return {
        "type": "modal",
        "callback_id": JANELA_HORARIO,
        "private_metadata": lead_id,
        "title": {"type": "plain_text", "text": "Sugerir outro horário"},
        "submit": {"type": "plain_text", "text": "Enviar"},
        "blocks": [{
            "type": "input", "block_id": "horario",
            "label": {"type": "plain_text", "text": "Qual horário sugerir ao lead?"},
            "element": {"type": "plain_text_input", "action_id": "valor",
                        "placeholder": {"type": "plain_text", "text": "ex.: amanhã às 15h"}},
        }],
    }


_SITUACAO = {
    "aprovada": "✅ Aprovado",
    "novo_horario": "🕒 Outro horário sugerido",
    "recusada": "↪️ Indicado o app",
}


# --- Integração ---------------------------------------------------------------------------------

class SlackBrax:
    def __init__(self, cliente, canal: str = config.SLACK_CANAL_APROVACAO, crm=None, resumidor=gerar_resumo):
        self.cliente = cliente  # slack_sdk.WebClient (ou um falso nos testes)
        self.canal = canal
        self.crm = crm
        self.resumidor = resumidor

    def aprovador(self, lead: Lead, resumo_do_ph: str, disponibilidade: str) -> tuple[str, str]:
        """Usado pela ferramenta solicitar_aprovacao_executivo: publica o pedido e devolve "pendente" na hora."""
        resumo = self.resumidor(lead, disponibilidade)
        resposta = self.cliente.chat_postMessage(
            channel=self.canal, text=f"Lead para executivo: {_rotulo_do_lead(lead)}",
            blocks=blocos_de_aprovacao(lead, resumo, disponibilidade),
        )
        lead.slack = {"canal": resposta["channel"], "ts": resposta["ts"], "resumo": resumo, "disponibilidade": disponibilidade}
        if self.crm and lead.crm.get("contato_id"):
            try:
                criar_nota(self.crm, lead, f"Resumo para o executivo (P.H.):\n{resumo}\n\nDisponibilidade: {disponibilidade}")
            except Exception as erro:
                lead.registrar_evento("crm_erro", f"nota: {str(erro)[:150]}")
        return "pendente", ""

    def alerta_humano(self, lead: Lead, motivo: str) -> None:
        """Avisa o time que alguém precisa assumir. O P.H. fica pausado até o botão "Devolver ao P.H." (decisão 036)."""
        resposta = self.cliente.chat_postMessage(
            channel=self.canal,
            text=f"🙋 Atendimento humano necessário: {_rotulo_do_lead(lead)}",
            blocks=blocos_de_atendimento(lead, motivo),
        )
        lead.slack["alerta"] = {"canal": resposta["channel"], "ts": resposta["ts"], "motivo": motivo}

    def mensagem_em_atendimento(self, lead: Lead, texto: str) -> None:
        """Mensagens que o lead manda durante a pausa vão para a thread do alerta, para quem está atendendo."""
        alerta = lead.slack.get("alerta")
        if not alerta:
            return
        self.cliente.chat_postMessage(
            channel=alerta["canal"], thread_ts=alerta["ts"],
            text=f"💬 {lead.primeiro_nome() or lead.id}: {texto}",
        )

    def finalizar(self, lead: Lead, situacao: str, detalhe: str = "") -> None:
        """Troca os botões pelo resultado, para ninguém clicar de novo."""
        if not lead.slack.get("ts"):
            return
        self.cliente.chat_update(
            channel=lead.slack["canal"], ts=lead.slack["ts"], text=f"{situacao}: {_rotulo_do_lead(lead)}",
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*{_rotulo_do_lead(lead)}*\n{lead.slack.get('resumo', '')}"}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": f"{situacao}{f' · {detalhe}' if detalhe else ''}"}]},
            ],
        )


# --- Decisão do time → retorno ao lead ----------------------------------------------------------

def _instrucao(decisao: str, lead: Lead, observacao: str) -> tuple[str, str, str]:
    """(instrução para a IA, link obrigatório, texto padronizado de reserva)."""
    nome = lead.primeiro_nome() or ""
    saudacao = f"{nome}, " if nome else ""
    disponibilidade = lead.slack.get("disponibilidade") or "o horário que você indicou"
    if decisao == "aprovada":
        link = config.LINK_AGENDA_EXECUTIVO
        return (
            f"O time aprovou a conversa com um executivo. Avise o lead com cordialidade e envie o link de agenda "
            f"{link} (exatamente este link), lembrando a disponibilidade que ele deu ({disponibilidade}). "
            "Não diga o formato da reunião (ligação, vídeo ou presencial): isso é definido na agenda.",
            link,
            f"Boa notícia{', ' + nome if nome else ''}! O time confirmou. Escolha o melhor horário por aqui: {link}",
        )
    if decisao == "novo_horario":
        link = config.LINK_AGENDA_EXECUTIVO
        return (
            f"O time não consegue no horário que o lead pediu e sugeriu: {observacao}. Ofereça esse horário com "
            f"cordialidade e envie o link de agenda {link} (exatamente este link) para o lead confirmar.",
            link,
            f"{saudacao}no horário que você pediu o time não consegue, mas {observacao} está livre. "
            f"Se funcionar, confirme por aqui: {link}",
        )
    link = config.LINK_APP
    empresa = lead.dados.get("empresa") or "a sua empresa"
    return (
        f"O time avaliou que o caminho mais rápido para o lead é abrir a conta direto pelo app, sem reunião. "
        f"Explique isso com cordialidade (sem dizer que foi recusado), envie o link {link} (exatamente este link) e "
        "lembre que cadastro e documentos são feitos só no app.",
        link,
        f"{saudacao}conversando com o time, o caminho mais rápido para {empresa} é abrir a conta direto pelo app: "
        f"{link}. Cadastro e documentos são feitos só por lá.",
    )


class Entregador:
    """Entrega uma mensagem proativa ao lead pelo canal da conversa (thread do e-mail ou WhatsApp)."""

    def __init__(self, gmail=None, envio_whatsapp=None):
        self.gmail = gmail
        self.envio_whatsapp = envio_whatsapp

    def entregar(self, lead: Lead, texto: str) -> str:
        if lead.canal == "email" and self.gmail and lead.email_contexto:
            from brax_sdr.canal_email import email_da_thread, montar_resposta

            self.gmail.users().messages().send(userId="me", body=montar_resposta(email_da_thread(lead.email_contexto), texto)).execute()
            return "e-mail"
        if lead.canal == "whatsapp" and self.envio_whatsapp:
            self.envio_whatsapp.enviar(lead.id, texto)
            return "whatsapp"
        raise RuntimeError(f"sem canal para entregar a mensagem ao lead {lead.id} (canal: {lead.canal})")


def processar_decisao(lead_id: str, decisao: str, observacao: str, usuario: str, agente, entregador: Entregador, slack: SlackBrax) -> str:
    """O time clicou num botão do Slack: grava a decisão, a IA escreve o retorno e ele é entregue ao lead."""
    with trava_do_lead(lead_id):
        lead = memoria.carregar(lead_id, pasta=agente.pasta_leads)
        if lead.aprovacao != "pendente":
            return "já decidido"  # dois cliques, ou outra pessoa do time já respondeu
        lead.aprovacao = decisao
        lead.registrar_evento(f"aprovacao_{decisao}", f"Slack <@{usuario}>: {observacao}".strip(": "))
        if lead.opt_out:
            memoria.salvar(lead, pasta=agente.pasta_leads)
            slack.finalizar(lead, "⛔ Sem retorno", "o lead pediu para não receber mensagens")
            return "sem retorno (opt-out)"
        memoria.salvar(lead, pasta=agente.pasta_leads)

        instrucao, link, padrao = _instrucao(decisao, lead, observacao)
        texto = agente.mensagem_proativa(lead_id, instrucao, link, padrao)
        lead = memoria.carregar(lead_id, pasta=agente.pasta_leads)
        try:
            canal = entregador.entregar(lead, texto)
            lead.registrar_evento("retorno_enviado", canal)
        except Exception as erro:
            lead.registrar_evento("retorno_falhou", str(erro)[:200])
            canal = None
        sincronizar_com_seguranca(agente.crm, lead)
        memoria.salvar(lead, pasta=agente.pasta_leads)
        detalhe = f"por <@{usuario}>" + (f" · {observacao}" if observacao else "")
        if not canal:
            detalhe += " · ⚠️ o retorno não pôde ser entregue ao lead"
        slack.finalizar(lead, _SITUACAO.get(decisao, decisao), detalhe)
        return f"retorno enviado ({canal})" if canal else "retorno não entregue"


def devolver_ao_ph(lead_id: str, usuario: str, agente, slack: SlackBrax) -> str:
    """O time terminou o atendimento: o P.H. volta a responder este lead na próxima mensagem (decisão 036)."""
    with trava_do_lead(lead_id):
        lead = memoria.carregar(lead_id, pasta=agente.pasta_leads)
        if not lead.atendimento_humano:
            return "já estava com o P.H."
        lead.atendimento_humano = False
        lead.registrar_evento("devolvido_ao_ph", f"Slack <@{usuario}>")
        memoria.salvar(lead, pasta=agente.pasta_leads)
    alerta = lead.slack.get("alerta")
    if alerta:
        slack.cliente.chat_update(
            channel=alerta["canal"], ts=alerta["ts"], text=f"Devolvido ao P.H.: {_rotulo_do_lead(lead)}",
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": (
                    f"🙋 *Atendimento humano* · {_rotulo_do_lead(lead)}\n*Motivo:* {alerta.get('motivo', '-')}"
                )}},
                {"type": "context", "elements": [{"type": "mrkdwn", "text": f"✅ Devolvido ao P.H. por <@{usuario}>"}]},
            ],
        )
    return "devolvido ao P.H."


def registrar_acoes(app, ao_decidir, ao_devolver=None) -> None:
    """Liga os botões e a janela do Slack (slack_bolt.App) às funções ao_decidir(lead_id, decisao, observacao, usuario)
    e ao_devolver(lead_id, usuario)."""

    @app.action(ACAO_DEVOLVER)
    def _devolver(ack, body):
        ack()
        if ao_devolver:
            ao_devolver(body["actions"][0]["value"], body["user"]["id"])

    @app.action(ACAO_APROVAR)
    def _aprovar(ack, body):
        ack()
        ao_decidir(body["actions"][0]["value"], "aprovada", "", body["user"]["id"])

    @app.action(ACAO_INDICAR_APP)
    def _indicar_app(ack, body):
        ack()
        ao_decidir(body["actions"][0]["value"], "recusada", "indicar o app", body["user"]["id"])

    @app.action(ACAO_NOVO_HORARIO)
    def _novo_horario(ack, body, client):
        ack()
        client.views_open(trigger_id=body["trigger_id"], view=janela_de_horario(body["actions"][0]["value"]))

    @app.view(JANELA_HORARIO)
    def _horario_enviado(ack, body, view):
        ack()
        horario = view["state"]["values"]["horario"]["valor"]["value"]
        ao_decidir(view["private_metadata"], "novo_horario", horario, body["user"]["id"])
