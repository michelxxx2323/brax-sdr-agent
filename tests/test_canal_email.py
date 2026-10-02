"""Testes do canal de e-mail com um Gmail FALSO: nenhuma chamada ao Google nem à Anthropic."""

import base64
import email as email_stdlib
import email.policy

import pytest
from anthropic.types import Message, TextBlock, Usage

from brax_sdr import config, memoria
from brax_sdr.agente import Agente
from brax_sdr.atendente_email import AtendenteEmail
from brax_sdr.canal_email import (
    ASSINATURA,
    limpar_texto,
    ler_mensagem,
    montar_resposta,
    motivo_para_ignorar,
    texto_para_o_agente,
)


def _b64(texto: str) -> str:
    return base64.urlsafe_b64encode(texto.encode("utf-8")).decode()


def mensagem_gmail(id="m1", de="Ana Souza <ana@lumen.example>", assunto="Cartões corporativos", corpo="Oi, quero saber mais.",
                   cabecalhos_extras=None, anexos=(), labels=("INBOX", "UNREAD")):
    cabecalhos = [
        {"name": "From", "value": de},
        {"name": "Subject", "value": assunto},
        {"name": "Message-ID", "value": f"<{id}@mail.example>"},
    ] + [{"name": k, "value": v} for k, v in (cabecalhos_extras or {}).items()]
    partes = [{"mimeType": "text/plain", "body": {"data": _b64(corpo)}}]
    partes += [{"mimeType": "application/pdf", "filename": nome, "body": {"attachmentId": "a1"}} for nome in anexos]
    return {"id": id, "threadId": f"t-{id}", "labelIds": list(labels),
            "payload": {"mimeType": "multipart/mixed", "headers": cabecalhos, "parts": partes}}


@pytest.fixture(autouse=True)
def configuracao_de_teste(monkeypatch):
    monkeypatch.setattr(config, "GMAIL_REMETENTE", "brax@gmail.example")
    monkeypatch.setattr(config, "EMAIL_REMETENTES_PERMITIDOS", set())


# --- Leitura e limpeza ---

def test_le_remetente_assunto_e_texto():
    email = ler_mensagem(mensagem_gmail())
    assert (email.remetente, email.nome_remetente, email.assunto) == ("ana@lumen.example", "Ana Souza", "Cartões corporativos")
    assert email.texto == "Oi, quero saber mais."
    assert email.thread_id == "t-m1"


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("Somos 28 pessoas.\n\nEm qua., 1 de out. de 2026 às 10:00, BRAX <brax@gmail.example> escreveu:\n> Quantas pessoas?", "Somos 28 pessoas."),
        ("We are 28.\n\nOn Wed, Oct 1, 2026 at 10:00 AM BRAX wrote:\n> How many?", "We are 28."),
        ("Gasto uns 70 mil.\n\nDe: BRAX <brax@gmail.example>\nEnviado: quarta\nAssunto: Re: Cartões", "Gasto uns 70 mil."),
        ("Pode ser amanhã.\n\nEnviado do meu iPhone", "Pode ser amanhã."),
        ("Obrigada!\n--\nAna Souza\nCEO | Lumen", "Obrigada!"),
    ],
)
def test_limpeza_tira_citacao_e_assinatura(bruto, esperado):
    assert limpar_texto(bruto) == esperado


def test_email_so_em_html_vira_texto():
    msg = mensagem_gmail()
    msg["payload"]["parts"] = [{"mimeType": "text/html", "body": {"data": _b64("<p>Oi,<br>somos 12 pessoas.</p>")}}]
    assert ler_mensagem(msg).texto == "Oi,\nsomos 12 pessoas."


# --- Filtros ---

@pytest.mark.parametrize(
    ("extras", "de", "motivo"),
    [
        ({"Auto-Submitted": "auto-replied"}, "Ana <ana@lumen.example>", "resposta automática"),
        ({"Precedence": "bulk"}, "Ana <ana@lumen.example>", "envio em massa"),
        ({"List-Unsubscribe": "<mailto:sair@news.example>"}, "News <news@news.example>", "newsletter ou lista de e-mails"),
        ({}, "Sistema <no-reply@banco.example>", "remetente automático"),
        ({}, "BRAX <brax@gmail.example>", "enviado pelo próprio P.H."),
    ],
)
def test_filtros_de_emails_que_nao_devem_ser_respondidos(extras, de, motivo):
    assert motivo_para_ignorar(ler_mensagem(mensagem_gmail(de=de, cabecalhos_extras=extras))) == motivo


