"""Checagem automática das respostas do P.H. antes do envio.

Fase 2: só ALERTA (registra no histórico e mostra no terminal), porque regras
por palavra-chave têm falsos positivos. Na Fase 6, um LLM juiz avalia cada
guardrail com mais precisão. Os códigos G1-G4 seguem cerebro/regras/guardrails.md;
os alertas "Estilo" seguem cerebro/voz/tom-de-voz.md; os de "Confiabilidade"
pegam afirmações sem base em ferramenta (ex.: "o time confirmou" sem aprovação).
"""

import re

_LIMITE_COM_VALOR = re.compile(r"limite[^.\n]{0,60}R\$\s*\d", re.IGNORECASE)
_RENDIMENTO_PERCENTUAL = re.compile(r"rend\w*[^.\n]{0,60}\d+(?:[.,]\d+)?\s*%", re.IGNORECASE)
_PEDIDO_DADO_SENSIVEL = re.compile(
    r"\b(me\s+(?:envi|mand|pass)\w*|(?:pode|poderia)\s+(?:me\s+)?(?:envi|mand|pass)\w*|informe|digite)"
    r"[^.\n]{0,40}\b(senha|c[óo]digo|cpf|rg|contrato social|documento|n[úu]mero do cart[ãa]o|cvv)",
    re.IGNORECASE,
)


LIMITE_CARACTERES_WHATSAPP = 400  # o tom de voz pede ~300; a folga evita alertas por pouco


def checar_resposta(texto: str, primeira_mensagem: bool, canal: str = "whatsapp") -> list[str]:
    alertas = []
    if canal == "whatsapp":
        if len(texto) > LIMITE_CARACTERES_WHATSAPP:
            alertas.append(f"Estilo: mensagem longa para WhatsApp ({len(texto)} caracteres)")
        if "**" in texto:
            alertas.append("Estilo: markdown (**) no WhatsApp")
    if _LIMITE_COM_VALOR.search(texto):
        alertas.append("G1: possível valor de limite informado")
    if _PEDIDO_DADO_SENSIVEL.search(texto):
        alertas.append("G2: possível pedido de dado sensível")
    if _RENDIMENTO_PERCENTUAL.search(texto):
        alertas.append("G3: possível rendimento com percentual")
    if primeira_mensagem and "assistente virtual" not in texto.lower():
        alertas.append("G4: primeira mensagem sem identificação como assistente virtual")
    return alertas


# --- Confiabilidade: o P.H. não pode afirmar o que não aconteceu (achado no teste "lumen2") ---

_AFIRMA_CONFIRMACAO = re.compile(
    r"\b(time|equipe)\b[^.\n]{0,30}\b(confirmou|aprovou|agendou)\b|\best[áa] (fechado|confirmado|agendado)\b",
    re.IGNORECASE,
)
_TEXTO_DE_EXEMPLO = re.compile(r"\[[^\]]{0,60}\b(link|url|inserir|nome)\b[^\]]{0,60}\]", re.IGNORECASE)
_PROMETE_ACAO_FUTURA = re.compile(
    r"\bvou (confirmar|verificar|checar|consultar)\b|\bum momentinho\b|\bte (mando|envio|passo)\b[^.\n]{0,40}\bem seguida\b",
    re.IGNORECASE,
)


def checar_confiabilidade(texto: str, ferramentas_usadas: list[str]) -> list[str]:
    alertas = []
    if _AFIRMA_CONFIRMACAO.search(texto) and "solicitar_aprovacao_executivo" not in ferramentas_usadas:
        alertas.append("Confiabilidade: afirma confirmação do time sem ter pedido aprovação nesta resposta")
    if _TEXTO_DE_EXEMPLO.search(texto):
        alertas.append("Confiabilidade: texto de exemplo entre colchetes (ex.: [link])")
    if _PROMETE_ACAO_FUTURA.search(texto) and not ferramentas_usadas:
        alertas.append("Confiabilidade: promete uma ação para depois sem ter chamado nenhuma ferramenta")
    return alertas


def tipo_de_evento(alerta: str) -> str:
    """Nome do evento registrado na memória do lead para cada tipo de alerta."""
    if alerta.startswith("Estilo"):
        return "alerta_estilo"
    if alerta.startswith("Confiabilidade"):
        return "alerta_confiabilidade"
    return "alerta_guardrail"
