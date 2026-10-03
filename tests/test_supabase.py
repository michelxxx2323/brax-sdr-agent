"""Testes dos leads no Supabase com um servidor FALSO (httpx.MockTransport): nenhuma chamada à internet."""

import json
from dataclasses import asdict

import httpx

from brax_sdr import memoria, supabase_leads
from brax_sdr.memoria import Lead
from brax_sdr.supabase_leads import SupabaseLeads, colunas_de_resumo


class SupabaseFalso:
    """Imita a API REST do Supabase para a tabela leads, guardando as linhas num dicionário."""

    def __init__(self):
        self.linhas, self.pedidos = {}, []

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        self.pedidos.append(pedido)
        if pedido.method == "POST":
            linha = json.loads(pedido.content)
            self.linhas[linha["id"]] = linha
            return httpx.Response(201)
        filtro = pedido.url.params.get("id")
        if filtro:
            linha = self.linhas.get(filtro.removeprefix("eq."))
            return httpx.Response(200, json=[{"estado": linha["estado"]}] if linha else [])
        return httpx.Response(200, json=[{"id": i} for i in sorted(self.linhas)])


def _banco(chave="sb_secret_teste"):
    falso = SupabaseFalso()
    return SupabaseLeads("https://exemplo.supabase.co", chave, transport=httpx.MockTransport(falso)), falso


def test_grava_le_e_lista():
    banco, falso = _banco()
    assert banco.ler("5511999990000") is None
    lead = Lead(id="5511999990000", faixa="executivo", dados={"empresa": "Lumen", "nome_contato": "Ana"})
    lead.mensagens = [{"role": "user", "content": "oi"}]
    banco.gravar(asdict(lead))
    assert banco.ler("5511999990000")["dados"]["empresa"] == "Lumen"
    assert banco.listar_ids() == ["5511999990000"]
    linha = falso.linhas["5511999990000"]
    assert (linha["empresa"], linha["faixa"], linha["total_mensagens"]) == ("Lumen", "executivo", 1)


def test_upsert_e_cabecalhos():
    banco, falso = _banco()
    banco.gravar(colunas_de_resumo({"id": "x"})["estado"])
    post = falso.pedidos[-1]
    assert post.headers["Prefer"] == "resolution=merge-duplicates,return=minimal"  # cria ou atualiza
    assert post.headers["apikey"] == "sb_secret_teste" and "Authorization" not in post.headers
    assert str(post.url) == "https://exemplo.supabase.co/rest/v1/leads"
    # Chave antiga (service_role, formato JWT) vai também no Authorization.
    antigo, falso2 = _banco("eyJhbGciOi.teste")
    antigo.listar_ids()
    assert falso2.pedidos[-1].headers["Authorization"] == "Bearer eyJhbGciOi.teste"


def test_memoria_usa_o_banco_so_na_pasta_padrao(tmp_path, monkeypatch):
    banco, falso = _banco()
    monkeypatch.setattr(supabase_leads, "cliente", lambda: banco)
    lead = memoria.carregar("ana@lumen.com", canal="email")
    lead.dados["empresa"] = "Lumen"
    memoria.salvar(lead)  # pasta padrão: vai para o Supabase
    assert memoria.carregar("ana@lumen.com").dados == {"empresa": "Lumen"}
    assert memoria.listar() == ["ana@lumen.com"]
    # Pasta própria (testes, evals): continua em arquivos, sem tocar no banco.
    pedidos_antes = len(falso.pedidos)
    memoria.salvar(Lead(id="eval-x"), pasta=tmp_path)
    assert (tmp_path / "eval-x.json").exists() and len(falso.pedidos) == pedidos_antes
