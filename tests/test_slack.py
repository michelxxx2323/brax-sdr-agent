"""Testes da aprovação pelo Slack (decisão 034) com Slack, Claude, Gmail e WhatsApp FALSOS: nada sai para a internet."""

import json

import pytest
from anthropic.types import Message, TextBlock, Usage

from brax_sdr import config, memoria
from brax_sdr.agente import Agente
from brax_sdr.canal_whatsapp import EnvioSimulado
from brax_sdr.ferramentas import executar
from brax_sdr.memoria import Lead
from brax_sdr.resumo import resumo_sem_ia
from brax_sdr.slack_brax import (
    ACAO_APROVAR,
    ACAO_INDICAR_APP,
    ACAO_NOVO_HORARIO,
    JANELA_HORARIO,
    Entregador,
    SlackBrax,
    processar_decisao,
    registrar_acoes,
)

TELEFONE = "5511900000002"


class SlackFalso:
    def __init__(self):
        self.postadas, self.atualizadas, self.janelas = [], [], []

    def chat_postMessage(self, **kwargs):
        self.postadas.append(kwargs)
        return {"channel": "C123", "ts": f"1700.{len(self.postadas)}"}

    def chat_update(self, **kwargs):
        self.atualizadas.append(kwargs)

    def views_open(self, **kwargs):
        self.janelas.append(kwargs)


class ClaudeFalso:
    def __init__(self, textos):
        self.textos, self.chamadas = list(textos), []
        self.messages = self

    def create(self, **kwargs):
        self.chamadas.append(kwargs)
        return Message(id="x", type="message", role="assistant", model="claude-haiku-4-5", stop_reason="end_turn",
                       stop_sequence=None, usage=Usage(input_tokens=1, output_tokens=1),
                       content=[TextBlock(type="text", text=self.textos.pop(0))])


def _slack(falso=None):
    return SlackBrax(falso or SlackFalso(), canal="C123", resumidor=lambda lead: "Ana · Lumen · 28 pessoas · R$ 70 mil/mês")


def lead_pendente(pasta, **mudancas) -> Lead:
    lead = Lead(id=TELEFONE, canal="whatsapp", faixa="executivo", motivo_faixa="28 funcionários (> 20)", aprovacao="pendente",
                dados={"nome_contato": "Ana", "empresa": "Lumen"},
                slack={"canal": "C123", "ts": "1700.1", "resumo": "Ana · Lumen", "disponibilidade": "segunda de manhã"},
                mensagens=[{"role": "user", "content": "segunda de manhã"},
                           {"role": "assistant", "content": "Vou confirmar a agenda com o time e te retorno por aqui."}])
    for campo, valor in mudancas.items():
        setattr(lead, campo, valor)
    memoria.salvar(lead, pasta=pasta)
    return lead


def _saida(envio):
    return [json.loads(linha) for linha in envio.arquivo.read_text(encoding="utf-8").splitlines()] if envio.arquivo.exists() else []


# --- Pedido de aprovação ---

def test_pedido_de_aprovacao_vai_para_o_slack_e_fica_pendente():
    falso = SlackFalso()
    lead = Lead(id=TELEFONE, faixa="executivo", motivo_faixa="28 funcionários (> 20)", dados={"empresa": "Lumen"})
    saida, erro = executar("solicitar_aprovacao_executivo", {"resumo": "x", "disponibilidade": "segunda de manhã"}, lead, _slack(falso).aprovador)
    resultado = json.loads(saida)
    assert erro is False and resultado["aprovacao"] == "pendente" and "link_agenda" not in resultado
    assert lead.slack == {"canal": "C123", "ts": "1700.1", "resumo": "Ana · Lumen · 28 pessoas · R$ 70 mil/mês", "disponibilidade": "segunda de manhã"}
    botoes = [e["action_id"] for e in falso.postadas[0]["blocks"][-1]["elements"]]
    assert botoes == [ACAO_APROVAR, ACAO_NOVO_HORARIO, ACAO_INDICAR_APP]
    assert all(e["value"] == TELEFONE for e in falso.postadas[0]["blocks"][-1]["elements"])


def test_transferencia_para_humano_avisa_no_slack():
    falso = SlackFalso()
    lead = Lead(id=TELEFONE, dados={"empresa": "Lumen", "nome_contato": "Ana"})
    executar("transferir_para_humano", {"motivo": "pediu para falar com uma pessoa"}, lead, alerta_humano=_slack(falso).alerta_humano)
    assert "pediu para falar com uma pessoa" in falso.postadas[0]["blocks"][0]["text"]["text"]


