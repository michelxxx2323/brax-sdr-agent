"""Follow-up: lembretes quando o lead para de responder (decisão 028).

Regras e textos ficam no código: são previsíveis, não custam tokens e não correm risco de vazamento
(mesmo raciocínio da recusa padronizada, decisão 023).
"""

from datetime import datetime, timedelta, timezone

from brax_sdr import config
from brax_sdr.memoria import Lead

BRASILIA = timezone(timedelta(hours=-3))  # sem horário de verão desde 2019


def somar_dias_uteis(inicio: datetime, dias: int) -> datetime:
    """Mesmo horário, `dias` dias úteis depois (sábados e domingos não contam; feriados ainda não)."""
    data = inicio
    while dias > 0:
        data += timedelta(days=1)
        if data.weekday() < 5:
            dias -= 1
    return data


def em_horario_comercial(momento: datetime) -> bool:
    local = momento.astimezone(BRASILIA)
    inicio, fim = config.FOLLOWUP_HORARIO_COMERCIAL
    return local.weekday() < 5 and inicio <= local.hour < fim


def numero_do_followup_devido(lead: Lead, agora: datetime) -> int | None:
    """Qual lembrete (1 ou 2) este lead deve receber agora, ou None. Todas as travas ficam aqui."""
    if lead.opt_out or lead.encerrada or lead.bloqueio or lead.sem_resposta or lead.atendimento_humano or lead.transferido_para_vendedor:
        return None
    if lead.faixa == "fora_do_icp" or not lead.aguardando_lead or not lead.ultima_resposta_em:
        return None
    if lead.canal != "email" or not lead.email_contexto:
        return None  # por enquanto só e-mail; o WhatsApp tem regras próprias da Meta (Fase 4)
    numero = lead.followups_enviados + 1
    if numero > len(config.FOLLOWUP_ESPERAS_DIAS_UTEIS):
        return None

    ultima = datetime.fromisoformat(lead.ultima_resposta_em)
    espera = config.FOLLOWUP_ESPERAS_DIAS_UTEIS[numero - 1]
    if config.FOLLOWUP_MINUTOS_TESTE:
        prazo = ultima + timedelta(minutes=espera * config.FOLLOWUP_MINUTOS_TESTE)
    else:
        if not em_horario_comercial(agora):
            return None
        prazo = somar_dias_uteis(ultima, espera)
    return numero if agora >= prazo else None


def texto_do_followup(numero: int, lead: Lead) -> str:
    nome = lead.primeiro_nome()
    empresa = lead.dados.get("empresa")
    saudacao = f"Oi, {nome}!" if nome else "Oi!"
    if numero == 1:
        assunto = f"os cartões corporativos da {empresa}" if empresa else "a BRAX"
        return f"{saudacao} Passando para saber se ainda faz sentido conversarmos sobre {assunto}. É só responder por aqui."
    return (
        f"{saudacao} Como não tivemos retorno, vou deixar nossa conversa em pausa. Se quiser retomar, é só responder "
        "este e-mail. E se não for o momento, sem problema: me avise que eu não envio mais mensagens."
    )


def registrar_followup(lead: Lead, numero: int, texto: str, agora: datetime) -> None:
    """Anota o lembrete na memória (o P.H. vê no histórico se o lead voltar a responder)."""
    lead.followups_enviados = numero
    lead.ultima_resposta_em = agora.isoformat(timespec="seconds")
    lead.mensagens.append({"role": "assistant", "content": texto})
    lead.registrar_evento("followup", f"lembrete {numero}")
    if numero >= len(config.FOLLOWUP_ESPERAS_DIAS_UTEIS):
        lead.sem_resposta, lead.aguardando_lead = True, False
        lead.registrar_evento("sem_resposta", f"{numero} lembretes sem retorno")
