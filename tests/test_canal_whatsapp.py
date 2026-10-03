"""Testes do canal de WhatsApp: formato da Meta, assinatura, avisos repetidos e servidor do webhook.

Nada aqui chama a Meta nem a Anthropic: o servidor é exercitado com o cliente de teste da FastAPI.
"""

import json

import pytest
from anthropic.types import Message, TextBlock, Usage
from fastapi.testclient import TestClient

from brax_sdr import config, memoria
from brax_sdr.agente import Agente
from brax_sdr.canal_whatsapp import EnvioSimulado, RegistroDeMensagens, assinatura, assinatura_valida, ler_webhook
from brax_sdr.simulador_whatsapp import montar_aviso
from brax_sdr.webhook_whatsapp import criar_app

SEGREDO = "segredo-de-teste"
TELEFONE = "5511900000001"


@pytest.fixture(autouse=True)
def configuracao(monkeypatch):
    monkeypatch.setattr(config, "WHATSAPP_APP_SECRET", SEGREDO)
    monkeypatch.setattr(config, "WHATSAPP_VERIFY_TOKEN", "token-verificacao")


# --- Assinatura ---

def test_assinatura_confere_corpo_e_segredo():
    corpo = b'{"oi": 1}'
    assert assinatura_valida(corpo, assinatura(corpo, SEGREDO), SEGREDO)
    assert not assinatura_valida(corpo, assinatura(corpo, "outro-segredo"), SEGREDO)
    assert not assinatura_valida(b'{"oi": 2}', assinatura(corpo, SEGREDO), SEGREDO)  # corpo alterado
    assert not assinatura_valida(corpo, None, SEGREDO)
    assert not assinatura_valida(corpo, assinatura(corpo, ""), "")  # sem segredo configurado, nada passa


# --- Leitura do formato da Meta ---

def test_le_texto_telefone_e_nome():
    [msg] = ler_webhook(montar_aviso(TELEFONE, "Ana Souza", "text", {"body": "Oi, quero o cartão"}, "wamid.1"))
    assert (msg.id, msg.telefone, msg.nome_perfil, msg.texto) == ("wamid.1", TELEFONE, "Ana Souza", "Oi, quero o cartão")


@pytest.mark.parametrize(
    ("tipo", "conteudo", "trecho"),
    [
        ("audio", {"id": "m"}, "não ouve áudios"),
        ("image", {"id": "m", "caption": "Segue meu RG"}, "Segue meu RG\n[O lead enviou uma imagem. Arquivos não são abertos"),
        ("document", {"id": "m", "filename": "contrato.pdf"}, "documentos só pelo app oficial"),
        ("location", {"latitude": 1}, "do tipo location"),
    ],
)
def test_mensagens_que_nao_sao_texto_viram_aviso_para_o_ph(tipo, conteudo, trecho):
    [msg] = ler_webhook(montar_aviso(TELEFONE, "Ana", tipo, conteudo))
    assert trecho in msg.texto
    assert "contrato.pdf" not in msg.texto  # nome de arquivo não chega ao modelo


def test_reacoes_e_avisos_de_status_sao_ignorados():
    assert ler_webhook(montar_aviso(TELEFONE, "Ana", "reaction", {"emoji": "👍"})) == []
    status = {"entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.1", "status": "read"}]}}]}]}
    assert ler_webhook(status) == []


def test_registro_ignora_ids_repetidos(tmp_path):
    registro = RegistroDeMensagens(pasta=tmp_path)
    assert registro.marcar_se_novo("wamid.1") is True
    assert registro.marcar_se_novo("wamid.1") is False
    assert RegistroDeMensagens(pasta=tmp_path).marcar_se_novo("wamid.1") is False  # vale depois de reiniciar


# --- Servidor do webhook ---

class ClienteFalso:
    def __init__(self, textos):
        self.textos, self.chamadas = list(textos), []
        self.messages = self

    def create(self, **kwargs):
        self.chamadas.append(kwargs)
        return Message(id="x", type="message", role="assistant", model="claude-haiku-4-5", stop_reason="end_turn",
                       stop_sequence=None, usage=Usage(input_tokens=1, output_tokens=1),
                       content=[TextBlock(type="text", text=self.textos.pop(0))])


def _servidor(tmp_path, textos):
    cliente = ClienteFalso(textos)
    envio = EnvioSimulado(pasta=tmp_path)
    app = criar_app(Agente(client=cliente, pasta_leads=tmp_path / "leads"), envio, RegistroDeMensagens(pasta=tmp_path))
    return TestClient(app), cliente, envio


def _postar(http, aviso, segredo=SEGREDO):
    corpo = json.dumps(aviso).encode()
    return http.post("/webhook", content=corpo, headers={"X-Hub-Signature-256": assinatura(corpo, segredo)})


def _saida(envio):
    return [json.loads(linha) for linha in envio.arquivo.read_text(encoding="utf-8").splitlines()] if envio.arquivo.exists() else []


def test_verificacao_do_webhook_pela_meta(tmp_path):
    http, _, _ = _servidor(tmp_path, [])
    ok = http.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "token-verificacao", "hub.challenge": "123"})
    assert (ok.status_code, ok.text) == (200, "123")
    errado = http.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "chute", "hub.challenge": "123"})
    assert errado.status_code == 403


