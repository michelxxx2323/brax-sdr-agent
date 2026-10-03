"""Testes do follow-up (decisão 028). Nenhum chama o Google nem a Anthropic."""

import base64
import email as email_stdlib
import email.policy
from datetime import datetime, timedelta, timezone

import pytest

from brax_sdr import config, memoria
from brax_sdr.agente import Agente
from brax_sdr.atendente_email import AtendenteEmail
from brax_sdr.followup import (
    BRASILIA,
    em_horario_comercial,
    numero_do_followup_devido,
    registrar_followup,
    somar_dias_uteis,
    texto_do_followup,
)
from brax_sdr.memoria import Lead

# Quarta-feira, 10h em Brasília.
QUARTA_10H = datetime(2026, 9, 30, 10, 0, tzinfo=BRASILIA)


@pytest.fixture(autouse=True)
def sem_modo_de_teste(monkeypatch):
    monkeypatch.setattr(config, "FOLLOWUP_MINUTOS_TESTE", 0)
    monkeypatch.setattr(config, "GMAIL_REMETENTE", "brax@gmail.example")


def lead_esperando(ultima=QUARTA_10H, **mudancas) -> Lead:
    lead = Lead(
        id="ana@lumen.example", canal="email", aguardando_lead=True,
        ultima_resposta_em=ultima.isoformat(), dados={"nome_contato": "Ana", "empresa": "Lumen"},
        email_contexto={"thread_id": "t1", "message_id": "<m1@x>", "referencias": "", "assunto": "Cartões",
                        "remetente": "ana@lumen.example"},
    )
    for campo, valor in mudancas.items():
        setattr(lead, campo, valor)
    return lead


# --- Calendário ---

def test_dias_uteis_pulam_o_fim_de_semana():
    sexta = datetime(2026, 10, 2, 10, 0, tzinfo=BRASILIA)
    assert somar_dias_uteis(sexta, 1).weekday() == 0  # segunda
    assert somar_dias_uteis(sexta, 3).date() == datetime(2026, 10, 7).date()  # quarta seguinte


def test_horario_comercial_de_brasilia():
    assert em_horario_comercial(QUARTA_10H)
    assert not em_horario_comercial(QUARTA_10H.replace(hour=20))
    assert not em_horario_comercial(datetime(2026, 10, 3, 10, 0, tzinfo=BRASILIA))  # sábado
    # 12h UTC = 9h em Brasília: já é horário comercial.
    assert em_horario_comercial(datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc))


# --- Quando dispara ---

def test_cadencia_primeiro_depois_segundo_depois_para():
    lead = lead_esperando()
    assert numero_do_followup_devido(lead, QUARTA_10H + timedelta(hours=23)) is None  # ainda não passou 1 dia útil
    quinta = QUARTA_10H + timedelta(days=1)
    assert numero_do_followup_devido(lead, quinta) == 1

    registrar_followup(lead, 1, texto_do_followup(1, lead), quinta)
    assert numero_do_followup_devido(lead, quinta + timedelta(days=1)) is None  # 2º só 3 dias úteis depois
    terca = datetime(2026, 10, 6, 10, 0, tzinfo=BRASILIA)  # quinta + 3 dias úteis (sex, seg, ter)
    assert numero_do_followup_devido(lead, terca) == 2

    registrar_followup(lead, 2, texto_do_followup(2, lead), terca)
    assert lead.sem_resposta is True
    assert numero_do_followup_devido(lead, terca + timedelta(days=30)) is None  # nunca um 3º


@pytest.mark.parametrize(
    ("mudanca", "motivo"),
    [
        ({"opt_out": True}, "pediu para parar"),
        ({"encerrada": True}, "conversa encerrada"),
        ({"bloqueio": "limite_de_custo"}, "bloqueado por custo"),
        ({"faixa": "fora_do_icp"}, "fora do perfil"),
        ({"aguardando_lead": False}, "o P.H. não fez pergunta"),
        ({"canal": "whatsapp"}, "WhatsApp fica para a Fase 4"),
        ({"email_contexto": {}}, "sem thread para responder"),
    ],
)
def test_travas_do_followup(mudanca, motivo):
    assert numero_do_followup_devido(lead_esperando(**mudanca), QUARTA_10H + timedelta(days=2)) is None, motivo


