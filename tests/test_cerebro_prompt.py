"""Testes do carregador do cérebro e do prompt. Não chamam a API."""

import json

from brax_sdr.cerebro import carregar_cerebro
from brax_sdr.memoria import Lead
from brax_sdr.prompt import montar_system


def test_cerebro_carrega_todos_os_arquivos_em_ordem_fixa():
    cerebro = carregar_cerebro()
    for caminho in ("vendas/icp.md", "regras/guardrails.md", "voz/tom-de-voz.md", "empresa/produto.md"):
        assert f'<arquivo caminho="{caminho}">' in cerebro
    assert "[NOME DA MARCA]" not in cerebro
    assert carregar_cerebro() == cerebro  # determinístico (necessário para o cache)


def test_system_tem_bloco_fixo_com_cache_e_contexto_do_lead():
    lead = Lead(id="teste", canal="email", dados={"funcionarios": 12})
    system = montar_system("CEREBRO", lead)
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert system[0]["text"].endswith("CEREBRO")
    contexto = json.loads(system[1]["text"].split("\n", 1)[1])
    assert contexto["canal"] == "email"
    assert contexto["primeira_mensagem"] is True
    assert contexto["dados_coletados"] == {"funcionarios": 12}


def test_bloco_fixo_nao_depende_do_lead():
    a = montar_system("C", Lead(id="a", canal="whatsapp"))[0]
    b = montar_system("C", Lead(id="b", canal="email", dados={"x": 1}))[0]
    assert a == b


def test_primeira_mensagem_falso_depois_que_o_ph_respondeu():
    lead = Lead(id="t", mensagens=[{"role": "user", "content": "oi"}, {"role": "assistant", "content": "olá"}])
    contexto = json.loads(montar_system("C", lead)[1]["text"].split("\n", 1)[1])
    assert contexto["primeira_mensagem"] is False