def test_mensagem_com_assinatura_falsa_e_recusada_sem_chamar_a_ia(tmp_path):
    http, cliente, envio = _servidor(tmp_path, [])
    resposta = _postar(http, montar_aviso(TELEFONE, "Ana", "text", {"body": "oi"}), segredo="segredo-errado")
    assert resposta.status_code == 403
    assert cliente.chamadas == [] and _saida(envio) == []


def test_mensagem_valida_e_respondida_e_fica_na_memoria(tmp_path):
    http, cliente, envio = _servidor(tmp_path, ["Oi, Ana! Aqui é o P.H., assistente virtual da BRAX. Qual o nome da empresa?"])
    assert _postar(http, montar_aviso(TELEFONE, "Ana Souza", "text", {"body": "Oi, quero o cartão"})).status_code == 200

    assert _saida(envio)[0]["para"] == TELEFONE
    assert _saida(envio)[0]["texto"].startswith("Oi, Ana!")
    lead = memoria.carregar(TELEFONE, pasta=tmp_path / "leads")
    assert lead.canal == "whatsapp"
    assert lead.mensagens[0]["content"].startswith("[Nome no perfil do WhatsApp: Ana Souza]")


def test_aviso_repetido_pela_meta_nao_gera_segunda_resposta(tmp_path):
    http, cliente, envio = _servidor(tmp_path, ["Oi! Aqui é o P.H., assistente virtual da BRAX. Qual o nome da empresa?"])
    aviso = montar_aviso(TELEFONE, "Ana", "text", {"body": "oi"}, "wamid.MESMO")
    _postar(http, aviso)
    assert _postar(http, aviso).status_code == 200  # a Meta precisa receber "ok", senão reenvia de novo
    assert len(cliente.chamadas) == 1 and len(_saida(envio)) == 1


def test_silencio_e_avisado_ao_simulador(tmp_path):
    http, cliente, envio = _servidor(tmp_path, [])
    lead = memoria.carregar(TELEFONE, pasta=tmp_path / "leads")
    lead.opt_out = True
    memoria.salvar(lead, pasta=tmp_path / "leads")
    _postar(http, montar_aviso(TELEFONE, "Ana", "text", {"body": "oi de novo"}))
    assert _saida(envio) == [{"para": TELEFONE, "texto": None, "motivo": "opt_out", "quando": _saida(envio)[0]["quando"]}]
    assert cliente.chamadas == []


def test_regras_do_whatsapp_valem_no_servidor(tmp_path):
    # A reescrita de mensagens longas (decisão 022) vale para o canal WhatsApp também pelo webhook.
    longa = "Oi, Ana! Aqui é o P.H., assistente virtual da BRAX. " + "A BRAX junta conta, cartões e despesas num só lugar. " * 10
    http, cliente, envio = _servidor(tmp_path, [longa, "Oi, Ana! Aqui é o P.H., assistente virtual da BRAX. A BRAX junta conta, cartões e despesas."])
    _postar(http, montar_aviso(TELEFONE, "Ana", "text", {"body": "o que vocês fazem?"}))
    assert len(cliente.chamadas) == 2  # resposta + reescrita
    assert len(_saida(envio)[0]["texto"]) < len(longa)


# --- Envio real (Meta), com a API falsa ---

from brax_sdr.canal_whatsapp import EnvioMeta, numero_brasileiro_com_nono_digito  # noqa: E402


def test_nono_digito_so_para_celular_brasileiro_sem_o_9():
    assert numero_brasileiro_com_nono_digito("551187654321") == "5511987654321"
    assert numero_brasileiro_com_nono_digito("5511987654321") is None  # já tem o 9
    assert numero_brasileiro_com_nono_digito("551132654321") is None  # fixo (começa com 3)
    assert numero_brasileiro_com_nono_digito("14155550123") is None  # não é do Brasil


class _RespostaFalsa:
    def __init__(self, status, corpo):
        self.status_code, self._corpo, self.text = status, corpo, json.dumps(corpo)

    def json(self):
        return self._corpo


def test_envio_tenta_de_novo_com_o_9_quando_a_meta_recusa(monkeypatch):
    destinos = []

    def post_falso(url, headers, json, timeout):
        destinos.append(json["to"])
        if json["to"] == "551187654321":
            return _RespostaFalsa(400, {"error": {"code": 131030, "message": "Recipient phone number not in allowed list"}})
        return _RespostaFalsa(200, {"messages": [{"id": "wamid.ok"}]})

    monkeypatch.setattr("brax_sdr.canal_whatsapp.httpx.post", post_falso)
    EnvioMeta(token="t", numero_id="123").enviar("551187654321", "Oi!")
    assert destinos == ["551187654321", "5511987654321"]


def test_erro_da_meta_aparece_com_o_motivo(monkeypatch):
    monkeypatch.setattr(
        "brax_sdr.canal_whatsapp.httpx.post",
        lambda url, headers, json, timeout: _RespostaFalsa(401, {"error": {"code": 190, "message": "Access token has expired"}}),
    )
    with pytest.raises(RuntimeError, match="Access token has expired"):
        EnvioMeta(token="t", numero_id="123").enviar("5511987654321", "Oi!")