def test_fora_do_horario_comercial_espera(monkeypatch):
    sabado = datetime(2026, 10, 3, 10, 0, tzinfo=BRASILIA)
    assert numero_do_followup_devido(lead_esperando(), sabado) is None


def test_modo_de_teste_usa_minutos_e_ignora_horario(monkeypatch):
    monkeypatch.setattr(config, "FOLLOWUP_MINUTOS_TESTE", 1)
    meia_noite = datetime(2026, 10, 4, 0, 0, tzinfo=BRASILIA)  # domingo, de madrugada
    lead = lead_esperando(ultima=meia_noite)
    assert numero_do_followup_devido(lead, meia_noite + timedelta(seconds=30)) is None
    assert numero_do_followup_devido(lead, meia_noite + timedelta(minutes=1)) == 1


# --- Textos ---

def test_textos_usam_nome_e_empresa():
    lead = lead_esperando()
    assert texto_do_followup(1, lead) == (
        "Oi, Ana! Passando para saber se ainda faz sentido conversarmos sobre os cartões corporativos da Lumen. "
        "É só responder por aqui."
    )
    assert "não envio mais mensagens" in texto_do_followup(2, lead)  # o 2º diz como parar
    assert texto_do_followup(1, Lead(id="x")).startswith("Oi! Passando")


# --- De ponta a ponta com Gmail falso ---

class _Chamada:
    def __init__(self, resultado):
        self.resultado = resultado

    def execute(self):
        return self.resultado


class GmailSoEnvio:
    def __init__(self):
        self.enviadas = []

    def users(self):
        return self

    def messages(self):
        return self

    def send(self, userId, body):
        self.enviadas.append(body)
        return _Chamada({"id": "x"})


def test_atendente_envia_lembrete_na_mesma_thread_e_registra(tmp_path):
    memoria.salvar(lead_esperando(), pasta=tmp_path)
    memoria.salvar(lead_esperando(opt_out=True, id="parou@x.example"), pasta=tmp_path)
    gmail = GmailSoEnvio()
    atendente = AtendenteEmail(gmail, Agente(client=object(), pasta_leads=tmp_path))

    assert atendente.enviar_followups(QUARTA_10H + timedelta(days=1)) == ["ana@lumen.example"]
    assert gmail.enviadas[0]["threadId"] == "t1"
    enviado = email_stdlib.message_from_bytes(base64.urlsafe_b64decode(gmail.enviadas[0]["raw"]), policy=email_stdlib.policy.default)
    assert enviado["In-Reply-To"] == "<m1@x>"
    assert enviado.get_content().startswith("Oi, Ana! Passando para saber")
    salvo = memoria.carregar("ana@lumen.example", pasta=tmp_path)
    assert salvo.followups_enviados == 1
    assert salvo.mensagens[-1]["role"] == "assistant"  # o P.H. vê o lembrete no histórico
    # Rodando de novo no mesmo instante, nada sai em dobro.
    assert atendente.enviar_followups(QUARTA_10H + timedelta(days=1)) == []


def test_resposta_do_lead_zera_os_lembretes(tmp_path):
    from anthropic.types import Message, TextBlock, Usage

    class Cliente:
        def __init__(self):
            self.messages = self

        def create(self, **kwargs):
            return Message(id="x", type="message", role="assistant", model="claude-haiku-4-5", stop_reason="end_turn",
                           stop_sequence=None, usage=Usage(input_tokens=1, output_tokens=1),
                           content=[TextBlock(type="text", text="Que bom que voltou, Ana! Quanto a Lumen gasta por mês?")])

    lead = lead_esperando(followups_enviados=2, sem_resposta=True, aguardando_lead=False)
    lead.mensagens = [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "Oi! Sou o P.H., assistente virtual."}]
    memoria.salvar(lead, pasta=tmp_path)
    Agente(client=Cliente(), pasta_leads=tmp_path).responder("ana@lumen.example", "Desculpa a demora!", canal="email")
    salvo = memoria.carregar("ana@lumen.example", pasta=tmp_path)
    assert (salvo.followups_enviados, salvo.sem_resposta, salvo.aguardando_lead) == (0, False, True)
