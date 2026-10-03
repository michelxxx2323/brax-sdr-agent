"""Memória por lead: histórico, dados de qualificação e eventos.

Dois lugares, com a mesma interface (decisões 014 e 043):
- Supabase, quando o .env tem SUPABASE_URL e SUPABASE_SECRET_KEY e a pasta é a padrão (produção);
- um arquivo JSON por lead numa pasta local (sem Supabase, nos testes e nos evals, que passam a própria pasta).
"""

import json
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path

from brax_sdr import config, supabase_leads


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Lead:
    id: str
    canal: str = "whatsapp"
    mensagens: list[dict] = field(default_factory=list)  # formato da Messages API
    dados: dict = field(default_factory=dict)  # dados de qualificação coletados
    faixa: str | None = None
    motivo_faixa: str | None = None
    prioridade: int = 0
    opt_out: bool = False
    aprovacao: str | None = None  # pendente | aprovada | novo_horario | recusada
    encerrada: bool = False  # despedidas depois do encerramento não recebem resposta
    custo_total_usd: float = 0.0  # estimativa acumulada de todas as respostas deste lead
    mensagens_hoje: dict = field(default_factory=dict)  # {"data", "total", "avisado"}
    bloqueio: str | None = None  # ex.: "limite_de_custo" (só uma pessoa do time desbloqueia)
    # Follow-up (decisão 028)
    ultima_resposta_em: str | None = None  # quando o P.H. falou com o lead pela última vez
    aguardando_lead: bool = False  # a última fala do P.H. foi uma pergunta
    followups_enviados: int = 0  # zera quando o lead responde
    sem_resposta: bool = False  # recebeu todos os lembretes e não respondeu
    email_contexto: dict = field(default_factory=dict)  # thread e cabeçalhos para responder na mesma conversa
    crm: dict = field(default_factory=dict)  # ids no HubSpot e estado da sincronização (decisão 033)
    slack: dict = field(default_factory=dict)  # mensagem de aprovação no Slack (canal, ts) e resumo (decisão 034)
    # Transferência (decisão 037): o vendedor entra em contato em horário comercial e o P.H. segue coletando informações.
    transferido_para_vendedor: bool = False
    eventos: list[dict] = field(default_factory=list)
    criado_em: str = field(default_factory=agora)
    atualizado_em: str = field(default_factory=agora)

    def primeiro_nome(self) -> str | None:
        """Nome registrado na qualificação ou, na falta, o do remetente do e-mail (para saudações)."""
        nome = (self.dados.get("nome_contato") or self.email_contexto.get("nome") or "").strip()
        return nome.split()[0] if nome else None

    def registrar_evento(self, tipo: str, detalhe: str = "") -> None:
        self.eventos.append({"quando": agora(), "tipo": tipo, "detalhe": detalhe})


def _id_seguro(lead_id: str) -> str:
    """Evita que o ID vire um caminho perigoso no disco (ex.: '../')."""
    limpo = re.sub(r"[^A-Za-z0-9_.@+-]", "_", lead_id.strip())
    return limpo.strip(".") or "lead_sem_id"


def _arquivo(lead_id: str, pasta: Path) -> Path:
    return pasta / f"{_id_seguro(lead_id)}.json"


def _banco(pasta: Path):
    """Cliente do Supabase quando é a pasta padrão e o banco está configurado; senão None (arquivos locais)."""
    return supabase_leads.cliente() if pasta == config.PASTA_LEADS else None


def carregar(lead_id: str, canal: str = "whatsapp", pasta: Path = config.PASTA_LEADS) -> Lead:
    """Lê o lead (do Supabase ou do disco) ou cria um novo, sem histórico."""
    banco = _banco(pasta)
    if banco:
        dados = banco.ler(_id_seguro(lead_id))
    else:
        caminho = _arquivo(lead_id, pasta)
        dados = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else None
    if dados is None:
        return Lead(id=_id_seguro(lead_id), canal=canal)
    # Ignora campos que deixaram de existir (ex.: a pausa da decisão 036, removida na 038): arquivos antigos continuam abrindo.
    conhecidos = {campo.name for campo in fields(Lead)}
    return Lead(**{chave: valor for chave, valor in dados.items() if chave in conhecidos})


def salvar(lead: Lead, pasta: Path = config.PASTA_LEADS) -> None:
    lead.atualizado_em = agora()
    banco = _banco(pasta)
    if banco:
        banco.gravar(asdict(lead))
        return
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = _arquivo(lead.id, pasta)
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(json.dumps(asdict(lead), ensure_ascii=False, indent=2), encoding="utf-8")
    temporario.replace(caminho)  # grava tudo ou nada, nunca um arquivo pela metade


def listar(pasta: Path = config.PASTA_LEADS) -> list[str]:
    """Ids de todos os leads salvos (usado pelo follow-up)."""
    banco = _banco(pasta)
    if banco:
        return banco.listar_ids()
    return sorted(caminho.stem for caminho in pasta.glob("*.json")) if pasta.exists() else []
