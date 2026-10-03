"""Testes dos evals e do painel, com Claude FALSO: nenhuma chamada à API."""

import json

from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

from brax_sdr import config
from brax_sdr.evals import CRITERIOS, carregar_cenarios, resumir, rodar_bateria, verificar
from brax_sdr.memoria import Lead
from brax_sdr.painel import gerar_html


def _msg(conteudo, stop="end_turn"):
    return Message(id="x", type="message", role="assistant", model="m", stop_reason=stop, stop_sequence=None,
                   usage=Usage(input_tokens=10, output_tokens=5), content=conteudo)


class ClaudeRoteirizado:
    """Responde conforme quem chama: lead simulado (modelo do lead), juiz (forçado a usar ferramenta) ou o P.H."""

    def __init__(self, falas_do_lead, falas_do_ph):
        self.falas_do_lead, self.falas_do_ph = list(falas_do_lead), list(falas_do_ph)
        self.messages = self

    def create(self, **kwargs):
        if kwargs.get("tool_choice", {}).get("type") == "tool":  # o juiz
            notas = {c: 4 for c in CRITERIOS}
            return _msg([ToolUseBlock(type="tool_use", id="j", name="registrar_avaliacao",
                                      input={**notas, "problemas": ["exemplo"], "resumo": "Boa conversa."})], "tool_use")
        if kwargs["max_tokens"] == 512:  # o lead simulado
            return _msg([TextBlock(type="text", text=self.falas_do_lead.pop(0))])
        return _msg([TextBlock(type="text", text=self.falas_do_ph.pop(0))])  # o P.H.


def test_cenarios_sao_validos():
    cenarios = carregar_cenarios()
    assert len(cenarios) == 20
    assert len({c["id"] for c in cenarios}) == 20  # ids únicos
    for c in cenarios:
        assert c["canal"] in ("whatsapp", "email") and c["persona"] and c["esperado"]


def test_verificacoes_objetivas():
    cenario = {"esperado": {"faixa": "fora_do_icp", "motivo_faixa_um_de": ["pessoa_fisica", "sem_cnpj"], "sem_alertas": ["G1"]}}
    lead = Lead(id="x", faixa="fora_do_icp", motivo_faixa="sem_cnpj")
    assert verificar(cenario, lead, []) == {
        "faixa": True, "motivo_faixa": True, "sem_alerta_G1": True, "sem_vazamento": True, "sem_alerta_de_confiabilidade": True,
    }
    lead.registrar_evento("vazamento_bloqueado", "o lead...")
    resultado = verificar(cenario, lead, ["G1: possível valor de limite informado"])
    assert resultado["sem_alerta_G1"] is False and resultado["sem_vazamento"] is False


def test_bateria_completa_com_lead_simulado_e_juiz():
    cenario = {"id": "teste", "titulo": "Teste", "canal": "whatsapp", "persona": "...", "esperado": {"opt_out": False}}
    cliente = ClaudeRoteirizado(
        falas_do_lead=["Oi, quero saber dos cartões", "[FIM]"],
        falas_do_ph=["Oi! Aqui é o P.H., assistente virtual da BRAX. Qual o nome da empresa?"],
    )
    bateria = rodar_bateria([cenario], cliente=cliente)
    [r] = bateria["resultados"]
    assert r["conversa"] == [("lead", "Oi, quero saber dos cartões"),
                             ("ph", "Oi! Aqui é o P.H., assistente virtual da BRAX. Qual o nome da empresa?")]
    assert r["passou"] is True and r["notas"]["resumo"] == "Boa conversa."
    assert r["custo_usd"] > 0 and bateria["modelo_conversa"] == config.MODELO_CONVERSA
    assert bateria["resumo"]["nota_media"] == 4.0


def test_resumo_e_painel():
    resultado = {
        "id": "x", "titulo": "Cenário <x>", "canal": "whatsapp", "esperado": {"faixa": "self_service"},
        "obtido": {"faixa": "executivo"}, "verificacoes": {"faixa": False, "sem_vazamento": True},
        "passou": False, "notas": {**{c: 3 for c in CRITERIOS}, "problemas": ["Prometeu <ligação>"], "resumo": "ok"},
        "alertas": ["G1: possível valor de limite informado"], "mensagens_do_lead": 4,
        "custo_usd": 0.05, "custo_ph_usd": 0.03, "conversa": [("lead", "oi"), ("ph", "olá <b>")],
    }
    resumo = resumir([resultado])
    assert resumo["taxa_roteamento_correto"] == 0 and resumo["alertas_de_guardrail"] == 1 and resumo["nota_media"] == 3
    bateria = {"data": "2026-10-04T10:00:00", "modelo_conversa": "claude-haiku-4-5", "modelo_juiz": "claude-sonnet-5",
               "modelo_lead_simulado": "claude-haiku-4-5", "resultados": [resultado], "resumo": resumo}
    pagina = gerar_html([bateria])
    assert "Evals do P.H." in pagina and "falhou" in pagina
    assert "&lt;b&gt;" in pagina and "<b>Lead:</b>" in pagina  # texto da conversa escapado; marcação própria mantida
    assert "Prometeu &lt;ligação&gt;" in pagina
    assert json.loads(json.dumps(bateria))  # a bateria é serializável
