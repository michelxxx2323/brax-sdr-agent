"""Configuração comum dos testes."""

import pytest

from brax_sdr import supabase_leads


@pytest.fixture(autouse=True)
def sem_supabase_de_verdade(monkeypatch):
    """Nenhum teste grava no banco real, mesmo com SUPABASE_URL no .env: sem cliente, os leads ficam em arquivos."""
    monkeypatch.setattr(supabase_leads, "cliente", lambda: None)
