"""Canal de e-mail: transforma e-mails do Gmail em mensagens para o P.H. e as respostas dele em e-mails.

Funções puras (filtros e limpeza de texto) ficam separadas do acesso ao Gmail, para serem testadas sem internet.
"""

import base64
import re
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.utils import parseaddr

from brax_sdr import config

ASSINATURA = "P.H. · Assistente virtual da BRAX"


@dataclass
class EmailRecebido:
    id: str
    thread_id: str
    remetente: str  # só o endereço, em minúsculas
    nome_remetente: str
    assunto: str
    texto: str  # já limpo: sem a parte citada e sem assinatura
    message_id: str  # cabeçalho Message-ID, para responder na mesma thread
    referencias: str
    anexos: list[str]
    cabecalhos: dict


# --- Leitura do formato do Gmail ---------------------------------------------------------------

def _decodificar(dados: str) -> str:
    return base64.urlsafe_b64decode(dados + "=" * (-len(dados) % 4)).decode("utf-8", errors="replace")


def _partes(payload: dict):
    yield payload
    for parte in payload.get("parts", []) or []:
        yield from _partes(parte)


def _texto_e_anexos(payload: dict) -> tuple[str, list[str]]:
    texto_plano, texto_html, anexos = "", "", []
    for parte in _partes(payload):
        if parte.get("filename"):
            anexos.append(parte["filename"])
            continue
        dados = (parte.get("body") or {}).get("data")
        if not dados:
            continue
        if parte.get("mimeType") == "text/plain" and not texto_plano:
            texto_plano = _decodificar(dados)
        elif parte.get("mimeType") == "text/html" and not texto_html:
            texto_html = _decodificar(dados)
    if texto_plano:
        return texto_plano, anexos
    # Só HTML: tira as tags de forma simples (o P.H. só precisa do texto).
    sem_tags = re.sub(r"<br\s*/?>|</p>|</div>", "\n", texto_html, flags=re.IGNORECASE)
    sem_tags = re.sub(r"<[^>]+>", "", sem_tags)
    return re.sub(r"&nbsp;", " ", sem_tags), anexos


def ler_mensagem(mensagem: dict) -> EmailRecebido:
    """Converte uma mensagem da Gmail API (formato 'full') em EmailRecebido."""
    cabecalhos = {h["name"].lower(): h["value"] for h in mensagem["payload"].get("headers", [])}
    nome, endereco = parseaddr(cabecalhos.get("from", ""))
    texto, anexos = _texto_e_anexos(mensagem["payload"])
    return EmailRecebido(
        id=mensagem["id"],
        thread_id=mensagem["threadId"],
        remetente=endereco.lower(),
        nome_remetente=nome,
        assunto=cabecalhos.get("subject", ""),
        texto=limpar_texto(texto),
        message_id=cabecalhos.get("message-id", ""),
        referencias=cabecalhos.get("references", ""),
        anexos=anexos,
        cabecalhos=cabecalhos,
    )


# --- Limpeza do texto --------------------------------------------------------------------------

# Onde começa a parte citada de uma resposta (Gmail, Outlook e celulares, em português e inglês).
_INICIO_CITACAO = re.compile(
    r"^\s*(Em .{5,200} escreveu:\s*$"
    r"|On .{5,200} wrote:\s*$"
    r"|-{2,}\s*Mensagem original\s*-{2,}"
    r"|-{2,}\s*Original Message\s*-{2,}"
    r"|De:\s.+$"
    r"|From:\s.+$"
    r"|>)",
    re.IGNORECASE | re.MULTILINE,
)
_ASSINATURA = re.compile(r"^(--\s*$|Enviado do meu |Sent from my |Enviado de )", re.IGNORECASE | re.MULTILINE)


def limpar_texto(texto: str) -> str:
    """Fica só com o que o lead escreveu agora: corta a parte citada e a assinatura."""
    texto = texto.replace("\r\n", "\n")
    citacao = _INICIO_CITACAO.search(texto)
    if citacao:
        texto = texto[: citacao.start()]
    assinatura = _ASSINATURA.search(texto)
    if assinatura:
        texto = texto[: assinatura.start()]
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


# --- Filtros: quais e-mails o P.H. NÃO deve responder ------------------------------------------

_REMETENTE_AUTOMATICO = re.compile(r"^(no-?reply|naoresponda|nao-responda|mailer-daemon|postmaster|bounce)", re.IGNORECASE)


