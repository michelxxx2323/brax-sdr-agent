"""Resumo do lead para o time comercial (Slack e nota no HubSpot), escrito pelo modelo mais forte (decisão 034).

Achado na Fase 4: o resumo escrito pelo P.H. dizia "Ana, parece ser founder/CEO" sem ela ter dito o cargo.
Num resumo para o time, palpite vira informação errada no CRM. Por isso a regra explícita: só fatos ditos.
"""

import anthropic

from brax_sdr import config
from brax_sdr.memoria import Lead

INSTRUCOES = (
    "Você resume conversas de pré-vendas da BRAX (conta PJ, cartões corporativos e gestão de despesas para startups) "
    "para o executivo que vai assumir o lead. Escreva em português do Brasil, em até 6 linhas curtas, sem markdown:\n"
    "1. Quem é e qual empresa (com tamanho e gasto mensal, se informados).\n"
    "2. A dor ou o motivo do contato.\n"
    "3. Solução atual e sinais de compra, se houver.\n"
    "4. Disponibilidade ou próximo passo combinado.\n"
    "Use só fatos ditos pelo lead na conversa. Se um dado não foi informado, escreva \"não informado\". "
    "Nunca suponha cargo, gênero, intenção ou qualquer dado que o lead não disse."
)


def _transcricao(lead: Lead) -> str:
    linhas = []
    for mensagem in lead.mensagens:
        conteudo = mensagem["content"]
        textos = [conteudo] if isinstance(conteudo, str) else [b["text"] for b in conteudo if b.get("type") == "text"]
        quem = "Lead" if mensagem["role"] == "user" else "P.H."
        linhas += [f"{quem}: {t}" for t in textos if t.strip()]
    return "\n".join(linhas)


def resumo_sem_ia(lead: Lead) -> str:
    """Alternativa determinística (se a chamada ao modelo falhar): só os dados registrados."""
    d = lead.dados
    gasto = f"R$ {d['gasto_mensal']:,.0f}".replace(",", ".") + "/mês" if d.get("gasto_mensal") else "não informado"
    return "\n".join([
        f"{d.get('nome_contato') or 'Nome não informado'} · cargo: {d.get('cargo') or 'não informado'}",
        f"{d.get('empresa') or 'Empresa não informada'} · {d.get('funcionarios') or '?'} pessoas · gasto {gasto}",
        f"Dor: {d.get('dor') or 'não informada'}",
        f"Solução atual: {d.get('solucao_atual') or 'não informada'}",
    ])


def gerar_resumo(lead: Lead, disponibilidade: str = "", client: anthropic.Anthropic | None = None) -> str:
    try:
        client = client or anthropic.Anthropic()
        resposta = client.messages.create(
            model=config.MODELO_AVANCADO,
            max_tokens=2048,
            thinking={"type": "disabled"},  # tarefa curta e objetiva: sem raciocínio estendido (mais barato)
            system=INSTRUCOES,
            messages=[{"role": "user", "content": (
                f"Dados registrados: {lead.dados}\n\nConversa:\n{_transcricao(lead)}"
                # A última mensagem do lead ainda não está no histórico quando o resumo é pedido (achado no teste da Elisa).
                + (f"\n\nDisponibilidade informada pelo lead agora: {disponibilidade}" if disponibilidade else "")
            )}],
        )
        texto = "\n".join(b.text for b in resposta.content if b.type == "text").strip()
        return texto or resumo_sem_ia(lead)
    except Exception:
        return resumo_sem_ia(lead)
