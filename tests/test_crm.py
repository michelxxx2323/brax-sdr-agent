"""Testes da sincronização com o HubSpot, usando um HubSpot FALSO (httpx.MockTransport): nada sai para a internet."""

import json

import httpx
import pytest

from brax_sdr import memoria
from brax_sdr.crm import (
    ETAPAS,
    HubSpot,
    campos_da_empresa,
    campos_do_contato,
    etapa_do_negocio,
    sincronizar_com_seguranca,
)
from brax_sdr.memoria import Lead


class HubSpotFalso:
    """Guarda objetos em memória e responde às rotas que o crm.py usa."""

    def __init__(self, com_funil_proprio=True, cair=False):
        self.objetos = {"contacts": {}, "companies": {}, "deals": {}}
        self.associacoes = []
        self.campos_criados = []
        self.cair = cair
        self.funis = []
        if com_funil_proprio:
            self.funis.append({"id": "funil-brax", "label": "BRAX Inbound",
                               "stages": [{"id": f"etapa-{k}", "label": rotulo} for k, rotulo, _ in ETAPAS]})
        self._proximo = 100

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        if self.cair:
            return httpx.Response(503, json={"message": "HubSpot fora do ar"})
        partes = pedido.url.path.strip("/").split("/")
        corpo = json.loads(pedido.content) if pedido.content else {}
        if partes[:3] == ["crm", "v3", "pipelines"]:
            if pedido.method == "GET":
                return httpx.Response(200, json={"results": self.funis})
            self.funis.append({"id": "funil-novo", "label": corpo["label"],
                               "stages": [{"id": f"novo-{i}", "label": e["label"]} for i, e in enumerate(corpo["stages"])]})
            return httpx.Response(201, json={"id": "funil-novo"})
        if partes[:3] == ["crm", "v3", "properties"]:
            if len(partes) == 5:  # grupos
                return httpx.Response(201, json={})
            nome = f"{partes[3]}.{corpo['name']}"
            if nome in self.campos_criados:
                return httpx.Response(409, json={"message": "já existe"})
            self.campos_criados.append(nome)
            return httpx.Response(201, json={})
        if partes[:2] == ["crm", "v4"]:
            self.associacoes.append((partes[3], partes[4], partes[7], partes[8]))
            return httpx.Response(200, json={})
        objeto = partes[3]
        if len(partes) == 5 and partes[4] == "search":
            filtro = corpo["filterGroups"][0]["filters"][0]
            achados = [{"id": i} for i, o in self.objetos[objeto].items()
                       if str(o.get(filtro["propertyName"], "")).lower() == filtro["value"].lower()]
            return httpx.Response(200, json={"results": achados[:1]})
        if pedido.method == "POST":
            self._proximo += 1
            id_ = str(self._proximo)
            self.objetos[objeto][id_] = dict(corpo["properties"])
            return httpx.Response(201, json={"id": id_})
        if pedido.method == "PATCH":
            self.objetos[objeto][partes[4]].update(corpo["properties"])
            return httpx.Response(200, json={"id": partes[4]})
        return httpx.Response(404, json={})


def _hubspot(falso):
    return HubSpot(token="teste", transporte=httpx.MockTransport(falso))


def lead_lumen(**mudancas) -> Lead:
    lead = Lead(id="ana@lumen.example", canal="email", faixa="executivo", motivo_faixa="28 funcionários (> 20)",
                dados={"nome_contato": "Ana", "empresa": "Lumen", "tipo_empresa": "ltda", "funcionarios": 28,
                       "gasto_mensal": 70000, "cargo": "CEO", "decisor": True, "sinais_de_compra": ["rodada_recente"]},
                prioridade=5)
    for campo, valor in mudancas.items():
        setattr(lead, campo, valor)
    return lead


# --- Regras (sem HTTP) ---