def motivo_para_ignorar(email: EmailRecebido) -> str | None:
    """Devolve o motivo para não responder, ou None se o e-mail deve ir para o P.H."""
    c = email.cabecalhos
    if config.GMAIL_REMETENTE and email.remetente == config.GMAIL_REMETENTE.lower():
        return "enviado pelo próprio P.H."
    if config.EMAIL_REMETENTES_PERMITIDOS and email.remetente not in config.EMAIL_REMETENTES_PERMITIDOS:
        return "remetente fora da lista de permitidos"
    # Respostas automáticas (férias, confirmações): responder cria um loop de e-mails entre robôs.
    if c.get("auto-submitted", "no").lower() != "no" or "x-autoreply" in c or "x-autorespond" in c:
        return "resposta automática"
    if c.get("precedence", "").lower() in ("bulk", "list", "junk", "auto_reply"):
        return "envio em massa"
    if "list-unsubscribe" in c or "list-id" in c:
        return "newsletter ou lista de e-mails"
    if _REMETENTE_AUTOMATICO.match(email.remetente.split("@")[0]):
        return "remetente automático"
    if not email.texto and not email.anexos:
        return "e-mail sem texto novo"
    return None


def texto_para_o_agente(email: EmailRecebido, primeiro_contato: bool) -> str:
    """Monta a mensagem do lead como o P.H. vai ler. Anexos nunca são abertos (guardrail G2)."""
    partes = []
    if primeiro_contato and email.assunto:
        partes.append(f"[Assunto do e-mail: {email.assunto}]")
    if email.nome_remetente and primeiro_contato:
        partes.append(f"[Nome no remetente: {email.nome_remetente}]")
    partes.append(email.texto or "(sem texto)")
    if email.anexos:
        partes.append(
            f"[O lead anexou {len(email.anexos)} arquivo(s). Os anexos não foram abertos: documentos só pelo app oficial.]"
        )
    return "\n".join(partes)


# --- Resposta ----------------------------------------------------------------------------------

_LINHA_ASSUNTO = re.compile(r"^\s*Assunto:.*\n+", re.IGNORECASE)
# "P.H. · Assistente virtual da BRAX", "P.H. - BRAX" ou só "P.H." numa linha.
_LINHA_ASSINATURA = re.compile(r"^\s*P\.?\s?H\.?\s*([·\-|][^\n]*)?$", re.IGNORECASE)
_LINHA_DE_FECHO = re.compile(r"^\s*(abra[çc]os?|um abra[çc]o|att\.?|atenciosamente|at[ée] mais)\s*,?\s*$", re.IGNORECASE)


def _corpo(texto: str) -> str:
    """Só o corpo: assunto e assinatura são do sistema, mesmo que o modelo os escreva (ele imita os exemplos).

    O texto pode juntar duas partes da resposta (decisão 027): assinaturas saem e só o último fecho ("Abraço,") fica.
    """
    corpo = _LINHA_ASSUNTO.sub("", texto.strip(), count=1)
    linhas = [linha for linha in corpo.splitlines() if not _LINHA_ASSINATURA.match(linha)]
    fechos = [i for i, linha in enumerate(linhas) if _LINHA_DE_FECHO.match(linha)]
    linhas = [linha for i, linha in enumerate(linhas) if i not in fechos[:-1]]
    corpo = re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()
    ultima_linha = corpo.splitlines()[-1].strip() if corpo else ""
    separador = "\n" if ultima_linha.endswith(",") else "\n\n"  # "Abraço," fica colado na assinatura
    return f"{corpo}{separador}{ASSINATURA}"


def montar_resposta(email: EmailRecebido, texto: str) -> dict:
    """Monta a resposta no formato da Gmail API, na mesma thread do e-mail recebido."""
    corpo = _corpo(texto)
    mensagem = MIMEText(corpo, "plain", "utf-8")
    mensagem["To"] = email.remetente
    if config.GMAIL_REMETENTE:
        mensagem["From"] = config.GMAIL_REMETENTE
    assunto = email.assunto or "Seu contato com a BRAX"
    mensagem["Subject"] = assunto if assunto.lower().startswith("re:") else f"Re: {assunto}"
    if email.message_id:
        mensagem["In-Reply-To"] = email.message_id
        mensagem["References"] = f"{email.referencias} {email.message_id}".strip()
    bruto = base64.urlsafe_b64encode(mensagem.as_bytes()).decode()
    return {"raw": bruto, "threadId": email.thread_id}
