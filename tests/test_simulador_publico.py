"""Testes do simulador público (Fase 8, decisão 060), com Claude FALSO: nenhuma chamada à API."""

import copy

from anthropic.types import Message, TextBlock, ToolUseBlock, Usage
from fastapi import FastAPI
from fastapi.testclient import TestClient

from brax_sdr import memoria
from brax_sdr.agente import Agente
from brax_sdr.canal_email import ASSINATURA
from brax_sdr.followup import numero_do_followup_devido
from brax_sdr.simulador_publico import SimuladorPublico, mascarar_dados_pessoais, registrar_rotas

SESSAO = "3f1c2a9e-1111-4c2b-9d7e-abcdefabcdef"


def _msg(conteudo, stop="end_turn"):
    return Message(id="x", type="message", role="assistant", model="m", stop_reason=stop, stop_sequence=None,
                   usage=Usage(input_tokens=10, output_tokens=5), content=conteudo)


class ClienteFalso:
    def __init__(self, respostas):
        self.respostas, self.chamadas, self.messages = list(respostas), [], self

    def create(self, **kwargs):
        self.chamadas.append(copy.deepcopy(kwargs))
        return self.respostas.pop(0)


def _simulador(tmp_path, respostas, custo=0.0, **limites):
    cliente = ClienteFalso(respostas)
    agente = Agente(client=cliente, pasta_leads=tmp_path)
    return SimuladorPublico(agente, custo_do_dia=lambda: custo, **limites), cliente


def test_mascara_dados_pessoais_e_preserva_numeros_do_negocio():
    texto = ("Sou a Ana, CPF 123.456.789-09, CNPJ 12.345.678/0001-90, cartão 4111 1111 1111 1111, "
             "e-mail ana@lumen.com.br e celular (11) 98765-4321. Somos 12 pessoas e gastamos R$ 15.000 por mês em 2026.")
    limpo, removidos = mascarar_dados_pessoais(texto)
    assert removidos == 5
    for dado in ("123.456.789-09", "12.345.678/0001-90", "4111", "ana@lumen.com.br", "98765-4321"):
        assert dado not in limpo
    assert "12 pessoas" in limpo and "R$ 15.000" in limpo and "2026" in limpo


def test_whatsapp_grava_como_simulador_e_devolve_bastidores(tmp_path):
    simulador, cliente = _simulador(tmp_path, [
        _msg([ToolUseBlock(type="tool_use", id="t1", name="registrar_qualificacao",
                           input={"empresa": "Lumen", "tipo_empresa": "ltda"})], "tool_use"),
        _msg([TextBlock(type="text", text="Oi! Aqui é o P.H., assistente virtual da BRAX. Quantas pessoas são?")]),
    ])
    saida = simulador.processar(SESSAO, "Oi, sou da Lumen, LTDA. Meu CPF é 123.456.789-09", "whatsapp", "1.2.3.4")
    assert saida["texto"].startswith("Oi! Aqui é o P.H.")
    assert saida["dados_pessoais_removidos"] == 1 and "123.456.789-09" not in saida["mensagem_do_lead"]
    assert "123.456.789-09" not in str(cliente.chamadas[0]["messages"])  # a IA nunca viu o CPF
    b = saida["bastidores"]
    assert b["dados"]["empresa"] == "Lumen" and b["etapa"] == "em_qualificacao" and b["temperatura"] == "frio"
    assert {"qualificacao", "dados_pessoais_removidos"} <= {e["tipo"] for e in b["eventos"]}
    lead = memoria.carregar(f"sim-{SESSAO}", pasta=tmp_path)
    assert lead.origem == "simulador" and "123.456.789-09" not in str(lead.mensagens)


def test_email_tem_assunto_e_assinatura_como_um_lead_real_receberia(tmp_path):
    simulador, cliente = _simulador(tmp_path, [_msg([TextBlock(type="text", text="Olá! Aqui é o P.H., assistente virtual da BRAX.\n\nQual o tamanho do time?")])])
    saida = simulador.processar(SESSAO, "Quero saber dos cartões.", "email", "1.2.3.4", assunto="Cartões para o time")
    assert saida["assunto"] == "Re: Cartões para o time"
    assert saida["texto"].endswith(ASSINATURA)
    assert cliente.chamadas[0]["messages"][-1]["content"].startswith("[Assunto do e-mail: Cartões para o time]")


def test_limites_e_teto(tmp_path):
    # Teto diário: nenhuma chamada à IA.
    simulador, cliente = _simulador(tmp_path, [], custo=0.31)
    assert simulador.processar(SESSAO, "Oi", "whatsapp", "1.2.3.4")["bloqueado"] == "teto_diario"
    assert cliente.chamadas == []
    # Limite por endereço de internet.
    simulador, _ = _simulador(tmp_path, [_msg([TextBlock(type="text", text="Oi! Aqui é o P.H., assistente virtual da BRAX.")])],
                              limite_por_ip_dia=1)
    simulador.processar(SESSAO, "Oi", "whatsapp", "9.9.9.9")
    assert simulador.processar(SESSAO, "De novo", "whatsapp", "9.9.9.9")["bloqueado"] == "limite_ip"
    # Limite por conversa.
    simulador, _ = _simulador(tmp_path, [], limite_por_sessao=1)
    assert simulador.processar(SESSAO, "Mais uma", "whatsapp", "5.5.5.5")["bloqueado"] == "limite_sessao"


def test_entradas_invalidas(tmp_path):
    simulador, _ = _simulador(tmp_path, [])
    for sessao, canal in (("../../etc", "whatsapp"), (SESSAO, "sms")):
        try:
            simulador.processar(sessao, "Oi", canal, "1.2.3.4")
            assert False, "deveria recusar"
        except ValueError:
            pass
    assert simulador.processar(SESSAO, "   ", "whatsapp", "1.2.3.4")["bloqueado"] == "texto_vazio"


def test_rota_e_origens_permitidas(tmp_path):
    simulador, _ = _simulador(tmp_path, [_msg([TextBlock(type="text", text="Oi! Aqui é o P.H., assistente virtual da BRAX.")])])
    app = FastAPI()
    registrar_rotas(app, simulador, ["https://painel.brax.example"])
    cliente = TestClient(app)
    r = cliente.post("/simulador/mensagem", json={"sessao": SESSAO, "texto": "Oi"},
                     headers={"Origin": "https://painel.brax.example"})
    assert r.status_code == 200 and r.headers.get("access-control-allow-origin") == "https://painel.brax.example"
    outra = cliente.options("/simulador/mensagem", headers={"Origin": "https://outro.site",
                                                            "Access-Control-Request-Method": "POST"})
    assert outra.headers.get("access-control-allow-origin") is None  # outro site não chama pelo navegador
    assert cliente.post("/simulador/mensagem", json={"sessao": "x", "texto": "Oi"}).status_code == 400


def test_follow_up_ignora_conversa_do_simulador():
    from datetime import datetime, timezone

    lead = memoria.Lead(id=f"sim-{SESSAO}", canal="email", origem="simulador", aguardando_lead=True,
                        ultima_resposta_em="2026-10-01T12:00:00+00:00", email_contexto={"thread_id": "t"})
    assert numero_do_followup_devido(lead, datetime(2026, 10, 9, 15, tzinfo=timezone.utc)) is None
