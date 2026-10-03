"""Leads no Supabase (Fase 5b, decisão 043).

Chamadas diretas à API REST do Supabase (PostgREST) com httpx, sem SDK extra, como no HubSpot.
A tabela é criada por supabase/esquema.sql. Só o servidor usa este módulo, com a chave SECRETA do projeto
(nunca vai para o navegador nem para o código; fica no .env e nas variáveis da hospedagem).
"""

import httpx

from brax_sdr import config

TABELA = "leads"


def colunas_de_resumo(estado: dict) -> dict:
    """Campos repetidos fora do JSON, para o painel comercial (Fase 7) filtrar e contar."""
    dados = estado.get("dados") or {}
    return {
        "id": estado["id"],
        "canal": estado.get("canal") or "whatsapp",
        "nome_contato": dados.get("nome_contato"),
        "empresa": dados.get("empresa"),
        "faixa": estado.get("faixa"),
        "motivo_faixa": estado.get("motivo_faixa"),
        "aprovacao": estado.get("aprovacao"),
        "prioridade": estado.get("prioridade") or 0,
        "opt_out": bool(estado.get("opt_out")),
        "encerrada": bool(estado.get("encerrada")),
        "transferido_para_vendedor": bool(estado.get("transferido_para_vendedor")),
        "sem_resposta": bool(estado.get("sem_resposta")),
        "custo_total_usd": round(estado.get("custo_total_usd") or 0.0, 5),
        "total_mensagens": len(estado.get("mensagens") or []),
        "estado": estado,
        "criado_em": estado.get("criado_em"),
        "atualizado_em": estado.get("atualizado_em"),
    }


class SupabaseLeads:
    def __init__(self, url: str, chave: str, transport: httpx.BaseTransport | None = None):
        cabecalhos = {"apikey": chave}
        if chave.startswith("eyJ"):  # chave antiga (service_role, formato JWT) também precisa do Authorization
            cabecalhos["Authorization"] = f"Bearer {chave}"
        self.http = httpx.Client(
            base_url=f"{url.rstrip('/')}/rest/v1", headers=cabecalhos, timeout=15, transport=transport
        )

    def ler(self, lead_id: str) -> dict | None:
        """O lead completo (coluna estado), ou None se ainda não existe."""
        resposta = self.http.get(f"/{TABELA}", params={"id": f"eq.{lead_id}", "select": "estado"})
        resposta.raise_for_status()
        linhas = resposta.json()
        return linhas[0]["estado"] if linhas else None

    def gravar(self, estado: dict) -> None:
        """Cria ou atualiza o lead (upsert pela chave id)."""
        resposta = self.http.post(
            f"/{TABELA}",
            json=colunas_de_resumo(estado),
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        resposta.raise_for_status()

    def listar_ids(self) -> list[str]:
        resposta = self.http.get(f"/{TABELA}", params={"select": "id", "order": "id"})
        resposta.raise_for_status()
        return [linha["id"] for linha in resposta.json()]


_cliente: SupabaseLeads | None = None


def cliente() -> SupabaseLeads | None:
    """Cliente único do processo, ou None se o Supabase não estiver configurado no .env (aí os leads ficam no PC)."""
    global _cliente
    if _cliente is None and config.SUPABASE_URL and config.SUPABASE_SECRET_KEY:
        _cliente = SupabaseLeads(config.SUPABASE_URL, config.SUPABASE_SECRET_KEY)
    return _cliente
