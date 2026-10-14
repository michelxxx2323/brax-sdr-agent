"""Simulador público: qualquer pessoa conversa com o P.H. pela página do painel (Fase 8, decisões 045, 047 e 060).

A página (rota pública no Lovable) fala só com este servidor; nunca com o banco. Aqui o código garante:
- dados pessoais (CPF, CNPJ, cartão, e-mail, telefone) viram [removido] antes de chegar à IA e ao banco;
- conversas marcadas com origem "simulador": fora do HubSpot, do Slack, do follow-up e do painel comercial;
- limites por sessão e por endereço de internet, e um teto de custo por dia para todas as conversas;
- WhatsApp ou e-mail, com o mesmo formato que um lead real receberia em cada canal.
"""

import re
import threading
import uuid
from datetime import datetime, timedelta, timezone

from brax_sdr import config, memoria
from brax_sdr.canal_email import _corpo
from brax_sdr.followup import BRASILIA
from brax_sdr.memoria import Lead
from brax_sdr.travas import trava_do_lead

ORIGEM = "simulador"
FUSO = BRASILIA  # UTC-3, o mesmo do follow-up (o Windows não traz a base de fusos do Python)
REMOVIDO = "[removido]"

# --- Dados pessoais -------------------------------------------------------------------------------
# Ordem importa: o cartão (13 a 19 dígitos) e o CNPJ vêm antes do CPF e do telefone, que são mais curtos.
_DADOS_PESSOAIS = [
    re.compile(r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b"),                               # e-mail
    re.compile(r"\b(?:\d[ .-]?){13,19}\b"),                                      # cartão
    re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),                      # CNPJ
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),                             # CPF
    re.compile(r"(?:\+?55[\s-]?)?\(?\b\d{2}\)?[\s-]?9?\d{4}[\s-]?\d{4}\b"),     # telefone
]


def mascarar_dados_pessoais(texto: str) -> tuple[str, int]:
    """Troca dados pessoais por [removido]. Devolve o texto e quantos trechos foram removidos."""
    removidos = 0
    for padrao in _DADOS_PESSOAIS:
        texto, n = padrao.subn(REMOVIDO, texto)
        removidos += n
    return texto, removidos


# --- Bastidores: as mesmas regras das visões do painel (supabase/painel.sql) ----------------------

def etapa(lead: Lead) -> str:
    perdido = lead.opt_out or lead.sem_resposta or lead.dados.get("motivo_encerramento")
    if lead.faixa == "fora_do_icp":
        return "fora_do_perfil"
    if perdido:
        return "perdido"
    if lead.faixa == "executivo" and lead.aprovacao in ("aprovada", "novo_horario"):
        return "reuniao_aprovada"
    if lead.faixa == "humano" or lead.transferido_para_vendedor:
        return "com_vendedor"
    if lead.faixa == "executivo" and lead.aprovacao != "recusada":
        return "reuniao_solicitada"
    if lead.faixa in ("self_service", "executivo"):
        return "qualificado_app"
    return "em_qualificacao"


def temperatura(lead: Lead) -> str:
    if lead.faixa == "fora_do_icp" or lead.opt_out or lead.sem_resposta or lead.dados.get("motivo_encerramento"):
        return "frio"
    return "quente" if lead.prioridade >= 6 else "morno" if lead.prioridade >= 2 else "frio"


def bastidores(lead: Lead, eventos_novos: list[dict]) -> dict:
    return {
        "dados": lead.dados,
        "faixa": lead.faixa,
        "motivo_faixa": lead.motivo_faixa,
        "etapa": etapa(lead),
        "temperatura": temperatura(lead),
        "prioridade": lead.prioridade,
        "aprovacao": lead.aprovacao,
        "transferido_para_vendedor": lead.transferido_para_vendedor,
        "resumo": lead.resumo,
        "eventos": [{"tipo": e["tipo"], "detalhe": e["detalhe"]} for e in eventos_novos],
    }


# --- Limites ------------------------------------------------------------------------------------

_SESSAO_VALIDA = re.compile(r"[A-Za-z0-9-]{8,64}")

AVISOS = {
    "teto_diario": "A demonstração atingiu o limite de conversas de hoje. Volte amanhã para conversar com o P.H.!",
    "limite_sessao": "Esta conversa chegou ao limite de mensagens da demonstração. Use \"Reiniciar\" para começar outra.",
    "limite_ip": "Você chegou ao limite de mensagens de hoje nesta demonstração. Volte amanhã!",
    "texto_vazio": "Escreva uma mensagem para o P.H.",
}


_ASSUNTO_GRAVADO = re.compile(r"^\[Assunto do e-mail: (.+?)\]")


def _assunto_da_conversa(lead: Lead) -> str | None:
    """O assunto do primeiro e-mail, que fica gravado no começo da primeira mensagem do lead."""
    primeira = next((m["content"] for m in lead.mensagens if m["role"] == "user"), None)
    achado = _ASSUNTO_GRAVADO.match(primeira) if isinstance(primeira, str) else None
    return achado.group(1) if achado else None


