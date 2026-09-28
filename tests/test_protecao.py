"""Testes de encerramento e proteção de custo. Nenhum chama a API."""

import pytest

from brax_sdr import config, memoria
from brax_sdr.agente import Agente
from brax_sdr.ferramentas import executar
from brax_sdr.memoria import Lead
from brax_sdr.protecao import MENSAGEM_LIMITE_CUSTO, MENSAGEM_LIMITE_DIARIO, MENSAGEM_TEXTO_LONGO, eh_despedida


class ClienteQueNaoPodeSerChamado:
    """Qualquer chamada à API aqui é um erro: a proteção deveria ter barrado antes."""

    def __init__(self):
        self.messages = self

    def create(self, **kwargs):
        raise AssertionError("a API não deveria ter sido chamada")


def _agente(tmp_path):
    return Agente(client=ClienteQueNaoPodeSerChamado(), pasta_leads=tmp_path)


@pytest.mark.parametrize("texto", ["tmj", "é nois", "Valeu!", "obrigado 🙏", "👍", "falou, abraço", "Tchau tchau", "ok, combinado"])
def test_reconhece_despedidas(texto):
    assert eh_despedida(texto)


@pytest.mark.parametrize("texto", ["Bom dia", "valeu, e quanto custa o plano?", "tchau, mas antes: tem cartão virtual?"])
def test_nao_confunde_pergunta_com_despedida(texto):
    assert not eh_despedida(texto)


def test_ferramenta_encerra_a_conversa_depois_do_roteamento():
    lead = Lead(id="t", faixa="self_service")
    _, erro = executar("encerrar_conversa", {"motivo": "proximo_passo_entregue"}, lead)
    assert erro is False
    assert lead.encerrada is True


def test_nao_encerra_lead_que_nao_foi_roteado():
    # Caso real "mei": o P.H. encerrou com "Abraço!" sem rotear; o CRM ficou sem faixa e sem motivo.
    lead = Lead(id="t")
    saida, erro = executar("encerrar_conversa", {"motivo": "proximo_passo_entregue"}, lead)
    assert erro is True
    assert "rotear_lead" in saida
    assert lead.encerrada is False


def test_conversa_fora_do_assunto_pode_ser_encerrada_sem_roteamento():
    lead = Lead(id="t")
    _, erro = executar("encerrar_conversa", {"motivo": "fora_do_assunto"}, lead)
    assert erro is False
    assert lead.encerrada is True


def test_despedida_depois_do_encerramento_nao_chama_a_api(tmp_path):
    # Caso real "lumen3": o P.H. respondeu "tmj" e "é nois" com emojis, gastando tokens.
    lead = memoria.carregar("fim", pasta=tmp_path)
    lead.encerrada = True
    memoria.salvar(lead, pasta=tmp_path)
    resposta = _agente(tmp_path).responder("fim", "é nois")
    assert resposta.texto is None
    assert resposta.motivo_silencio == "conversa_encerrada"


def test_pergunta_nova_reabre_a_conversa(tmp_path):
    lead = memoria.carregar("volta", pasta=tmp_path)
    lead.encerrada = True
    memoria.salvar(lead, pasta=tmp_path)
    with pytest.raises(AssertionError, match="API não deveria"):
        _agente(tmp_path).responder("volta", "Esqueci de perguntar: tem cartão virtual?")  # chegou à API = reabriu


def test_limite_diario_avisa_uma_vez_e_depois_fica_em_silencio(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LIMITE_MENSAGENS_POR_DIA", 2)
    lead = memoria.carregar("spam", pasta=tmp_path)
    lead.encerrada = True  # as 2 primeiras são despedidas: contam, mas não chamam a API
    memoria.salvar(lead, pasta=tmp_path)
    agente = _agente(tmp_path)
    agente.responder("spam", "ok")
    agente.responder("spam", "ok")
    assert agente.responder("spam", "ok").texto == MENSAGEM_LIMITE_DIARIO
    quarta = agente.responder("spam", "ok")
    assert quarta.texto is None
    assert quarta.motivo_silencio == "limite_diario"


def test_limite_de_custo_passa_para_humano_sem_chamar_a_api(tmp_path):
    lead = memoria.carregar("caro", pasta=tmp_path)
    lead.custo_total_usd = config.LIMITE_CUSTO_POR_LEAD_USD
    memoria.salvar(lead, pasta=tmp_path)
    agente = _agente(tmp_path)
    assert agente.responder("caro", "mais uma pergunta").texto == MENSAGEM_LIMITE_CUSTO
    assert agente.responder("caro", "e outra").texto is None
    salvo = memoria.carregar("caro", pasta=tmp_path)
    assert salvo.bloqueio == "limite_de_custo"
    assert any(e["tipo"] == "transferencia_humano" for e in salvo.eventos)


def test_mensagem_longa_pede_resumo_sem_chamar_a_api(tmp_path):
    resposta = _agente(tmp_path).responder("longo", "a" * (config.LIMITE_CARACTERES_MENSAGEM + 1))
    assert resposta.texto == MENSAGEM_TEXTO_LONGO
    salvo = memoria.carregar("longo", pasta=tmp_path)
    assert "não processada" in salvo.mensagens[0]["content"]  # o texto gigante não é guardado


def test_lead_salvo_antes_das_novas_regras_continua_abrindo(tmp_path):
    # Arquivos antigos (sem os campos novos) precisam continuar funcionando.
    antigo = Lead(id="antigo")
    memoria.salvar(antigo, pasta=tmp_path)
    caminho = tmp_path / "antigo.json"
    import json
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    for campo in ("encerrada", "custo_total_usd", "mensagens_hoje", "bloqueio"):
        dados.pop(campo)
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    assert memoria.carregar("antigo", pasta=tmp_path).custo_total_usd == 0.0
