"""Regras de roteamento do ICP (cerebro/vendas/icp.md e qualificacao.md).

O modelo EXTRAI os dados da conversa; este código DECIDE a faixa (decisão 013).
Assim a regra é previsível, testável e auditável, e muda num lugar só.
"""

from dataclasses import dataclass

from brax_sdr import config

TIPOS_EMPRESA = ("ltda", "sa", "outro_cnpj", "mei", "sem_cnpj", "pessoa_fisica")
TIPOS_FORA_DO_ICP = {"mei": "mei", "sem_cnpj": "sem_cnpj", "pessoa_fisica": "pessoa_fisica"}

# Pontuação de prioridade (cerebro/vendas/qualificacao.md). Não muda a faixa.
PONTOS_POR_SINAL = {
    "rodada_recente": 3,
    "contratando_rapido": 2,
    "primeira_pessoa_financas": 2,
    "novo_escritorio": 1,
    "gastos_em_dolar": 2,
    "insatisfeito_com_banco": 1,
}
PONTOS_DECISOR = 2


@dataclass(frozen=True)
class Roteamento:
    faixa: str  # self_service | executivo | fora_do_icp | humano | dados_insuficientes
    motivo: str


def _reais(valor: float) -> str:
    return "R$ " + f"{valor:,.0f}".replace(",", ".")


def rotear(
    tipo_empresa: str | None = None,
    funcionarios: int | None = None,
    gasto_mensal: float | None = None,
    so_quer_credito: bool = False,
    setor_especial: bool = False,
) -> Roteamento:
    """Aplica a tabela de roteamento na ordem definida em qualificacao.md."""
    # 1. Fora do ICP: desqualificar cedo.
    if tipo_empresa in TIPOS_FORA_DO_ICP:
        return Roteamento("fora_do_icp", TIPOS_FORA_DO_ICP[tipo_empresa])
    if so_quer_credito:
        return Roteamento("fora_do_icp", "so_credito")

    # 2. Setor de análise especial: o agente não decide.
    if setor_especial:
        return Roteamento("humano", "setor_analise_especial")

    # 3. Executivo: basta UM dos critérios acima do limite.
    motivos_executivo = []
    if funcionarios is not None and funcionarios > config.LIMITE_FUNCIONARIOS_SELF_SERVICE:
        motivos_executivo.append(f"{funcionarios} funcionários (> {config.LIMITE_FUNCIONARIOS_SELF_SERVICE})")
    if gasto_mensal is not None and gasto_mensal > config.LIMITE_GASTO_SELF_SERVICE:
        motivos_executivo.append(f"gasto de {_reais(gasto_mensal)}/mês (> {_reais(config.LIMITE_GASTO_SELF_SERVICE)})")

    faltando = [
        nome
        for nome, valor in (("tipo_empresa", tipo_empresa), ("funcionarios", funcionarios), ("gasto_mensal", gasto_mensal))
        if valor is None
    ]

    if motivos_executivo:
        # Sem saber o tipo de empresa ainda pode ser MEI/PF: confirmar antes.
        if tipo_empresa is None:
            return Roteamento("dados_insuficientes", "falta: tipo_empresa")
        return Roteamento("executivo", " e ".join(motivos_executivo))

    # 4. Self-service: precisa dos DOIS critérios dentro do limite.
    if faltando:
        return Roteamento("dados_insuficientes", "falta: " + ", ".join(faltando))
    return Roteamento(
        "self_service",
        f"{funcionarios} funcionários e gasto de {_reais(gasto_mensal)}/mês (dentro dos limites)",
    )


def prioridade(sinais: list[str] | None, decisor: bool | None) -> int:
    """Soma os pontos dos sinais de compra. Sinais desconhecidos são ignorados."""
    pontos = sum(PONTOS_POR_SINAL.get(s, 0) for s in set(sinais or []))
    if decisor:
        pontos += PONTOS_DECISOR
    return pontos