def test_lista_de_remetentes_permitidos(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_REMETENTES_PERMITIDOS", {"eu@pessoal.example"})
    assert motivo_para_ignorar(ler_mensagem(mensagem_gmail())) == "remetente fora da lista de permitidos"
    assert motivo_para_ignorar(ler_mensagem(mensagem_gmail(de="Eu <EU@pessoal.example>"))) is None


def test_email_normal_passa_pelos_filtros():
    assert motivo_para_ignorar(ler_mensagem(mensagem_gmail())) is None


def test_anexos_nunca_sao_abertos_e_o_ph_e_avisado():
    email = ler_mensagem(mensagem_gmail(corpo="Segue o contrato social.", anexos=["contrato.pdf"]))
    texto = texto_para_o_agente(email, primeiro_contato=False)
    assert "anexou 1 arquivo(s)" in texto and "não foram abertos" in texto
    assert "contrato.pdf" not in texto  # nem o nome do arquivo chega ao modelo


def test_primeiro_contato_inclui_assunto_e_nome():
    texto = texto_para_o_agente(ler_mensagem(mensagem_gmail()), primeiro_contato=True)
    assert "[Assunto do e-mail: Cartões corporativos]" in texto
    assert "[Nome no remetente: Ana Souza]" in texto


# --- Resposta ---

def _decodificar_resposta(corpo_api: dict) -> email_stdlib.message.Message:
    # policy.default decodifica os cabeçalhos como um leitor de e-mail faria ("Cartões", não =?utf-8?q?...)
    return email_stdlib.message_from_bytes(base64.urlsafe_b64decode(corpo_api["raw"]), policy=email_stdlib.policy.default)


def test_resposta_vai_na_mesma_thread_com_assinatura():
    recebido = ler_mensagem(mensagem_gmail())
    corpo_api = montar_resposta(recebido, "Oi, Ana! Quantas pessoas trabalham na Lumen?\n\nAbraço,")
    assert corpo_api["threadId"] == "t-m1"
    enviado = _decodificar_resposta(corpo_api)
    assert enviado["To"] == "ana@lumen.example"
    assert enviado["Subject"] == "Re: Cartões corporativos"
    assert enviado["In-Reply-To"] == "<m1@mail.example>"
    texto = enviado.get_payload(decode=True).decode("utf-8")
    assert texto.endswith(f"Abraço,\n{ASSINATURA}")


def test_assunto_e_assinatura_escritos_pelo_modelo_sao_removidos():
    # O modelo imita os exemplos do cérebro, que mostram assunto e assinatura.
    escrito = "Assunto: Re: Cartões\n\nOi, Ana!\n\nAbraço,\nP.H. · Assistente virtual da BRAX"
    texto = _decodificar_resposta(montar_resposta(ler_mensagem(mensagem_gmail()), escrito)).get_payload(decode=True).decode("utf-8")
    assert not texto.startswith("Assunto")
    assert texto.count("Assistente virtual da BRAX") == 1


# --- Atendente com Gmail falso ---

class _Chamada:
    def __init__(self, resultado):
        self.resultado = resultado

    def execute(self):
        return self.resultado


class GmailFalso:
    """Imita servico.users().messages()/labels() o suficiente para o atendente."""

    def __init__(self, mensagens):
        self.mensagens = {m["id"]: m for m in mensagens}
        self.enviadas = []
        self.etiquetas = []

    def users(self):
        return self

    def messages(self):
        return self

    def labels(self):
        return _Etiquetas(self)

    def list(self, userId, q, maxResults):
        return _Chamada({"messages": [{"id": i} for i in reversed(list(self.mensagens))]})

    def get(self, userId, id, format):
        return _Chamada(self.mensagens[id])

    def modify(self, userId, id, body):
        self.mensagens[id]["labelIds"] += body["addLabelIds"]
        return _Chamada({})

    def send(self, userId, body):
        self.enviadas.append(body)
        return _Chamada({"id": "enviado"})


class _Etiquetas:
    def __init__(self, gmail):
        self.gmail = gmail

    def list(self, userId):
        return _Chamada({"labels": self.gmail.etiquetas})

    def create(self, userId, body):
        nova = {"id": "Label_1", "name": body["name"]}
        self.gmail.etiquetas.append(nova)
        return _Chamada(nova)


class ClienteFalso:
    def __init__(self, textos):
        self.textos, self.chamadas = list(textos), []
        self.messages = self

    def create(self, **kwargs):
        self.chamadas.append(kwargs)
        return Message(id="x", type="message", role="assistant", model="claude-haiku-4-5",
                       content=[TextBlock(text=self.textos.pop(0), type="text")], stop_reason="end_turn",
                       stop_sequence=None, usage=Usage(input_tokens=10, output_tokens=5))


def test_atendente_responde_na_thread_e_etiqueta(tmp_path):
    gmail = GmailFalso([mensagem_gmail()])
    cliente = ClienteFalso(["Oi, Ana! Aqui é o P.H., assistente virtual da BRAX. Quantas pessoas trabalham na Lumen?"])
    atendente = AtendenteEmail(gmail, Agente(client=cliente, pasta_leads=tmp_path))

    assert atendente.processar("m1") == "respondido"
    assert gmail.enviadas[0]["threadId"] == "t-m1"
    assert "Label_1" in gmail.mensagens["m1"]["labelIds"]
    assert gmail.etiquetas[0]["name"] == config.GMAIL_ETIQUETA_PROCESSADO
    lead = memoria.carregar("ana@lumen.example", pasta=tmp_path)
    assert lead.canal == "email"
    assert "[Assunto do e-mail: Cartões corporativos]" in lead.mensagens[0]["content"]


def test_email_ja_processado_nao_e_respondido_de_novo(tmp_path):
    gmail = GmailFalso([mensagem_gmail()])
    atendente = AtendenteEmail(gmail, Agente(client=ClienteFalso(["Olá! Sou o P.H., assistente virtual."]), pasta_leads=tmp_path))
    atendente.processar("m1")
    assert atendente.processar("m1") == "já processado"
    assert len(gmail.enviadas) == 1


def test_resposta_automatica_e_ignorada_sem_chamar_a_ia(tmp_path):
    gmail = GmailFalso([mensagem_gmail(cabecalhos_extras={"Auto-Submitted": "auto-replied"})])
    cliente = ClienteFalso([])
    resultado = AtendenteEmail(gmail, Agente(client=cliente, pasta_leads=tmp_path)).processar("m1")
    assert resultado == "ignorado (resposta automática)"
    assert cliente.chamadas == [] and gmail.enviadas == []
    assert "Label_1" in gmail.mensagens["m1"]["labelIds"]  # etiquetado para não ser lido de novo


def test_email_no_estilo_de_email_nao_e_encurtado(tmp_path):
    # Respostas longas são normais no e-mail: a reescrita (decisão 022) vale só para o WhatsApp.
    longo = "Oi, Ana! Aqui é o P.H., assistente virtual da BRAX. " + "A BRAX junta conta PJ, cartões e despesas. " * 12
    cliente = ClienteFalso([longo])
    AtendenteEmail(GmailFalso([mensagem_gmail()]), Agente(client=cliente, pasta_leads=tmp_path)).processar("m1")
    assert len(cliente.chamadas) == 1


def test_lead_que_veio_do_whatsapp_responde_no_estilo_do_canal_atual(tmp_path):
    lead = memoria.carregar("ana@lumen.example", canal="whatsapp", pasta=tmp_path)
    lead.mensagens = [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "Oi! Sou o P.H., assistente virtual."}]
    memoria.salvar(lead, pasta=tmp_path)
    cliente = ClienteFalso(["Oi, Ana! Seguimos por e-mail então."])
    AtendenteEmail(GmailFalso([mensagem_gmail()]), Agente(client=cliente, pasta_leads=tmp_path)).processar("m1")
    assert memoria.carregar("ana@lumen.example", pasta=tmp_path).canal == "email"