def test_resumo_sem_ia_nao_inventa_cargo():
    # Achado da Fase 4: "Ana, parece ser founder/CEO" sem ela ter dito o cargo.
    texto = resumo_sem_ia(Lead(id="x", dados={"nome_contato": "Ana", "empresa": "Lumen"}))
    assert "cargo: não informado" in texto


# --- Decisão no Slack → retorno ao lead ---

def _cenario(tmp_path, textos_da_ia):
    agente = Agente(client=ClaudeFalso(textos_da_ia), pasta_leads=tmp_path)
    envio = EnvioSimulado(pasta=tmp_path)
    slack_falso = SlackFalso()
    return agente, envio, Entregador(envio_whatsapp=envio), slack_falso, _slack(slack_falso)


def test_aprovacao_gera_retorno_da_ia_com_o_link(tmp_path):
    lead_pendente(tmp_path)
    texto_ia = f"Boa notícia, Ana! O time confirmou. Escolha seu horário de segunda pela manhã: {config.LINK_AGENDA_EXECUTIVO}"
    agente, envio, entregador, slack_falso, slack = _cenario(tmp_path, [texto_ia])

    assert processar_decisao(TELEFONE, "aprovada", "", "U1", agente, entregador, slack) == "retorno enviado (whatsapp)"
    assert _saida(envio)[0]["texto"] == texto_ia
    salvo = memoria.carregar(TELEFONE, pasta=tmp_path)
    assert salvo.aprovacao == "aprovada" and salvo.mensagens[-1]["content"] == texto_ia
    assert agente.client.chamadas[0]["tool_choice"] == {"type": "none"}  # a IA só escreve; não usa ferramentas
    assert "✅ Aprovado" in slack_falso.atualizadas[0]["blocks"][-1]["elements"][0]["text"]


def test_retorno_sem_o_link_cai_no_texto_padronizado(tmp_path):
    lead_pendente(tmp_path)
    agente, envio, entregador, _, slack = _cenario(tmp_path, ["Oi, Ana! Tudo certo, o time vai te procurar."])  # sem link
    processar_decisao(TELEFONE, "aprovada", "", "U1", agente, entregador, slack)
    texto = _saida(envio)[0]["texto"]
    assert config.LINK_AGENDA_EXECUTIVO in texto and texto.startswith("Boa notícia, Ana!")
    eventos = memoria.carregar(TELEFONE, pasta=tmp_path).eventos
    assert {"tipo": "retorno_padrao_usado", "detalhe": "link obrigatório ausente"}.items() <= next(
        e for e in eventos if e["tipo"] == "retorno_padrao_usado").items()


def test_retorno_com_texto_interno_cai_no_texto_padronizado(tmp_path):
    lead_pendente(tmp_path)
    vazado = f"O lead foi aprovado. Link: {config.LINK_AGENDA_EXECUTIVO}"
    agente, envio, entregador, _, slack = _cenario(tmp_path, [vazado])
    processar_decisao(TELEFONE, "aprovada", "", "U1", agente, entregador, slack)
    assert "O lead" not in _saida(envio)[0]["texto"]


def test_sugerir_outro_horario_inclui_o_horario_e_o_link(tmp_path):
    lead_pendente(tmp_path)
    agente, envio, entregador, slack_falso, slack = _cenario(tmp_path, ["Ana, segunda não dá. Que tal amanhã?"])  # sem link
    processar_decisao(TELEFONE, "novo_horario", "terça às 10h", "U1", agente, entregador, slack)
    texto = _saida(envio)[0]["texto"]
    assert "terça às 10h" in texto and config.LINK_AGENDA_EXECUTIVO in texto
    assert "terça às 10h" in slack_falso.atualizadas[0]["blocks"][-1]["elements"][0]["text"]


def test_indicar_o_app_envia_o_link_do_app(tmp_path):
    lead_pendente(tmp_path)
    texto_ia = f"Ana, o caminho mais rápido para a Lumen é abrir a conta pelo app: {config.LINK_APP}. Cadastro e documentos só por lá."
    agente, envio, entregador, _, slack = _cenario(tmp_path, [texto_ia])
    processar_decisao(TELEFONE, "recusada", "indicar o app", "U1", agente, entregador, slack)
    assert _saida(envio)[0]["texto"] == texto_ia


def test_segundo_clique_nao_gera_segundo_retorno(tmp_path):
    lead_pendente(tmp_path)
    agente, envio, entregador, _, slack = _cenario(tmp_path, [f"Ana, aprovado! {config.LINK_AGENDA_EXECUTIVO}"])
    processar_decisao(TELEFONE, "aprovada", "", "U1", agente, entregador, slack)
    assert processar_decisao(TELEFONE, "recusada", "", "U2", agente, entregador, slack) == "já decidido"
    assert len(_saida(envio)) == 1


