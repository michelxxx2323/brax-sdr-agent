"""Canal de WhatsApp: lê os avisos (webhook) da WhatsApp Cloud API e envia as respostas do P.H.

Como no e-mail, quem fala com a Meta é o CÓDIGO, nunca o modelo (decisão 026).
Funções puras (assinatura, leitura do formato da Meta) ficam separadas do envio, para serem testadas sem internet.
"""

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from pathlib import Path

import httpx

from brax_sdr import config, memoria


@dataclass
class MensagemWhatsApp:
    id: str  # id da mensagem na Meta (wamid...), usado para ignorar avisos repetidos
    telefone: str  # número do lead, só dígitos com DDI (ex.: 5511999990000): é o id do lead
    nome_perfil: str  # nome do perfil do WhatsApp
    tipo: str  # text, audio, image, document...
    texto: str  # o que o P.H. vai ler


# --- Segurança: o aviso veio mesmo da Meta? ----------------------------------------------------

def assinatura(corpo: bytes, segredo: str) -> str:
    """Assinatura no formato do cabeçalho X-Hub-Signature-256 (HMAC-SHA256 do corpo com a chave secreta do app)."""
    return "sha256=" + hmac.new(segredo.encode(), corpo, hashlib.sha256).hexdigest()


def assinatura_valida(corpo: bytes, cabecalho: str | None, segredo: str) -> bool:
    if not segredo or not cabecalho:
        return False
    return hmac.compare_digest(assinatura(corpo, segredo), cabecalho)


# --- Leitura do formato da Meta ----------------------------------------------------------------

_SEM_TEXTO = {
    "audio": "[O lead enviou um áudio. O P.H. não ouve áudios: peça, com educação, que escreva a mensagem.]",
    "image": "[O lead enviou uma imagem. Arquivos não são abertos: documentos só pelo app oficial.]",
    "document": "[O lead enviou um documento. Arquivos não são abertos: documentos só pelo app oficial.]",
    "video": "[O lead enviou um vídeo, que não foi aberto.]",
    "sticker": None,  # figurinha: não pede resposta
    "reaction": None,  # reação (👍 numa mensagem): não pede resposta
}


def _texto_da_mensagem(mensagem: dict) -> str | None:
    tipo = mensagem.get("type")
    if tipo == "text":
        return mensagem.get("text", {}).get("body", "")
    if tipo == "button":
        return mensagem.get("button", {}).get("text", "")
    if tipo == "interactive":
        interativo = mensagem.get("interactive", {})
        resposta = interativo.get("button_reply") or interativo.get("list_reply") or {}
        return resposta.get("title", "")
    if tipo in _SEM_TEXTO:
        aviso = _SEM_TEXTO[tipo]
        legenda = (mensagem.get(tipo) or {}).get("caption")
        if aviso and legenda:
            return f"{legenda}\n{aviso}"
        return aviso
    return f"[O lead enviou uma mensagem do tipo {tipo}, que o P.H. não consegue ler.]"


def ler_webhook(dados: dict) -> list[MensagemWhatsApp]:
    """Extrai as mensagens de um aviso da Meta. Avisos de status (entregue, lida) são ignorados."""
    mensagens = []
    for entrada in dados.get("entry", []):
        for mudanca in entrada.get("changes", []):
            valor = mudanca.get("value", {})
            nomes = {c.get("wa_id"): c.get("profile", {}).get("name", "") for c in valor.get("contacts", [])}
            for m in valor.get("messages", []):
                texto = _texto_da_mensagem(m)
                if texto is None or not texto.strip():
                    continue
                mensagens.append(MensagemWhatsApp(
                    id=m["id"], telefone=m["from"], nome_perfil=nomes.get(m["from"], ""), tipo=m.get("type", ""), texto=texto,
                ))
    return mensagens


def texto_para_o_agente(mensagem: MensagemWhatsApp, primeiro_contato: bool) -> str:
    if primeiro_contato and mensagem.nome_perfil:
        return f"[Nome no perfil do WhatsApp: {mensagem.nome_perfil}]\n{mensagem.texto}"
    return mensagem.texto


# --- Avisos repetidos: a Meta reenvia quando acha que falhou ----------------------------------

