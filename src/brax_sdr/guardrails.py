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
_LISTA_COM_MARCADORES = re.compile(r"^\s*[-*•]\s+\S", re.MULTILINE)


def checar_resposta(texto: str, primeira_mensagem: bool, canal: str = "whatsapp") -> list[str]:
    alertas = []
    if canal == "whatsapp":
        if len(texto) > LIMITE_CARACTERES_WHATSAPP:
            alertas.append(f"Estilo: mensagem longa para WhatsApp ({len(texto)} caracteres)")
        if "**" in texto:
            alertas.append("Estilo: markdown (**) no WhatsApp")
        if _LISTA_COM_MARCADORES.search(texto):
            alertas.append("Estilo: lista com marcadores no WhatsApp")
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
    r"\bvou (confirmar|verificar|checar|consultar)\b|\bum momentinho\b|\bte (mando|envio|passo)\b[^.\n]{0,40}\bem seguida\b"
    # Achado no 1º teste com Slack: "Deixa eu confirmar com o time... Já retorno por aqui!" com a reunião já aprovada.
    # Na 1ª bateria de evals, "Deixa eu confirmar uma coisa: quem mais participa...?" (uma pergunta) disparou o alerta:
    # agora só conta quando a confirmação é "com o time".
    r"|\bdeixa eu (confirmar|verificar|checar|ver) com (o|a) (time|equipe)\b|\bj[áa] (te )?retorno\b"
    # Decisão 054 (conversa do Wesley): "Assim que eu confirmar com o time, te retorno por aqui" passava sem alerta.
    r"|\bconfirmar com (o|a) (time|equipe)\b|\bte retorno\b|\bretorno por aqui\b|\bvolto a te (chamar|procurar)\b",
    re.IGNORECASE,
)


def promete_retorno(texto: str) -> bool:
    """Verdadeiro se o texto promete uma ação ou um retorno para depois (sem dizer quem vai fazer)."""
    return bool(_PROMETE_ACAO_FUTURA.search(texto))


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


# --- Vazamento: texto interno que nunca pode chegar ao cliente (achado no teste "mei3") ---

# Só termos que NUNCA aparecem numa fala legítima ao cliente. Palavras comuns ("ferramenta", "instruções",
# "protocolo") ficam de fora: um bloqueio indevido troca a resposta por uma transferência para humano.
_TEXTO_INTERNO = re.compile(
    r"\b(lead|leads|prompt|tool_use|proximo_passo|registrar_qualificacao|rotear_lead|"
    r"solicitar_aprovacao_executivo|transferir_para_humano|registrar_opt_out|encerrar_conversa|"
    r"dados_coletados|fora_do_icp|self_service|dados_insuficientes)\b"
    # Regras do sistema narradas ao cliente (teste "mei4": "Despedidas seguintes não recebem resposta").
    r"|\bdespedidas?\b[^.\n]{0,40}\bn[ãa]o recebe(m)? resposta"
    # Estado do sistema narrado ao cliente (teste de follow-up: a resposta foi só "Conversa encerrada.").
    r"|\bconversa encerrada\b"
    # Planejamento narrado ao cliente (dados de demonstração com o Haiku 5.5, decisão 055): "Vou registrar de novo, com o
    # gasto em dólar como sinal de compra"; "Falta confirmar o tipo de empresa para rotear".
    r"|\brotear\b|\bsina(l|is) de compra\b|\bregistrar (de novo|novamente)\b"
    r"|\b(registrar|registrei|registrando|registro) (os|esses|estes) dados\b"
    # Bastidor em inglês (bateria de 11/10, cenário self-service: "The registration failed because of an unknown field,
    # and routing still needs the company's sector. I'll retry..."). O P.H. só fala português com o lead.
    r"|\b(the|because|I'll|I will|retry|routing|registration|unknown field|still needs?)\b",
    re.IGNORECASE,
)


def sem_paragrafos_internos(texto: str) -> str:
    """Tira os parágrafos que narram o sistema e mantém o resto da resposta (decisão 055).

    Sem o "pensamento" ligado (decisão 051), o Haiku 5.5 às vezes escreve o próprio planejamento antes da resposta.
    Devolve "" se todos os parágrafos forem internos (aí vale o bloqueio da mensagem inteira, decisão 024).
    """
    # Por parágrafo, nunca por frase: num parágrafo de bastidor, as outras frases também costumam ser bastidor, mesmo sem
    # termo interno ("Conversa encerrada. Wesley recebeu a orientação e se despediu naturalmente."). Testado em 11/10.
    paragrafos = [p for p in texto.split("\n\n") if p.strip()]
    return "\n\n".join(p for p in paragrafos if not _TEXTO_INTERNO.search(p))


# Frase inteira de registro narrado, só quando ela COMEÇA assim (simulador, decisão 061: "Vou registrar o que você me
# contou."). Aqui a remoção é por frase porque o resto do parágrafo costuma ser a resposta de verdade.
_FRASE_DE_REGISTRO = re.compile(
    r"(?:(?<=^)|(?<=[.!?]\s)|(?<=\n))[ \t]*"
    r"(?:(?:vou|deixa eu|deixe-me|já|ja)\s+(?:registrar|anotar)|registrei)\b"  # "Anotado!" é reação natural e fica
    r"[^\n]*?(?:[.!?]+(?=\s|$)[ \t]*|$)",  # "R$ 15.000" não termina a frase
    re.IGNORECASE | re.MULTILINE,
)


def sem_frases_de_registro(texto: str) -> str:
    """Tira frases como "Vou registrar o que você me contou." Nunca tira uma frase com link (o próximo passo do lead)."""
    limpo = _FRASE_DE_REGISTRO.sub(lambda m: m.group(0) if "http" in m.group(0) else "", texto)
    limpo = re.sub(r"[ \t]+\n", "\n", limpo)  # o espaço que sobra no fim da linha quando a última frase sai
    return re.sub(r"\n{3,}", "\n\n", limpo).strip()


def parece_texto_interno(texto: str) -> bool:
    """Verdadeiro se a mensagem fala do sistema em vez de falar com o cliente (ex.: 'o lead se despediu')."""
    return bool(_TEXTO_INTERNO.search(texto))
