"""Mensagens padronizadas, enviadas pelo código (decisão 023).

Recusas (fora do perfil) têm texto fixo por motivo: em fintech, uma recusa mal
explicada gera reclamação, e o modelo errou esse momento em dois testes seguidos.
"""

_FORA_DO_ICP = {
    "mei": (
        "Hoje a BRAX atende só empresas LTDA e S.A. com time, então ainda não conseguimos abrir conta para MEI. "
        "Vale procurar uma conta PJ feita para MEI. Se a empresa crescer e virar LTDA, vamos adorar conversar!"
    ),
    "sem_cnpj": (
        "A BRAX é uma conta para empresas com CNPJ, então ainda não conseguimos te atender. "
        "Quando a empresa estiver aberta, é só voltar a falar com a gente!"
    ),
    "pessoa_fisica": (
        "A BRAX é uma conta só para empresas (CNPJ), então não temos opção para pessoa física. "
        "Se um dia você abrir uma empresa, vamos adorar conversar!"
    ),
    "so_credito": (
        "A BRAX é focada em conta PJ, cartões corporativos e gestão de despesas, e não oferece empréstimo. "
        "Se no futuro vocês quiserem organizar os gastos do time, vamos adorar conversar!"
    ),
}


def mensagem_transferencia(nome: str | None = None, primeira_mensagem: bool = False) -> str:
    """Resposta quando o lead pede uma pessoa (o código transfere, sem passar pela IA: decisão 036)."""
    abertura = f"Claro, {nome}!" if nome else "Claro!"
    if primeira_mensagem:  # guardrail G4: identificar-se na primeira mensagem
        abertura += " Aqui é o P.H., assistente virtual da BRAX."
    return (
        f"{abertura} Vou chamar uma pessoa do nosso time para continuar a conversa com você por aqui, "
        "em horário comercial (seg a sex, 9h às 18h)."
    )


def mensagem_sem_interesse(nome: str | None = None, empresa: str | None = None) -> str:
    """Despedida quando o lead diz que não tem interesse (achado no teste de follow-up: "Conversa encerrada.")."""
    abertura = f"Entendido, {nome}!" if nome else "Entendido!"
    fecho = f" Sucesso para a {empresa}!" if empresa else " Sucesso!"
    return (
        f"{abertura} Obrigado pelo seu tempo e pela conversa. Não vou mais te enviar lembretes. "
        f"Se em algum momento fizer sentido, é só responder por aqui.{fecho}"
    )


def mensagem_fora_do_icp(motivo: str, nome: str | None = None, primeira_mensagem: bool = False) -> str:
    abertura = f"Obrigado pelo interesse, {nome}!" if nome else "Obrigado pelo interesse!"
    if primeira_mensagem:  # guardrail G4: identificar-se na primeira mensagem
        abertura += " Aqui é o P.H., assistente virtual da BRAX."
    return f"{abertura} {_FORA_DO_ICP.get(motivo, _FORA_DO_ICP['sem_cnpj'])}"
