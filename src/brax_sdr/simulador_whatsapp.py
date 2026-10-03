"""Simulador do WhatsApp: faz o papel da Meta para testar o webhook sem número de telefone.

Monta os avisos no mesmo formato da WhatsApp Cloud API, assina com a chave secreta (como a Meta faz),
envia ao servidor e mostra a resposta do P.H., lida do arquivo de saída do modo simulado.
"""

import argparse
import json
import sys
import threading
import time
import uuid

import httpx

from brax_sdr import config
from brax_sdr.canal_whatsapp import assinatura
from brax_sdr.terminal import MOTIVOS_DE_SILENCIO, mostrar_estado

AJUDA = """Comandos:
  /audio       simula um áudio          /foto      simula uma foto com legenda
  /documento   simula um PDF            /repetir   reenvia o último aviso (a Meta faz isso às vezes)
  /estado      o que o P.H. registrou   /sair      encerra"""


def montar_aviso(telefone: str, nome: str, tipo: str, conteudo: dict, mensagem_id: str | None = None) -> dict:
    """Aviso no formato da WhatsApp Cloud API (webhook de mensagens)."""
    mensagem = {"from": telefone, "id": mensagem_id or f"wamid.SIMULADO{uuid.uuid4().hex}",
                "timestamp": str(int(time.time())), "type": tipo, tipo: conteudo}
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "SIMULADO", "changes": [{"field": "messages", "value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "15550000000", "phone_number_id": "SIMULADO"},
            "contacts": [{"profile": {"name": nome}, "wa_id": telefone}],
            "messages": [mensagem],
        }}]}],
    }


def enviar_aviso(url: str, aviso: dict) -> int:
    corpo = json.dumps(aviso).encode()
    cabecalhos = {"Content-Type": "application/json", "X-Hub-Signature-256": assinatura(corpo, config.WHATSAPP_APP_SECRET)}
    return httpx.post(url, content=corpo, headers=cabecalhos, timeout=10).status_code


def _linhas_de_saida() -> list[dict]:
    arquivo = config.PASTA_WHATSAPP / "saida_simulada.jsonl"
    if not arquivo.exists():
        return []
    return [json.loads(linha) for linha in arquivo.read_text(encoding="utf-8").splitlines() if linha.strip()]


class CaixaDeEntrada:
    """Vigia as mensagens do P.H. para este lead e mostra na hora, inclusive as que ele manda por iniciativa própria
    (retorno da aprovação no Slack, follow-up). Achado no 1º teste com Slack: o simulador só olhava logo depois de o
    lead escrever, e o retorno da aprovação nunca apareceu."""

    def __init__(self, telefone: str):
        self.telefone = telefone
        self.vistas = len(_linhas_de_saida())  # mensagens antigas não são mostradas de novo
        self.chegou = threading.Event()

    def _mostrar(self, linha: dict) -> None:
        if linha["texto"] is None:
            motivo = linha.get("motivo")
            print(f"\n[O P.H. não responde: {MOTIVOS_DE_SILENCIO.get(motivo, motivo)}]\n")
        else:
            print(f"\nP.H.: {linha['texto']}\n")
        print("Você (lead): ", end="", flush=True)

    def conferir(self) -> None:
        linhas = _linhas_de_saida()
        novas, self.vistas = linhas[self.vistas:], len(linhas)
        for linha in novas:
            if linha["para"] == self.telefone:
                self._mostrar(linha)
                self.chegou.set()

    def vigiar(self) -> None:
        while True:
            self.conferir()
            time.sleep(0.5)


def main() -> None:
    for fluxo in (sys.stdout, sys.stdin):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="Converse com o P.H. como se fosse um lead no WhatsApp (simulado).")
    parser.add_argument("--telefone", default="5511900000001", help="número fictício do lead (só dígitos, com DDI)")
    parser.add_argument("--nome", default="Lead de Teste", help="nome do perfil do WhatsApp")
    parser.add_argument("--url", default=f"http://127.0.0.1:{config.WHATSAPP_PORTA}/webhook")
    args = parser.parse_args()

    try:
        httpx.get(args.url.replace("/webhook", "/saude"), timeout=5)
    except httpx.HTTPError:
        print(f"Não encontrei o servidor em {args.url}. Em outro terminal, rode: .venv\\Scripts\\python.exe servidor_whatsapp.py")
        sys.exit(1)

    print(f"WhatsApp simulado | lead: {args.nome} ({args.telefone}) | servidor: {args.url}")
    print(AJUDA + "\n")
    caixa = CaixaDeEntrada(args.telefone)
    threading.Thread(target=caixa.vigiar, daemon=True).start()
    ultimo_aviso = None
    while True:
        try:
            texto = input("Você (lead): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not texto:
            continue
        if texto == "/sair":
            break
        if texto == "/estado":
            mostrar_estado(args.telefone)
            continue
        if texto == "/repetir":
            if not ultimo_aviso:
                print("Nada para repetir ainda.\n")
                continue
            aviso = ultimo_aviso
            print("(reenviando o último aviso, com o mesmo id: o servidor deve ignorar)")
        elif texto == "/audio":
            aviso = montar_aviso(args.telefone, args.nome, "audio", {"id": "midia1", "mime_type": "audio/ogg"})
        elif texto == "/foto":
            aviso = montar_aviso(args.telefone, args.nome, "image", {"id": "midia2", "caption": "Segue meu RG"})
        elif texto == "/documento":
            aviso = montar_aviso(args.telefone, args.nome, "document", {"id": "midia3", "filename": "contrato.pdf"})
        else:
            aviso = montar_aviso(args.telefone, args.nome, "text", {"body": texto})

        caixa.chegou.clear()
        status = enviar_aviso(args.url, aviso)
        if status != 200:
            print(f"O servidor recusou o aviso (HTTP {status}).\n")
            continue
        ultimo_aviso = aviso
        if texto == "/repetir":
            time.sleep(2)
            print("(confira no terminal do servidor: \"aviso repetido ignorado\")\n")
            continue
        # Espera a resposta antes de pedir a próxima mensagem; mensagens que chegarem depois aparecem sozinhas.
        if not caixa.chegou.wait(timeout=120):
            print("(ainda sem resposta: veja o terminal do servidor. Se houver aprovação pendente no Slack, "
                  "o retorno aparece aqui assim que alguém clicar.)\n")
