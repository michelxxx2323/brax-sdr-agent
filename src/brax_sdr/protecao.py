"""Proteção de custo e encerramento de conversa (decisão 021).

Tudo aqui roda ANTES de chamar a API: quando uma regra dispara, a resposta
é uma mensagem fixa (ou silêncio) e nenhum token é gasto.
"""

import re
import unicodedata
from datetime import date
from difflib import get_close_matches

from brax_sdr import config
from brax_sdr.memoria import Lead

MENSAGEM_LIMITE_DIARIO = (
    "Recebi muitas mensagens por hoje. Para te atender melhor, uma pessoa do time vai continuar a conversa por aqui."
)
MENSAGEM_LIMITE_CUSTO = "Para seguir com o seu atendimento, uma pessoa do nosso time vai continuar a conversa por aqui."
MENSAGEM_TEXTO_LONGO = "Sua mensagem ficou bem longa. Consegue me resumir em poucas linhas o que você precisa?"

# Palavras que, sozinhas, formam uma despedida ou agradecimento. Saudações ("bom dia") ficam de fora:
# podem ser o começo de uma conversa nova.
_PALAVRAS_DE_DESPEDIDA = {
    "tchau", "tchauzinho", "valeu", "vlw", "obrigado", "obrigada", "obg", "brigado", "brigada", "grato", "grata",
    "tmj", "tamo", "junto", "e", "nois", "falou", "flw", "abs", "abraco", "abracos", "ate", "mais", "logo",
    "ok", "okay", "blz", "beleza", "show", "top", "perfeito", "perfeita", "combinado", "fechado", "certo",
    "muito", "de", "nada", "joia", "otimo", "otima", "legal", "kk", "kkk", "kkkk", "haha", "rs", "entao",
    # Achado no teste "mei3": "entendi. obrigado" reabriu a conversa.
    # ("bom" e "dia" ficam de fora: "Bom dia" pode abrir uma conversa nova.)
    "entendi", "entendido", "entendo", "compreendi", "ta", "ah", "sim", "pode", "deixa", "deixar", "tranquilo",
    "obrigadao", "valeuzao", "bjs", "beijos", "abracao",
}


_PALAVRAS_LONGAS = [p for p in _PALAVRAS_DE_DESPEDIDA if len(p) >= 5]


def _sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _palavra_de_despedida(palavra: str) -> bool:
    if palavra in _PALAVRAS_DE_DESPEDIDA:
        return True
    # Tolera erro de digitação em palavras longas (achado no teste "mei4": "Entedi, Obrigado").
    return len(palavra) >= 5 and bool(get_close_matches(palavra, _PALAVRAS_LONGAS, n=1, cutoff=0.85))


def eh_despedida(texto: str) -> bool:
    """Verdadeiro para mensagens curtas feitas só de despedida, agradecimento ou emojis."""
    if len(texto) > 60:
        return False
    palavras = re.findall(r"[a-z]+", _sem_acentos(texto.lower()))
    return all(_palavra_de_despedida(p) for p in palavras)  # só emojis/pontuação também conta


# Pedido explícito para falar com uma pessoa (guardrail G4: transferir sempre). Achado no teste do Fabio: ele pediu duas
# vezes e o modelo seguiu qualificando ("antes de eu te conectar, deixa eu entender melhor...").
_PEDE_HUMANO = re.compile(
    r"\b(falar|conversar|atendimento|atender|passa|passe|transfere|transfira)\b[^.?!\n]{0,30}"
    r"\b(pessoa|humano|humana|atendente|algu[ée]m de verdade|algu[ée]m real|ser humano|gente de verdade)\b"
    r"|\bpessoa (real|de verdade)\b|\batendente humano\b|\bn[ãa]o quero (falar com )?(rob[ôo]|bot|ia|m[áa]quina)\b",
    re.IGNORECASE,
)


def pede_humano(texto: str) -> bool:
    return bool(_PEDE_HUMANO.search(texto))


def verificar_antes_da_api(lead: Lead, texto: str) -> tuple[str, str | None] | None:
    """Aplica as regras de proteção a uma mensagem recebida.

    Devolve None se a mensagem pode seguir para o modelo. Caso contrário, devolve
    (motivo, resposta_fixa), com resposta_fixa None quando o P.H. deve ficar em silêncio.
    """
    # 1. Limite de custo por lead: avisa uma vez e passa para humano.
    if lead.bloqueio:
        return lead.bloqueio, None
    if lead.custo_total_usd >= config.LIMITE_CUSTO_POR_LEAD_USD:
        lead.bloqueio = "limite_de_custo"
        lead.registrar_evento("transferencia_humano", f"limite de custo atingido (US$ {lead.custo_total_usd:.2f})")
        return "limite_de_custo", MENSAGEM_LIMITE_CUSTO

    # 2. Limite de mensagens por dia: avisa uma vez por dia, depois silêncio até o dia seguinte.
    hoje = date.today().isoformat()
    if lead.mensagens_hoje.get("data") != hoje:
        lead.mensagens_hoje = {"data": hoje, "total": 0, "avisado": False}
    lead.mensagens_hoje["total"] += 1
    if lead.mensagens_hoje["total"] > config.LIMITE_MENSAGENS_POR_DIA:
        if lead.mensagens_hoje["avisado"]:
            return "limite_diario", None
        lead.mensagens_hoje["avisado"] = True
        lead.registrar_evento("transferencia_humano", "limite de mensagens por dia atingido")
        return "limite_diario", MENSAGEM_LIMITE_DIARIO

    # 3. Conversa encerrada: despedidas não recebem resposta; qualquer outra coisa reabre.
    if lead.encerrada:
        if eh_despedida(texto):
            return "conversa_encerrada", None
        lead.encerrada = False
        lead.dados.pop("motivo_encerramento", None)  # conversa nova: o motivo antigo deixa de valer
        lead.registrar_evento("conversa_reaberta", texto[:80])

    # 4. Mensagem longa demais: pede um resumo sem gastar tokens.
    if len(texto) > config.LIMITE_CARACTERES_MENSAGEM:
        return "mensagem_longa", MENSAGEM_TEXTO_LONGO

    return None
