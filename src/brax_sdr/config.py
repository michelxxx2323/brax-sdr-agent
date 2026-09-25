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

# Preço em US$ por milhão de tokens (entrada, saída), conferido em 2026-09-24.
# Só para ESTIMAR custo no terminal e nos evals; a fatura oficial está no Console da Anthropic.
PRECOS_USD_POR_MILHAO = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}


def custo_estimado_usd(modelo: str, uso: dict) -> float:
    """Estimativa: escrita no cache custa 1,25x a entrada; leitura do cache, 0,1x."""
    entrada, saida = PRECOS_USD_POR_MILHAO.get(modelo, (0.0, 0.0))
    tokens_entrada = (
        uso.get("input_tokens", 0)
        + 1.25 * uso.get("cache_creation_input_tokens", 0)
        + 0.1 * uso.get("cache_read_input_tokens", 0)
    )
    return (tokens_entrada * entrada + uso.get("output_tokens", 0) * saida) / 1_000_000


# --- Pastas ---
PASTA_CEREBRO = RAIZ / "cerebro"
PASTA_LEADS = RAIZ / "data" / "local" / "leads"  # ignorada pelo Git

# --- Roteamento (hipótese do ICP, a calibrar na Fase 6) ---
LIMITE_FUNCIONARIOS_SELF_SERVICE = 20
LIMITE_GASTO_SELF_SERVICE = 50_000  # R$ por mês

# --- Links públicos ---
LINK_APP = os.getenv("BRAX_LINK_APP") or "https://app.brax.example/abrir-conta"
LINK_AGENDA_EXECUTIVO = os.getenv("BRAX_LINK_AGENDA_EXECUTIVO") or "https://agenda.brax.example/executivo"
