"""Configuração central do agente.

Este é o ÚNICO lugar onde os nomes dos modelos aparecem (decisão 003).
Para comparar modelos sem mexer no código, defina no .env:
    BRAX_MODELO_CONVERSA=claude-sonnet-5
"""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")

# --- Modelos (IDs conferidos na referência oficial da API em 2026-09-24) ---
MODELO_CONVERSA = os.getenv("BRAX_MODELO_CONVERSA") or "claude-haiku-4-5"
MODELO_AVANCADO = os.getenv("BRAX_MODELO_AVANCADO") or "claude-sonnet-5"

# Respostas do P.H. são curtas, mas um limite baixo demais corta a mensagem no meio.
MAX_TOKENS_CONVERSA = 4096

# Segurança contra laços infinitos de ferramentas numa única resposta.
MAX_RODADAS_FERRAMENTAS = 8

# --- Pastas ---
PASTA_CEREBRO = RAIZ / "cerebro"
PASTA_LEADS = RAIZ / "data" / "local" / "leads"  # ignorada pelo Git

# --- Roteamento (hipótese do ICP, a calibrar na Fase 6) ---
LIMITE_FUNCIONARIOS_SELF_SERVICE = 20
LIMITE_GASTO_SELF_SERVICE = 50_000  # R$ por mês

# --- Links públicos ---
LINK_APP = os.getenv("BRAX_LINK_APP") or "https://app.brax.example/abrir-conta"
LINK_AGENDA_EXECUTIVO = os.getenv("BRAX_LINK_AGENDA_EXECUTIVO") or "https://agenda.brax.example/executivo"
