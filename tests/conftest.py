"""Configuração comum dos testes."""

import pytest

from brax_sdr import supabase_leads


@pytest.fixture(autouse=True)
def sem_supabase_de_verdade(monkeypatch):
    """Nenhum teste grava no banco real, mesmo com SUPABASE_URL no .env: sem cliente, os leads ficam em arquivos."""
    monkeypatch.setattr(supabase_leads, "cliente", lambda: None)


@pytest.fixture(autouse=True)
def sem_resumo_automatico(monkeypatch):
    """O resumo para o painel faria uma chamada a mais ao cliente falso dos testes; fica desligado, salvo nos testes dele."""
    from brax_sdr.agente import Agente

    monkeypatch.setattr(Agente, "_atualizar_resumo", lambda self, lead, uso: None)
