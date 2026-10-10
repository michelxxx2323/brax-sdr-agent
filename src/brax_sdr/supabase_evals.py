"""Resultados dos evals no Supabase, para a aba "Qualidade" do painel (Fase 7, decisão 050).

A tabela é criada por supabase/evals.sql. Os JSON em evals/resultados continuam sendo a fonte da verdade (e o painel
do GitHub Pages continua lendo deles); o Supabase recebe uma cópia, para o painel comercial mostrar a qualidade
ao lado da operação.
"""

from datetime import datetime, timezone

from brax_sdr.evals import CRITERIOS

TABELA = "evals"


def linhas_da_bateria(bateria: dict, nome: str) -> list[dict]:
    """Uma linha da tabela evals por cenário. `nome` identifica a bateria (o nome do arquivo, sem .json)."""
    data = datetime.fromisoformat(bateria["data"])
    if data.tzinfo is None:  # as baterias guardam a hora local do PC, sem fuso
        data = data.astimezone(timezone.utc)
    linhas = []
    for r in bateria["resultados"]:
        notas = {c: r["notas"][c] for c in CRITERIOS if c in r["notas"]}
        linhas.append({
            "bateria": nome,
            "cenario": r["id"],
            "data": data.isoformat(timespec="seconds"),
            "modelo_conversa": bateria["modelo_conversa"],
            "modelo_juiz": bateria.get("modelo_juiz"),
            "titulo": r.get("titulo"),
            "canal": r.get("canal"),
            "passou": bool(r["passou"]),
            "falhas": [nome_ for nome_, ok in r.get("verificacoes", {}).items() if not ok],
            "notas": notas,
            "nota_media": round(sum(notas.values()) / len(notas), 2) if len(notas) == len(CRITERIOS) else None,
            "problemas": r["notas"].get("problemas", []),
            "resumo_juiz": r["notas"].get("resumo") or r["notas"].get("erro"),
            "alertas": r.get("alertas", []),
            "esperado": r.get("esperado", {}),
            "obtido": r.get("obtido", {}),
            "mensagens_do_lead": r.get("mensagens_do_lead"),
            "custo_usd": r.get("custo_usd"),
            "custo_ph_usd": r.get("custo_ph_usd"),
            "conversa": r.get("conversa", []),
        })
    return linhas


def gravar_bateria(http, bateria: dict, nome: str) -> int:
    """Cria ou atualiza as linhas da bateria (upsert pela chave bateria + cenário). Devolve quantas linhas enviou.

    `http` é o cliente httpx do Supabase (supabase_leads.cliente().http), já com a chave secreta.
    """
    linhas = linhas_da_bateria(bateria, nome)
    resposta = http.post(f"/{TABELA}", json=linhas, headers={"Prefer": "resolution=merge-duplicates,return=minimal"})
    resposta.raise_for_status()
    return len(linhas)
