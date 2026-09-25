"""Memória por lead: histórico, dados de qualificação e eventos.

Fase 2: um arquivo JSON por lead em data/local/leads/ (ignorado pelo Git).
Fase de canais: a mesma interface passa a usar o Supabase (decisão 014).
"""

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from brax_sdr import config


def _agora() -> str:
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
    aprovacao: str | None = None  # pendente | aprovada | recusada
    eventos: list[dict] = field(default_factory=list)
    criado_em: str = field(default_factory=_agora)
    atualizado_em: str = field(default_factory=_agora)

    def registrar_evento(self, tipo: str, detalhe: str = "") -> None:
        self.eventos.append({"quando": _agora(), "tipo": tipo, "detalhe": detalhe})


def _id_seguro(lead_id: str) -> str:
    """Evita que o ID vire um caminho perigoso no disco (ex.: '../')."""
    limpo = re.sub(r"[^A-Za-z0-9_.@+-]", "_", lead_id.strip())
    return limpo.strip(".") or "lead_sem_id"


def _arquivo(lead_id: str, pasta: Path) -> Path:
    return pasta / f"{_id_seguro(lead_id)}.json"


def carregar(lead_id: str, canal: str = "whatsapp", pasta: Path = config.PASTA_LEADS) -> Lead:
    """Lê o lead do disco ou cria um novo, sem histórico."""
    caminho = _arquivo(lead_id, pasta)
    if not caminho.exists():
        return Lead(id=_id_seguro(lead_id), canal=canal)
    return Lead(**json.loads(caminho.read_text(encoding="utf-8")))


def salvar(lead: Lead, pasta: Path = config.PASTA_LEADS) -> None:
    lead.atualizado_em = _agora()
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = _arquivo(lead.id, pasta)
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(json.dumps(asdict(lead), ensure_ascii=False, indent=2), encoding="utf-8")
    temporario.replace(caminho)  # grava tudo ou nada, nunca um arquivo pela metade