def test_lead_que_pediu_parada_nao_recebe_retorno(tmp_path):
    lead_pendente(tmp_path, opt_out=True)
    agente, envio, entregador, slack_falso, slack = _cenario(tmp_path, [])
    assert processar_decisao(TELEFONE, "aprovada", "", "U1", agente, entregador, slack) == "sem retorno (opt-out)"
    assert _saida(envio) == [] and agente.client.chamadas == []
    assert "não receber mensagens" in slack_falso.atualizadas[0]["blocks"][-1]["elements"][0]["text"]


def test_falha_na_entrega_fica_visivel_no_slack(tmp_path):
    lead_pendente(tmp_path)
    agente, _, _, slack_falso, slack = _cenario(tmp_path, [f"Ana, aprovado! {config.LINK_AGENDA_EXECUTIVO}"])
    assert processar_decisao(TELEFONE, "aprovada", "", "U1", agente, Entregador(), slack) == "retorno não entregue"
    assert "não pôde ser entregue" in slack_falso.atualizadas[0]["blocks"][-1]["elements"][0]["text"]


# --- Ligação dos botões (slack_bolt) ---

class AppFalso:
    def __init__(self):
        self.acoes, self.janelas = {}, {}

    def action(self, nome):
        return lambda funcao: self.acoes.setdefault(nome, funcao)

    def view(self, nome):
        return lambda funcao: self.janelas.setdefault(nome, funcao)


def test_botoes_e_janela_chamam_a_decisao_certa():
    app, decisoes, cliente = AppFalso(), [], SlackFalso()
    registrar_acoes(app, lambda *args: decisoes.append(args))
    corpo = {"actions": [{"value": TELEFONE}], "user": {"id": "U1"}, "trigger_id": "T1"}
    app.acoes[ACAO_APROVAR](ack=lambda: None, body=corpo)
    app.acoes[ACAO_INDICAR_APP](ack=lambda: None, body=corpo)
    app.acoes[ACAO_NOVO_HORARIO](ack=lambda: None, body=corpo, client=cliente)
    assert cliente.janelas[0]["view"]["private_metadata"] == TELEFONE
    vista = {"private_metadata": TELEFONE, "state": {"values": {"horario": {"valor": {"value": "terça às 10h"}}}}}
    app.janelas[JANELA_HORARIO](ack=lambda: None, body={"user": {"id": "U1"}}, view=vista)
    assert decisoes == [
        (TELEFONE, "aprovada", "", "U1"),
        (TELEFONE, "recusada", "indicar o app", "U1"),
        (TELEFONE, "novo_horario", "terça às 10h", "U1"),
    ]


# --- Achados do 1º teste real com Slack ---

def test_simulador_mostra_mensagem_proativa_sem_o_lead_escrever(tmp_path, monkeypatch, capsys):
    # O retorno da aprovação chega sem o lead ter escrito nada: antes, o simulador nunca o mostrava.
    from brax_sdr import simulador_whatsapp

    monkeypatch.setattr(config, "PASTA_WHATSAPP", tmp_path)
    envio = EnvioSimulado(pasta=tmp_path)
    envio.enviar(TELEFONE, "mensagem antiga")
    caixa = simulador_whatsapp.CaixaDeEntrada(TELEFONE)
    envio.enviar("5511999999999", "para outro lead")
    envio.enviar(TELEFONE, f"Boa notícia, Bruno! Escolha o horário: {config.LINK_AGENDA_EXECUTIVO}")
    caixa.conferir()
    saida = capsys.readouterr().out
    assert "Boa notícia, Bruno!" in saida
    assert "mensagem antiga" not in saida and "para outro lead" not in saida
    assert caixa.chegou.is_set()


def test_contexto_mostra_o_link_quando_a_reuniao_ja_foi_aprovada():
    from brax_sdr.prompt import montar_system

    contexto = montar_system("C", Lead(id="x", aprovacao="aprovada"))[1]["text"]
    assert config.LINK_AGENDA_EXECUTIVO in contexto and "link_agenda_ja_enviado" in contexto
    assert "link_agenda_ja_enviado" not in montar_system("C", Lead(id="x", aprovacao="pendente"))[1]["text"]


def test_deixa_eu_confirmar_sem_ferramenta_gera_alerta():
    from brax_sdr.guardrails import checar_confiabilidade

    frase = "Opa, Bruno! Deixa eu confirmar com o time se quinta à tarde ainda tá disponível. Já retorno por aqui!"
    assert checar_confiabilidade(frase, []) == ["Confiabilidade: promete uma ação para depois sem ter chamado nenhuma ferramenta"]
