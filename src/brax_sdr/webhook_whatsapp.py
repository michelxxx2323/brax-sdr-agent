"""Servidor do webhook do WhatsApp: a Meta (ou o simulador) avisa aqui cada mensagem nova.

Fluxo: confere a assinatura → ignora avisos repetidos → responde "ok" na hora → atende em seguida.
A Meta espera resposta rápida; se demorar, ela reenvia o aviso (por isso os ids já vistos são ignorados).
"""

import hmac
import json
import threading
from datetime import datetime

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from brax_sdr import config, memoria
from brax_sdr.agente import Agente
from brax_sdr.canal_whatsapp import MensagemWhatsApp, RegistroDeMensagens, assinatura_valida, ler_webhook, texto_para_o_agente


def _log(texto: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {texto}", flush=True)


def criar_app(agente: Agente, envio, registro: RegistroDeMensagens) -> FastAPI:
    app = FastAPI(title="BRAX SDR: webhook do WhatsApp")
    travas_por_lead: dict[str, threading.Lock] = {}
    trava_do_dicionario = threading.Lock()

    def trava_do_lead(telefone: str) -> threading.Lock:
        with trava_do_dicionario:
            return travas_por_lead.setdefault(telefone, threading.Lock())

    def atender(mensagem: MensagemWhatsApp) -> None:
        # Uma mensagem por vez para cada lead: duas respostas simultâneas corromperiam a memória dele.
        with trava_do_lead(mensagem.telefone):
            try:
                pasta = agente.pasta_leads
                primeiro = not memoria.carregar(mensagem.telefone, canal="whatsapp", pasta=pasta).mensagens
                resposta = agente.responder(mensagem.telefone, texto_para_o_agente(mensagem, primeiro), canal="whatsapp")
                if resposta.texto:
                    envio.enviar(mensagem.telefone, resposta.texto)
                    _log(f"{mensagem.telefone}: respondido")
                else:
                    if hasattr(envio, "registrar_silencio"):
                        envio.registrar_silencio(mensagem.telefone, resposta.motivo_silencio)
                    _log(f"{mensagem.telefone}: sem resposta ({resposta.motivo_silencio})")
            except Exception as erro:  # uma mensagem com problema não derruba o servidor
                _log(f"ERRO ao atender {mensagem.telefone}: {type(erro).__name__}: {erro}")

    @app.get("/webhook")
    def verificar(
        modo: str = Query("", alias="hub.mode"),
        token: str = Query("", alias="hub.verify_token"),
        desafio: str = Query("", alias="hub.challenge"),
    ):
        """Verificação que a Meta faz uma vez, ao cadastrar o endereço do webhook."""
        if modo == "subscribe" and hmac.compare_digest(token, config.WHATSAPP_VERIFY_TOKEN):
            return PlainTextResponse(desafio)
        raise HTTPException(status_code=403, detail="token de verificação inválido")

    @app.post("/webhook")
    async def receber(request: Request, tarefas: BackgroundTasks):
        corpo = await request.body()
        if not assinatura_valida(corpo, request.headers.get("x-hub-signature-256"), config.WHATSAPP_APP_SECRET):
            _log("Aviso recusado: assinatura inválida")
            raise HTTPException(status_code=403, detail="assinatura inválida")
        try:
            dados = json.loads(corpo)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="JSON inválido")
        for mensagem in ler_webhook(dados):
            # Marca ANTES de atender: na dúvida, uma resposta a menos, nunca uma repetida.
            if registro.marcar_se_novo(mensagem.id):
                tarefas.add_task(atender, mensagem)
            else:
                _log(f"{mensagem.telefone}: aviso repetido ignorado ({mensagem.id})")
        return {"ok": True}

    @app.get("/saude")
    def saude():
        return {"ok": True, "modo": config.WHATSAPP_MODO}

    return app