@pytest.mark.parametrize(
    ("mudancas", "ja_tem", "etapa"),
    [
        ({"faixa": "self_service"}, False, "qualificado_app"),
        ({}, False, "reuniao_solicitada"),
        ({"aprovacao": "pendente"}, False, "reuniao_solicitada"),
        ({"aprovacao": "aprovada"}, False, "reuniao_aprovada"),
        ({"aprovacao": "novo_horario"}, False, "reuniao_aprovada"),
        ({"aprovacao": "recusada"}, False, "qualificado_app"),
        ({"sem_resposta": True}, True, "perdido"),
        ({"opt_out": True}, True, "perdido"),
        ({"faixa": "fora_do_icp", "motivo_faixa": "mei"}, False, None),  # fora do perfil não vira negócio
        ({"faixa": None}, False, None),  # ainda sem faixa
        ({"faixa": None, "sem_resposta": True}, False, None),
    ],
)
def test_etapa_do_negocio(mudancas, ja_tem, etapa):
    assert etapa_do_negocio(lead_lumen(**mudancas), ja_tem_negocio=ja_tem) == etapa


def test_sem_interesse_depois_de_qualificado_vira_perdido():
    lead = lead_lumen(faixa="self_service")
    lead.dados["motivo_encerramento"] = "sem_interesse"
    assert etapa_do_negocio(lead, ja_tem_negocio=True) == "perdido"
    assert campos_do_contato(lead)["brax_motivo_encerramento"] == "sem_interesse"


def test_campos_do_contato_e_da_empresa():
    contato = campos_do_contato(lead_lumen())
    assert contato["email"] == "ana@lumen.example" and contato["firstname"] == "Ana"
    assert contato["brax_decisor"] == "sim" and contato["brax_prioridade"] == "5"
    assert "phone" not in contato
    assert campos_do_contato(Lead(id="5511900000002"))["phone"] == "+5511900000002"  # lead de WhatsApp
    # Bug da 1ª sincronização real: leads do terminal ("lumen") viravam telefone "+lumen".
    terminal = campos_do_contato(Lead(id="lumen"))
    assert "phone" not in terminal and "email" not in terminal and terminal["brax_lead_id"] == "lumen"
    empresa = campos_da_empresa(lead_lumen())
    assert empresa == {"name": "Lumen", "numberofemployees": "28", "brax_tipo_empresa": "ltda", "brax_gasto_mensal": "70000"}


# --- Sincronização com o HubSpot falso ---

def test_primeira_sincronizacao_cria_e_associa_tudo():
    falso = HubSpotFalso()
    lead = lead_lumen()
    feito = _hubspot(falso).sincronizar(lead)
    assert feito == ["contato", "empresa", "negócio (reuniao_solicitada)"]
    negocio = falso.objetos["deals"][lead.crm["negocio_id"]]
    assert (negocio["pipeline"], negocio["dealstage"]) == ("funil-brax", "etapa-reuniao_solicitada")
    assert len(falso.associacoes) == 3  # contato↔empresa, negócio↔contato, negócio↔empresa
    assert lead.crm["pendente"] is False


def test_sincronizar_de_novo_atualiza_sem_duplicar():
    falso = HubSpotFalso()
    hubspot = _hubspot(falso)
    lead = lead_lumen()
    hubspot.sincronizar(lead)
    lead.aprovacao = "aprovada"
    hubspot.sincronizar(lead)
    assert len(falso.objetos["contacts"]) == 1 and len(falso.objetos["deals"]) == 1
    assert falso.objetos["deals"][lead.crm["negocio_id"]]["dealstage"] == "etapa-reuniao_aprovada"
    assert len(falso.associacoes) == 3  # associações só na primeira vez


def test_segunda_pessoa_da_mesma_empresa_reaproveita_a_empresa():
    # Pendência da Fase 2: a Sara e o Ricardo, ambos da Lumen.
    falso = HubSpotFalso()
    hubspot = _hubspot(falso)
    hubspot.sincronizar(lead_lumen())
    sara = lead_lumen(id="sara@lumen.example")
    sara.dados["nome_contato"] = "Sara"
    hubspot.sincronizar(sara)
    assert len(falso.objetos["companies"]) == 1
    assert len(falso.objetos["contacts"]) == 2
    assert sara.eventos[-1]["tipo"] == "crm_empresa_existente"