class RegistroDeMensagens:
    """Lembra os ids já processados (em arquivo, para valer mesmo se o servidor reiniciar)."""

    def __init__(self, pasta: Path = config.PASTA_WHATSAPP, limite: int = 2000):
        self.arquivo = pasta / "processadas.json"
        self.limite = limite
        self._trava = threading.Lock()

    def marcar_se_novo(self, mensagem_id: str) -> bool:
        """Marca a mensagem como processada. Devolve False se ela já tinha sido vista."""
        with self._trava:
            ids = json.loads(self.arquivo.read_text(encoding="utf-8")) if self.arquivo.exists() else []
            if mensagem_id in ids:
                return False
            ids = (ids + [mensagem_id])[-self.limite:]
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            self.arquivo.write_text(json.dumps(ids), encoding="utf-8")
            return True


# --- Envio -------------------------------------------------------------------------------------

class EnvioSimulado:
    """Modo simulado: grava a resposta num arquivo, de onde o simular_whatsapp.py lê e mostra."""

    def __init__(self, pasta: Path = config.PASTA_WHATSAPP):
        self.arquivo = pasta / "saida_simulada.jsonl"
        self._trava = threading.Lock()

    def enviar(self, telefone: str, texto: str) -> None:
        with self._trava:
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            with self.arquivo.open("a", encoding="utf-8") as saida:
                saida.write(json.dumps({"para": telefone, "texto": texto, "quando": memoria.agora()}, ensure_ascii=False) + "\n")

    def registrar_silencio(self, telefone: str, motivo: str | None) -> None:
        """Só no simulado: avisa o simulador que o P.H. decidiu não responder (para ele não ficar esperando)."""
        with self._trava:
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            with self.arquivo.open("a", encoding="utf-8") as saida:
                saida.write(json.dumps({"para": telefone, "texto": None, "motivo": motivo, "quando": memoria.agora()}) + "\n")


class EnvioMeta:
    """Modo real: envia pela WhatsApp Cloud API. Só respostas dentro da janela de 24h do lead (texto livre)."""

    def __init__(self, token: str = config.WHATSAPP_ACCESS_TOKEN, numero_id: str = config.WHATSAPP_PHONE_NUMBER_ID):
        if not token or not numero_id:
            raise RuntimeError("Modo meta: preencha WHATSAPP_ACCESS_TOKEN e WHATSAPP_PHONE_NUMBER_ID no .env.")
        self.url = f"https://graph.facebook.com/{config.WHATSAPP_API_VERSAO}/{numero_id}/messages"
        self.cabecalhos = {"Authorization": f"Bearer {token}"}

    def _postar(self, telefone: str, texto: str) -> httpx.Response:
        return httpx.post(
            self.url,
            headers=self.cabecalhos,
            json={"messaging_product": "whatsapp", "to": telefone, "type": "text", "text": {"body": texto}},
            timeout=20,
        )

    def enviar(self, telefone: str, texto: str) -> None:
        resposta = self._postar(telefone, texto)
        alternativo = numero_brasileiro_com_nono_digito(telefone)
        if resposta.status_code >= 400 and alternativo and _codigo_de_erro(resposta) == ERRO_NUMERO_NAO_PERMITIDO:
            # A Meta costuma entregar celulares brasileiros sem o 9º dígito, mas a lista de números permitidos
            # do número de teste guarda o número com o 9. Tenta de novo no formato da lista.
            resposta = self._postar(alternativo, texto)
        if resposta.status_code >= 400:
            raise RuntimeError(f"A Meta recusou o envio (HTTP {resposta.status_code}): {resposta.text[:300]}")


ERRO_NUMERO_NAO_PERMITIDO = 131030  # "Recipient phone number not in allowed list"


def _codigo_de_erro(resposta: httpx.Response) -> int | None:
    try:
        return resposta.json().get("error", {}).get("code")
    except ValueError:
        return None


def numero_brasileiro_com_nono_digito(telefone: str) -> str | None:
    """55 + DDD + 8 dígitos de celular (começando de 6 a 9) → o mesmo número com o 9 na frente. Senão, None."""
    if len(telefone) == 12 and telefone.startswith("55") and telefone[4] in "6789":
        return f"{telefone[:4]}9{telefone[4:]}"
    return None


def criar_envio():
    return EnvioMeta() if config.WHATSAPP_MODO == "meta" else EnvioSimulado()
