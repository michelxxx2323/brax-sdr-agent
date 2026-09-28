"""Testes do laço do agente com um cliente FALSO: nenhuma chamada real à API."""

import copy

from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

from brax_sdr import memoria
from brax_sdr.agente import Agente


def _msg(conteudo, stop_reason):
    return Message(
        id="msg_teste",
        type="message",
        role="assistant",
        model="claude-haiku-4-5",
        content=conteudo,
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=Usage(input_tokens=100, output_tokens=20),
    )


class ClienteFalso:
    """Imita client.messages.create devolvendo respostas pré-programadas, em ordem."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []
        self.messages = self

    def create(self, **kwargs):
        self.chamadas.append(copy.deepcopy(kwargs))  # cópia: o agente continua mexendo na lista depois
        return self.respostas.pop(0)


def test_conversa_com_ferramenta_salva_historico_completo(tmp_path):
    cliente = ClienteFalso([
        _msg([ToolUseBlock(id="t1", name="registrar_qualificacao", input={"funcionarios": 6}, type="tool_use")], "tool_use"),
        _msg([TextBlock(text="Oi! Aqui é o P.H., assistente virtual da BRAX.", type="text")], "end_turn"),
    ])
    agente = Agente(client=cliente, pasta_leads=tmp_path)
    resposta = agente.responder("lead1", "Somos 6 pessoas")

    assert resposta.texto == "Oi! Aqui é o P.H., assistente virtual da BRAX."
    assert resposta.ferramentas_usadas == ["registrar_qualificacao"]
    assert resposta.alertas == []
    assert resposta.uso["input_tokens"] == 200

    salvo = memoria.carregar("lead1", pasta=tmp_path)
    assert salvo.dados == {"funcionarios": 6}
    assert [m["role"] for m in salvo.mensagens] == ["user", "assistant", "user", "assistant"]
    assert salvo.mensagens[2]["content"][0]["tool_use_id"] == "t1"

    # A segunda chamada já enxerga o dado registrado no contexto do lead.
    assert '"funcionarios": 6' in cliente.chamadas[1]["system"][1]["text"]


def test_texto_escrito_junto_com_ferramenta_nao_se_perde(tmp_path):
    # Caso real da primeira conversa: texto + ferramenta na mesma rodada, depois rodada final vazia.
    cliente = ClienteFalso([
        _msg([
            TextBlock(text="Perfeito! Hoje como o time paga as despesas?", type="text"),
            ToolUseBlock(id="t1", name="registrar_qualificacao", input={"funcionarios": 12}, type="tool_use"),
        ], "tool_use"),
        _msg([], "end_turn"),
    ])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("lead7", "Somos 12 pessoas")
    assert resposta.texto == "Perfeito! Hoje como o time paga as despesas?"


def test_texto_antes_da_ferramenta_nao_aparece_quando_ha_texto_depois(tmp_path):
    # Caso real "lumen2": pergunta escrita antes da aprovação + resposta depois da recusa = duas mensagens contraditórias.
    lead = memoria.carregar("lead8", pasta=tmp_path)
    lead.faixa = "executivo"
    memoria.salvar(lead, pasta=tmp_path)
    cliente = ClienteFalso([
        _msg([
            TextBlock(text="Qual horário funciona melhor para você hoje: manhã ou tarde?", type="text"),
            ToolUseBlock(id="t1", name="solicitar_aprovacao_executivo",
                         input={"resumo": "Lumen", "disponibilidade": "Hoje"}, type="tool_use"),
        ], "tool_use"),
        _msg([TextBlock(text="Hoje não dá, mas amanhã às 15h está livre: link", type="text")], "end_turn"),
    ])
    agente = Agente(client=cliente, pasta_leads=tmp_path, aprovador=lambda *_: ("novo_horario", "amanhã às 15h"))
    resposta = agente.responder("lead8", "Quero conversar hoje")

    assert resposta.texto == "Hoje não dá, mas amanhã às 15h está livre: link"
    salvo = memoria.carregar("lead8", pasta=tmp_path)
    textos_salvos = [b["text"] for m in salvo.mensagens if isinstance(m["content"], list) for b in m["content"] if b["type"] == "text"]
    assert textos_salvos == ["Hoje não dá, mas amanhã às 15h está livre: link"]  # o histórico mostra só o que o lead viu
    assert salvo.mensagens[1]["content"][0]["type"] == "tool_use"


def test_confirmacao_inventada_gera_alerta(tmp_path):
    # Caso real "lumen2": o P.H. disse que o time confirmou sem ter pedido aprovação.
    cliente = ClienteFalso([_msg([TextBlock(
        text="O time confirmou: amanhã às 15h está fechado. Link: [link será enviado pelo time]", type="text")], "end_turn")])
    lead = memoria.carregar("lead9", pasta=tmp_path)
    lead.mensagens = [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "Olá, sou o P.H., assistente virtual."}]
    memoria.salvar(lead, pasta=tmp_path)
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("lead9", "E aí?")
    assert "Confiabilidade: afirma confirmação do time sem ter pedido aprovação nesta resposta" in resposta.alertas
    assert "Confiabilidade: texto de exemplo entre colchetes (ex.: [link])" in resposta.alertas
    assert memoria.carregar("lead9", pasta=tmp_path).eventos[-1]["tipo"] == "alerta_confiabilidade"


def test_historico_e_relido_na_mensagem_seguinte(tmp_path):
    cliente = ClienteFalso([
        _msg([TextBlock(text="Olá! Sou o P.H., assistente virtual da BRAX.", type="text")], "end_turn"),
        _msg([TextBlock(text="Entendi.", type="text")], "end_turn"),
    ])
    agente = Agente(client=cliente, pasta_leads=tmp_path)
    agente.responder("lead2", "Oi")
    agente.responder("lead2", "Tudo bem?")
    enviadas = cliente.chamadas[1]["messages"]
    assert [m["role"] for m in enviadas] == ["user", "assistant", "user"]
    assert enviadas[0]["content"] == "Oi"
    assert enviadas[2]["content"] == "Tudo bem?"


def test_primeira_mensagem_sem_identificacao_gera_alerta(tmp_path):
    cliente = ClienteFalso([_msg([TextBlock(text="Oi, tudo bem?", type="text")], "end_turn")])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("lead3", "Oi")
    assert resposta.alertas == ["G4: primeira mensagem sem identificação como assistente virtual"]
    assert memoria.carregar("lead3", pasta=tmp_path).eventos[-1]["tipo"] == "alerta_guardrail"


def test_depois_do_opt_out_o_agente_nao_chama_a_api(tmp_path):
    lead = memoria.carregar("lead4", pasta=tmp_path)
    lead.opt_out = True
    memoria.salvar(lead, pasta=tmp_path)
    cliente = ClienteFalso([])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("lead4", "Oi de novo")
    assert resposta.texto is None
    assert cliente.chamadas == []


def test_erro_da_api_nao_corrompe_o_historico(tmp_path):
    class ClienteQueFalha(ClienteFalso):
        def create(self, **kwargs):
            if self.respostas:
                return super().create(**kwargs)
            raise RuntimeError("API fora do ar")

    cliente = ClienteQueFalha([
        _msg([ToolUseBlock(id="t1", name="registrar_opt_out", input={}, type="tool_use")], "tool_use"),
    ])
    agente = Agente(client=cliente, pasta_leads=tmp_path)
    try:
        agente.responder("lead5", "Para de me mandar mensagem")
    except RuntimeError:
        pass
    salvo = memoria.carregar("lead5", pasta=tmp_path)
    assert salvo.mensagens == []  # nada salvo pela metade
    assert salvo.opt_out is False


def test_recusa_do_modelo_vira_transferencia_segura(tmp_path):
    cliente = ClienteFalso([_msg([], "refusal")])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("lead6", "...")
    assert "pessoa do nosso time" in resposta.texto
    salvo = memoria.carregar("lead6", pasta=tmp_path)
    assert salvo.mensagens[-1]["role"] == "assistant"
