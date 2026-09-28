"""Testes do terminal. Não chamam a API."""

import pytest

from brax_sdr.terminal import parece_comando


@pytest.mark.parametrize(
    "texto",
    [r".venv\Scripts\python.exe conversar.py --lead mei4 --detalhes", "python conversar.py", "conversar.py --lead x"],
)
def test_reconhece_comandos(texto):  # caso real do teste "mei3"
    assert parece_comando(texto)


@pytest.mark.parametrize("texto", ["Sou MEI", "quero usar o python da empresa", "tenho 3 funcionários"])
def test_mensagens_normais_nao_sao_comandos(texto):
    assert not parece_comando(texto)
