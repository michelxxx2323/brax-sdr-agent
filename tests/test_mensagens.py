"""Testes das mensagens padronizadas pelo código. Não chamam a API."""

from brax_sdr.mensagens import garantir_identificacao


def test_identificacao_completa_quando_falta():
    assert garantir_identificacao("Oi, Caio! Aqui é P.H., assistente da BRAX. Tudo bem?") == (
        "Oi, Caio! Aqui é P.H., assistente virtual da BRAX. Tudo bem?"
    )
    # Caso real dos evals: a primeira mensagem já começava falando do vendedor.
    assert garantir_identificacao("Um vendedor vai entrar em contato.") == (
        "Aqui é o P.H., assistente virtual da BRAX. Um vendedor vai entrar em contato."
    )
    assert garantir_identificacao("Opa, Gustavo! Entendo a urgência.") == (
        "Opa, Gustavo! Aqui é o P.H., assistente virtual da BRAX. Entendo a urgência."
    )


def test_identificacao_que_ja_existe_nao_muda():
    texto = "Oi, Joana! Aqui é o P.H., assistente virtual da BRAX 👋 Como posso ajudar?"
    assert garantir_identificacao(texto) == texto
