"""Checagem automática das respostas do P.H. antes do envio.

Fase 2: só ALERTA (registra no histórico e mostra no terminal), porque regras
por palavra-chave têm falsos positivos. Na Fase 6, um LLM juiz avalia cada
guardrail com mais precisão. Os códigos G1-G4 seguem cerebro/regras/guardrails.md.
"""

import re

_LIMITE_COM_VALOR = re.compile(r"limite[^.\n]{0,60}R\$\s*\d", re.IGNORECASE)
_RENDIMENTO_PERCENTUAL = re.compile(r"rend\w*[^.\n]{0,60}\d+(?:[.,]\d+)?\s*%", re.IGNORECASE)
_PEDIDO_DADO_SENSIVEL = re.compile(
    r"\b(me\s+(?:envi|mand|pass)\w*|(?:pode|poderia)\s+(?:me\s+)?(?:envi|mand|pass)\w*|informe|digite)"
    r"[^.\n]{0,40}\b(senha|c[óo]digo|cpf|rg|contrato social|documento|n[úu]mero do cart[ãa]o|cvv)",
    re.IGNORECASE,
)


def checar_resposta(texto: str, primeira_mensagem: bool) -> list[str]:
    alertas = []
    if _LIMITE_COM_VALOR.search(texto):
        alertas.append("G1: possível valor de limite informado")
    if _PEDIDO_DADO_SENSIVEL.search(texto):
        alertas.append("G2: possível pedido de dado sensível")
    if _RENDIMENTO_PERCENTUAL.search(texto):
        alertas.append("G3: possível rendimento com percentual")
    if primeira_mensagem and "assistente virtual" not in texto.lower():
        alertas.append("G4: primeira mensagem sem identificação como assistente virtual")
    return alertas