def test_empresas_seguidas_nao_duplicam_mesmo_com_busca_atrasada():
    # Achado real: a busca do HubSpot demora para enxergar um registro novo; duas Nuvias seguidas viraram duas empresas.
    falso = HubSpotFalso()
    hubspot = _hubspot(falso)
    rota_original = falso.__call__

    def busca_atrasada(pedido):
        if pedido.url.path.endswith("/companies/search"):
            return httpx.Response(200, json={"results": []})  # a busca ainda não enxerga nada
        return rota_original(pedido)

    hubspot.http._transport = httpx.MockTransport(busca_atrasada)
    hubspot.sincronizar(lead_lumen(id="paulo@nuvia.example", dados={"empresa": "Nuvia"}))
    hubspot.sincronizar(lead_lumen(id="ana@nuvia.example", dados={"empresa": "nuvia "}))
    assert len(falso.objetos["companies"]) == 1


def test_contato_que_ja_existia_no_crm_e_atualizado():
    falso = HubSpotFalso()
    falso.objetos["contacts"]["7"] = {"email": "ana@lumen.example", "firstname": "Ana (cadastro antigo)"}
    lead = lead_lumen()
    _hubspot(falso).sincronizar(lead)
    assert lead.crm["contato_id"] == "7"
    assert falso.objetos["contacts"]["7"]["firstname"] == "Ana"


def test_sem_funil_proprio_usa_o_funil_padrao():
    falso = HubSpotFalso(com_funil_proprio=False)
    lead = lead_lumen(faixa="self_service")
    _hubspot(falso).sincronizar(lead)
    negocio = falso.objetos["deals"][lead.crm["negocio_id"]]
    assert (negocio["pipeline"], negocio["dealstage"]) == ("default", "qualifiedtobuy")


def test_configurar_e_idempotente():
    falso = HubSpotFalso(com_funil_proprio=False)
    hubspot = _hubspot(falso)
    primeira = hubspot.configurar()
    segunda = hubspot.configurar()
    assert "funil: 'BRAX Inbound' criado" in primeira
    assert "funil: 'BRAX Inbound' já existia" in segunda
    assert all("já existia" in linha for linha in segunda)


def test_hubspot_fora_do_ar_nao_derruba_a_conversa():
    lead = lead_lumen()
    assert sincronizar_com_seguranca(_hubspot(HubSpotFalso(cair=True)), lead) is False
    assert lead.crm["pendente"] is True
    assert lead.eventos[-1]["tipo"] == "crm_erro"
    assert sincronizar_com_seguranca(None, lead) is False  # sem CRM configurado: nada acontece


def test_agente_sincroniza_depois_de_cada_resposta(tmp_path):
    from anthropic.types import Message, TextBlock, Usage

    from brax_sdr.agente import Agente

    class Cliente:
        def __init__(self):
            self.messages = self

        def create(self, **kwargs):
            return Message(id="x", type="message", role="assistant", model="claude-haiku-4-5", stop_reason="end_turn",
                           stop_sequence=None, usage=Usage(input_tokens=1, output_tokens=1),
                           content=[TextBlock(type="text", text="Oi! Aqui é o P.H., assistente virtual da BRAX. Qual o nome da empresa?")])

    falso = HubSpotFalso()
    Agente(client=Cliente(), pasta_leads=tmp_path, crm=_hubspot(falso)).responder("ana@lumen.example", "oi", canal="email")
    salvo = memoria.carregar("ana@lumen.example", pasta=tmp_path)
    assert salvo.crm["contato_id"] in falso.objetos["contacts"]  # ids guardados na memória do lead
    assert falso.objetos["deals"] == {}  # ainda sem faixa: sem negócio