# --- Achado no 1º teste real de e-mail: o lead recebeu só "Abraço, P.H." ---

def test_texto_antes_do_registro_de_dados_nao_se_perde(tmp_path):
    # O modelo escreveu o e-mail inteiro ANTES de registrar os dados e, depois, só a despedida.
    from anthropic.types import ToolUseBlock

    class ClienteEmDuasRodadas(ClienteFalso):
        def __init__(self):
            super().__init__([])
            self.respostas = [
                Message(id="a", type="message", role="assistant", model="claude-haiku-4-5", stop_reason="tool_use",
                        stop_sequence=None, usage=Usage(input_tokens=10, output_tokens=5), content=[
                            TextBlock(type="text", text="Oi, Paulo,\n\nAqui é o P.H., assistente virtual da BRAX. "
                                                        "Quanto a Nuvia gasta por mês com cartão?\n\nAbraço,\nP.H. · Assistente virtual da BRAX"),
                            ToolUseBlock(type="tool_use", id="t1", name="registrar_qualificacao", input={"funcionarios": 8}),
                        ]),
                Message(id="b", type="message", role="assistant", model="claude-haiku-4-5", stop_reason="end_turn",
                        stop_sequence=None, usage=Usage(input_tokens=10, output_tokens=5),
                        content=[TextBlock(type="text", text="Abraço,\nP.H. · Assistente virtual da BRAX")]),
            ]

        def create(self, **kwargs):
            self.chamadas.append(kwargs)
            return self.respostas.pop(0)

    gmail = GmailFalso([mensagem_gmail()])
    AtendenteEmail(gmail, Agente(client=ClienteEmDuasRodadas(), pasta_leads=tmp_path)).processar("m1")
    texto = _decodificar_resposta(gmail.enviadas[0]).get_content()
    assert "Quanto a Nuvia gasta por mês com cartão?" in texto
    assert texto.count("Abraço,") == 1
    assert texto.count("Assistente virtual da BRAX") == 1
    assert texto.rstrip().endswith(f"Abraço,\n{ASSINATURA}")


def test_corpo_remove_assinatura_curta_e_fecho_repetido():
    escrito = "Oi, Ana!\n\nAbraço,\nP.H.\n\nAbraço,\nP.H. - BRAX"
    texto = _decodificar_resposta(montar_resposta(ler_mensagem(mensagem_gmail()), escrito)).get_content()
    assert texto.rstrip() == f"Oi, Ana!\n\nAbraço,\n{ASSINATURA}"
