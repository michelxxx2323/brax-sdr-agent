"""Testes da tabela de roteamento do ICP. Não chamam a API."""

import pytest

from brax_sdr.roteamento import prioridade, rotear


@pytest.mark.parametrize(
    ("dados", "faixa_esperada"),
    [
        # Self-service: os dois critérios dentro do limite (limites inclusivos).
        ({"tipo_empresa": "ltda", "funcionarios": 6, "gasto_mensal": 8_000}, "self_service"),
        ({"tipo_empresa": "sa", "funcionarios": 20, "gasto_mensal": 50_000}, "self_service"),
        # Executivo: basta um critério acima.
        ({"tipo_empresa": "ltda", "funcionarios": 21, "gasto_mensal": 10_000}, "executivo"),
        ({"tipo_empresa": "ltda", "funcionarios": 5, "gasto_mensal": 50_001}, "executivo"),
        ({"tipo_empresa": "ltda", "funcionarios": 28, "gasto_mensal": None}, "executivo"),
        # Fora do ICP.
        ({"tipo_empresa": "mei", "funcionarios": 1, "gasto_mensal": 2_000}, "fora_do_icp"),
        ({"tipo_empresa": "pessoa_fisica"}, "fora_do_icp"),
        ({"tipo_empresa": "sem_cnpj"}, "fora_do_icp"),
        ({"tipo_empresa": "ltda", "funcionarios": 50, "so_quer_credito": True}, "fora_do_icp"),
        # Setor especial vai para humano, mesmo sendo grande.
        ({"tipo_empresa": "ltda", "funcionarios": 80, "setor_especial": True}, "humano"),
        # Dados insuficientes.
        ({}, "dados_insuficientes"),
        ({"tipo_empresa": "ltda", "funcionarios": 10}, "dados_insuficientes"),
        ({"funcionarios": 100}, "dados_insuficientes"),  # pode ser MEI? confirmar tipo antes
    ],
)
def test_faixas(dados, faixa_esperada):
    assert rotear(**dados).faixa == faixa_esperada


def test_motivo_fora_do_icp_usa_codigo_padronizado():
    assert rotear(tipo_empresa="mei").motivo == "mei"
    assert rotear(tipo_empresa="ltda", so_quer_credito=True).motivo == "so_credito"


def test_motivo_executivo_explica_os_criterios():
    motivo = rotear(tipo_empresa="ltda", funcionarios=28, gasto_mensal=70_000).motivo
    assert "28 funcionários" in motivo
    assert "R$ 70.000" in motivo


def test_motivo_dados_insuficientes_lista_o_que_falta():
    assert rotear(tipo_empresa="ltda").motivo == "falta: funcionarios, gasto_mensal"


def test_prioridade():
    assert prioridade(["rodada_recente", "contratando_rapido"], decisor=True) == 7
    assert prioridade(["sinal_inventado"], decisor=False) == 0
    assert prioridade(["gastos_em_dolar", "gastos_em_dolar"], decisor=None) == 2  # não conta duas vezes
    assert prioridade(None, None) == 0
