"""Testes das ferramentas e da checagem de guardrails. Não chamam a API."""

import json

from brax_sdr import config
from brax_sdr.ferramentas import executar
from brax_sdr.guardrails import checar_resposta
from brax_sdr.memoria import Lead


def _executar(nome, entrada, lead, aprovador=None):
    saida, erro = executar(nome, entrada, lead, aprovador)
    return json.loads(saida), erro


def test_qualificacao_acumula_dados_e_calcula_prioridade():
    lead = Lead(id="t")
    _executar("registrar_qualificacao", {"empresa": "Lumen", "sinais_de_compra": ["rodada_recente"]}, lead)
    _executar("registrar_qualificacao", {"funcionarios": 28, "decisor": True, "sinais_de_compra": ["gastos_em_dolar"]}, lead)
    assert lead.dados["empresa"] == "Lumen"
    assert lead.dados["sinais_de_compra"] == ["gastos_em_dolar", "rodada_recente"]
    assert lead.prioridade == 3 + 2 + 2


def test_qualificacao_rejeita_dado_invalido_sem_alterar_o_lead():
    lead = Lead(id="t")
    resultado, erro = _executar("registrar_qualificacao", {"funcionarios": "vinte"}, lead)
    assert erro is True
    assert "funcionarios" in resultado["erro"]
    assert lead.dados == {}
    _, erro = _executar("registrar_qualificacao", {"tipo_empresa": "cooperativa"}, lead)
    assert erro is True


def test_rotear_self_service_devolve_link_do_app():
    lead = Lead(id="t", dados={"tipo_empresa": "ltda", "funcionarios": 6, "gasto_mensal": 8000})
    resultado, _ = _executar("rotear_lead", {}, lead)
    assert resultado["faixa"] == "self_service"
    assert resultado["link_app"] == config.LINK_APP
    assert lead.faixa == "self_service"


def test_rotear_com_dados_insuficientes_nao_grava_faixa():
    lead = Lead(id="t", dados={"tipo_empresa": "ltda"})
    resultado, _ = _executar("rotear_lead", {}, lead)
    assert resultado["faixa"] == "dados_insuficientes"
    assert lead.faixa is None


def test_aprovacao_exige_faixa_executivo():
    lead = Lead(id="t", faixa="self_service")
    _, erro = _executar("solicitar_aprovacao_executivo", {"resumo": "x", "disponibilidade": "tarde"}, lead)
    assert erro is True


def test_aprovacao_aprovada_libera_link_de_agenda():
    lead = Lead(id="t", faixa="executivo")
    resultado, _ = _executar(
        "solicitar_aprovacao_executivo",
        {"resumo": "Lumen, 28 pessoas", "disponibilidade": "tarde"},
        lead,
        aprovador=lambda lead, resumo, disp: ("aprovada", "ok"),
    )
    assert resultado["link_agenda"] == config.LINK_AGENDA_EXECUTIVO
    assert lead.aprovacao == "aprovada"


def test_aprovacao_sem_aprovador_fica_pendente_e_sem_link():
    lead = Lead(id="t", faixa="executivo")
    resultado, _ = _executar("solicitar_aprovacao_executivo", {"resumo": "x", "disponibilidade": "manhã"}, lead)
    assert resultado["aprovacao"] == "pendente"
    assert "link_agenda" not in resultado


def test_opt_out_marca_o_lead():
    lead = Lead(id="t")
    _executar("registrar_opt_out", {}, lead)
    assert lead.opt_out is True
    assert lead.eventos[-1]["tipo"] == "opt_out"


def test_ferramenta_desconhecida_vira_erro():
    _, erro = _executar("apagar_tudo", {}, Lead(id="t"))
    assert erro is True


# --- Guardrails ---

def test_resposta_segura_nao_gera_alerta():
    texto = "Oi! Aqui é o P.H., assistente virtual da BRAX. O limite depende de uma análise feita no app."
    assert checar_resposta(texto, primeira_mensagem=True) == []


def test_alertas_de_guardrail():
    assert checar_resposta("Seu limite será de R$ 20 mil.", False) == ["G1: possível valor de limite informado"]
    assert checar_resposta("Pode me enviar o contrato social por aqui?", False) == ["G2: possível pedido de dado sensível"]
    assert checar_resposta("O saldo rende 1,2% ao mês.", False) == ["G3: possível rendimento com percentual"]
    assert checar_resposta("Oi! Tudo bem?", True) == ["G4: primeira mensagem sem identificação como assistente virtual"]


def test_frase_de_protecao_nao_e_confundida_com_pedido():
    texto = "Eu nunca vou te pedir senha, código ou documento por aqui."
    assert checar_resposta(texto, False) == []
