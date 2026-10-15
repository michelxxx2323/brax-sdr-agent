"""Testes dos leads no Supabase com um servidor FALSO (httpx.MockTransport): nenhuma chamada à internet."""

import json
import threading
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


def test_sinal_de_vida_consulta_o_banco_e_sobrevive_a_falhas():
    import threading

    chamadas = []

    class BancoInstavel:
        def listar_ids(self):
            chamadas.append(1)
            if len(chamadas) == 1:
                raise httpx.ConnectError("banco pausado")  # a falha não derruba o laço
            parar.set()
            return []

    parar = threading.Event()
    supabase_leads.manter_ativo(BancoInstavel(), parar=parar, intervalo=0)
    assert len(chamadas) == 2


def test_restaura_a_conta_demo_mesmo_com_o_email_trocado():
    # Decisão 058: o login da demo é público; um visitante pode trocar senha ou e-mail. A conta é achada pela marca
    # nos metadados (app_metadata, que o usuário não altera) e volta ao e-mail e à senha publicados.
    pedidos = []

    def servidor(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        if pedido.method == "GET":
            return httpx.Response(200, json={"users": [
                {"id": "u1", "email": "time@brax.example", "app_metadata": {}},
                {"id": "u2", "email": "trocado@invasor.example", "app_metadata": {"papel": "demonstracao"}},
            ]})
        return httpx.Response(200, json={})

    banco = SupabaseLeads("https://exemplo.supabase.co", "sb_secret_teste", transport=httpx.MockTransport(servidor))
    assert banco.restaurar_conta_demo("demo@brax-sdr.dev", "BraxDemo2026!") is True
    put = pedidos[-1]
    assert put.method == "PUT" and str(put.url).endswith("/auth/v1/admin/users/u2")
    assert json.loads(put.content)["email"] == "demo@brax-sdr.dev"
    assert put.headers["Authorization"] == "Bearer sb_secret_teste"


def test_conta_demo_protegida_em_ciclo_proprio(monkeypatch):
    # Decisão 062: a cada 5 minutos, separado do sinal de vida de 6 horas; uma falha não derruba o ciclo.
    monkeypatch.setattr(supabase_leads.config, "SUPABASE_DEMO_EMAIL", "demo@brax-sdr.dev")
    monkeypatch.setattr(supabase_leads.config, "SUPABASE_DEMO_SENHA", "BraxDemo2026!")
    chamadas, parar = [], threading.Event()

    class Banco:
        def restaurar_conta_demo(self, email, senha):
            chamadas.append((email, senha))
            if len(chamadas) == 1:
                raise httpx.ConnectError("fora do ar")
            parar.set()
            return True

    supabase_leads.proteger_conta_demo(Banco(), parar=parar, intervalo=0)
    assert chamadas == [("demo@brax-sdr.dev", "BraxDemo2026!")] * 2
    assert supabase_leads.INTERVALO_CONTA_DEMO_S == 300