class SimuladorPublico:
    def __init__(self, agente, custo_do_dia, teto_diario_usd: float = config.SIMULADOR_TETO_DIARIO_USD,
                 limite_por_sessao: int = config.SIMULADOR_LIMITE_POR_SESSAO,
                 limite_por_ip_dia: int = config.SIMULADOR_LIMITE_POR_IP_DIA):
        self.agente = agente
        self.custo_do_dia = custo_do_dia  # função: quanto o simulador já gastou hoje (US$)
        self.teto, self.limite_sessao, self.limite_ip = teto_diario_usd, limite_por_sessao, limite_por_ip_dia
        self._por_ip: dict[tuple[str, str], int] = {}
        self._trava = threading.Lock()

    def _conta_ip(self, ip: str) -> int:
        chave = (ip, datetime.now(FUSO).date().isoformat())
        with self._trava:
            self._por_ip[chave] = self._por_ip.get(chave, 0) + 1
            return self._por_ip[chave]

    def processar(self, sessao: str, texto: str, canal: str, ip: str, assunto: str | None = None) -> dict:
        if not _SESSAO_VALIDA.fullmatch(sessao or ""):
            raise ValueError("sessão inválida")
        if canal not in ("whatsapp", "email"):
            raise ValueError("canal inválido: use whatsapp ou email")
        texto = (texto or "").strip()
        if not texto:
            return {"bloqueado": "texto_vazio", "texto": AVISOS["texto_vazio"]}
        if self.custo_do_dia() >= self.teto:
            return {"bloqueado": "teto_diario", "texto": AVISOS["teto_diario"]}
        if self._conta_ip(ip) > self.limite_ip:
            return {"bloqueado": "limite_ip", "texto": AVISOS["limite_ip"]}

        lead_id = f"sim-{sessao}"
        pasta = self.agente.pasta_leads
        with trava_do_lead(lead_id):
            lead = memoria.carregar(lead_id, canal=canal, pasta=pasta)
            if sum(1 for m in lead.mensagens if m["role"] == "user") >= self.limite_sessao:
                return {"bloqueado": "limite_sessao", "texto": AVISOS["limite_sessao"]}
            primeiro = not lead.mensagens
            if primeiro:
                lead.origem = ORIGEM
                memoria.salvar(lead, pasta=pasta)
            limpo, removidos = mascarar_dados_pessoais(texto)
            assunto_limpo = mascarar_dados_pessoais(assunto)[0] if assunto else None
            if canal == "email" and not assunto_limpo and not primeiro:
                assunto_limpo = _assunto_da_conversa(lead)  # a página mandou só o primeiro (decisão 061)
            para_o_agente = limpo
            if canal == "email" and primeiro and assunto_limpo:
                para_o_agente = f"[Assunto do e-mail: {assunto_limpo}]\n{limpo}"
            eventos_antes = len(lead.eventos)
            resposta = self.agente.responder(lead_id, para_o_agente, canal=canal)
            lead = memoria.carregar(lead_id, pasta=pasta)
            if removidos:
                lead.registrar_evento("dados_pessoais_removidos", f"{removidos} trecho(s) trocados por {REMOVIDO}")
                memoria.salvar(lead, pasta=pasta)

        saida = {
            "texto": resposta.texto,
            "silencio": resposta.motivo_silencio,
            "mensagem_do_lead": limpo,  # a página mostra o que foi de fato enviado ao P.H.
            "dados_pessoais_removidos": removidos,
            "bastidores": bastidores(lead, lead.eventos[eventos_antes:]),
        }
        if canal == "email" and resposta.texto:
            saida["texto"] = _corpo(resposta.texto)  # mesmo corpo e assinatura que um lead real recebe
            base = assunto_limpo or "Seu contato com a BRAX"
            saida["assunto"] = base if base.lower().startswith("re:") else f"Re: {base}"
        return saida


def nova_sessao() -> str:
    return str(uuid.uuid4())


# --- Banco: custo do dia e limpeza de 7 dias ----------------------------------------------------

def custo_simulador_hoje(banco) -> float:
    """Quanto as conversas do simulador gastaram hoje (fuso de São Paulo), somando o custo de cada lead."""
    inicio = datetime.now(FUSO).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    resposta = banco.http.get("/leads", params={
        "select": "custo_total_usd", "estado->>origem": f"eq.{ORIGEM}", "atualizado_em": f"gte.{inicio.isoformat()}",
    })
    resposta.raise_for_status()
    return sum(float(linha["custo_total_usd"] or 0) for linha in resposta.json())


def apagar_conversas_antigas(banco, dias: int = config.SIMULADOR_DIAS_DE_GUARDA) -> int:
    """Apaga as conversas do simulador com mais de `dias` dias (decisão 060). Devolve quantas apagou."""
    limite = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    resposta = banco.http.delete("/leads", params={"estado->>origem": f"eq.{ORIGEM}", "criado_em": f"lt.{limite}"},
                                 headers={"Prefer": "return=representation"})
    resposta.raise_for_status()
    return len(resposta.json())


# --- Rotas no servidor (o mesmo processo do webhook do WhatsApp) ---------------------------------

def registrar_rotas(app, simulador: SimuladorPublico, origens: list[str]) -> None:
    """POST /simulador/mensagem. Só os endereços em `origens` (o painel publicado) podem chamar pelo navegador."""
    from fastapi import HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    if origens:
        app.add_middleware(CORSMiddleware, allow_origins=origens, allow_methods=["POST"], allow_headers=["content-type"])

    class Pedido(BaseModel):
        sessao: str
        texto: str
        canal: str = "whatsapp"
        assunto: str | None = None

    @app.post("/simulador/mensagem")
    def mensagem(pedido: Pedido, request: Request):
        encaminhado = request.headers.get("x-forwarded-for", "")
        ip = encaminhado.split(",")[0].strip() or (request.client.host if request.client else "desconhecido")
        try:
            return simulador.processar(pedido.sessao, pedido.texto, pedido.canal, ip, pedido.assunto)
        except ValueError as erro:
            raise HTTPException(status_code=400, detail=str(erro))

