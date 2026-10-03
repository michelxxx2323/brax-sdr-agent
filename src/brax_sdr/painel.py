"""Painel dos evals: uma página HTML independente (docs/index.html), publicada pelo GitHub Pages (decisão 039).

Lê todas as baterias de evals/resultados/*.json e mostra a mais recente em destaque, com o histórico abaixo.
"""

import html
import json
from pathlib import Path

from brax_sdr import config
from brax_sdr.evals import CRITERIOS

PASTA_RESULTADOS = config.RAIZ / "evals" / "resultados"
ARQUIVO_PAINEL = config.RAIZ / "docs" / "index.html"

ROTULOS = {
    "tom_e_clareza": "Tom e clareza",
    "uma_pergunta_por_vez": "Uma pergunta por vez",
    "nao_repete_perguntas": "Não repete perguntas",
    "honestidade": "Honestidade",
    "guardrails": "Guardrails",
    "conducao": "Condução",
}


def carregar_baterias(pasta: Path = PASTA_RESULTADOS) -> list[dict]:
    baterias = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(pasta.glob("*.json"))] if pasta.exists() else []
    return sorted(baterias, key=lambda b: b["data"])


def _e(texto) -> str:
    return html.escape(str(texto))


def _pct(valor: float) -> str:
    return f"{valor * 100:.0f}%"


def _cartoes(resumo: dict) -> str:
    cartoes = [
        ("Cenários aprovados", f"{resumo['aprovados']}/{resumo['cenarios']}", "todas as verificações objetivas passaram"),
        ("Roteamento correto", _pct(resumo["taxa_roteamento_correto"]), "faixa certa nos cenários com faixa esperada"),
        ("Nota média do juiz", f"{resumo['nota_media']}/5" if resumo["nota_media"] else "-", "média dos 6 critérios"),
        ("Alertas de guardrail", str(resumo["alertas_de_guardrail"]), "G1 a G4, somando todos os cenários"),
        ("Custo médio por conversa", f"US$ {resumo['custo_medio_ph_usd']:.3f}", "só o P.H. (sem lead simulado e juiz)"),
        ("Custo da bateria", f"US$ {resumo['custo_total_usd']:.2f}", "P.H. + lead simulado + juiz"),
    ]
    return "".join(
        f'<div class="cartao"><div class="rotulo">{_e(t)}</div><div class="valor">{_e(v)}</div><div class="nota">{_e(n)}</div></div>'
        for t, v, n in cartoes
    )


def _barras(medias: dict) -> str:
    linhas = []
    for criterio in CRITERIOS:
        valor = medias.get(criterio)
        largura = (valor or 0) / 5 * 100
        linhas.append(
            f'<div class="barra-linha"><span class="barra-rotulo">{_e(ROTULOS[criterio])}</span>'
            f'<span class="barra"><span class="barra-preenchida" style="width:{largura:.0f}%"></span></span>'
            f'<span class="barra-valor">{valor if valor is not None else "-"}</span></div>'
        )
    return "".join(linhas)


def _cenarios(resultados: list[dict]) -> str:
    blocos = []
    for r in resultados:
        selo = '<span class="selo ok">passou</span>' if r["passou"] else '<span class="selo falhou">falhou</span>'
        falhas = [nome for nome, ok in r["verificacoes"].items() if not ok]
        notas = r["notas"]
        media = (round(sum(notas[c] for c in CRITERIOS) / len(CRITERIOS), 1) if "erro" not in notas else "-")
        conversa = "".join(
            f'<div class="fala {quem}"><b>{"Lead" if quem == "lead" else "P.H."}:</b> {_e(texto)}</div>'
            for quem, texto in r["conversa"]
        )
        problemas = "".join(f"<li>{_e(p)}</li>" for p in notas.get("problemas", []))
        blocos.append(f"""
<details class="cenario">
  <summary>{selo}<span class="titulo">{_e(r['titulo'])}</span>
    <span class="meta">nota {media} · {r['mensagens_do_lead']} msgs · US$ {r['custo_ph_usd']:.3f}</span></summary>
  <div class="detalhe">
    <p><b>Esperado:</b> {_e(json.dumps(r['esperado'], ensure_ascii=False))}<br>
       <b>Obtido:</b> {_e(json.dumps({k: v for k, v in r['obtido'].items() if v not in (None, False)}, ensure_ascii=False))}</p>
    {f'<p class="erro"><b>Verificações que falharam:</b> {_e(", ".join(falhas))}</p>' if falhas else ''}
    <p><b>Juiz:</b> {_e(notas.get('resumo', notas.get('erro', '')))}</p>
    {f'<ul>{problemas}</ul>' if problemas else ''}
    <div class="conversa">{conversa}</div>
  </div>
</details>""")
    return "".join(blocos)


def _historico(baterias: list[dict]) -> str:
    linhas = "".join(
        f"<tr><td>{_e(b['data'][:16].replace('T', ' '))}</td><td>{_e(b['modelo_conversa'])}</td>"
        f"<td>{b['resumo']['aprovados']}/{b['resumo']['cenarios']}</td><td>{_pct(b['resumo']['taxa_roteamento_correto'])}</td>"
        f"<td>{b['resumo']['nota_media']}</td><td>{b['resumo']['alertas_de_guardrail']}</td>"
        f"<td>US$ {b['resumo']['custo_medio_ph_usd']:.3f}</td></tr>"
        for b in reversed(baterias)
    )
    return (
        "<table><thead><tr><th>Data</th><th>Modelo de conversa</th><th>Aprovados</th><th>Roteamento</th>"
        f"<th>Nota</th><th>Alertas</th><th>Custo/conversa</th></tr></thead><tbody>{linhas}</tbody></table>"
    )


def gerar_html(baterias: list[dict]) -> str:
    if not baterias:
        return "<!doctype html><title>Evals do P.H.</title><p>Nenhuma bateria de avaliação ainda.</p>"
    atual = baterias[-1]
    resumo = atual["resumo"]
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Evals do P.H.</title>
<style>
:root {{ --fundo:#f7f7f5; --cartao:#fff; --texto:#1d1d1f; --suave:#6b6b70; --borda:#e3e3e0; --destaque:#2f6f4f;
        --ok:#2f6f4f; --ok-fundo:#e6f2ea; --falha:#a33a2c; --falha-fundo:#f8e7e4; --barra:#e9e9e6; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fundo:#141416; --cartao:#1e1e21; --texto:#ececee; --suave:#a0a0a8;
        --borda:#2e2e33; --destaque:#7cc79d; --ok:#7cc79d; --ok-fundo:#1f3328; --falha:#f08a7a; --falha-fundo:#3a2220; --barra:#2a2a2e; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--fundo); color:var(--texto); font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif }}
main {{ max-width:980px; margin:0 auto; padding:32px 16px 64px }}
h1 {{ font-size:26px; margin:0 0 4px }} h2 {{ font-size:18px; margin:36px 0 12px }}
.sub {{ color:var(--suave); margin:0 0 24px }}
.cartoes {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px }}
.cartao {{ background:var(--cartao); border:1px solid var(--borda); border-radius:12px; padding:14px 16px }}
.rotulo {{ color:var(--suave); font-size:13px }} .valor {{ font-size:26px; font-weight:650; margin:2px 0 }}
.nota {{ color:var(--suave); font-size:12px }}
.painel {{ background:var(--cartao); border:1px solid var(--borda); border-radius:12px; padding:16px }}
.barra-linha {{ display:grid; grid-template-columns:170px 1fr 36px; gap:10px; align-items:center; margin:6px 0 }}
.barra {{ background:var(--barra); border-radius:6px; height:12px; overflow:hidden }}
.barra-preenchida {{ display:block; height:100%; background:var(--destaque) }}
.barra-valor {{ text-align:right; font-variant-numeric:tabular-nums }}
.cenario {{ background:var(--cartao); border:1px solid var(--borda); border-radius:10px; margin:8px 0 }}
.cenario summary {{ cursor:pointer; padding:10px 14px; display:flex; gap:10px; align-items:center; flex-wrap:wrap }}
.titulo {{ flex:1; min-width:200px }} .meta {{ color:var(--suave); font-size:13px }}
.selo {{ font-size:12px; font-weight:600; padding:2px 8px; border-radius:999px }}
.selo.ok {{ color:var(--ok); background:var(--ok-fundo) }} .selo.falhou {{ color:var(--falha); background:var(--falha-fundo) }}
.detalhe {{ padding:0 14px 14px; border-top:1px solid var(--borda) }} .erro {{ color:var(--falha) }}
.conversa {{ display:flex; flex-direction:column; gap:6px; margin-top:8px }}
.fala {{ padding:8px 10px; border-radius:8px; white-space:pre-wrap; max-width:92% }}
.fala.lead {{ background:var(--barra); align-self:flex-start }} .fala.ph {{ background:var(--ok-fundo); align-self:flex-end }}
table {{ width:100%; border-collapse:collapse; background:var(--cartao); border:1px solid var(--borda); border-radius:12px; overflow:hidden }}
th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--borda); font-size:14px }}
.tabela {{ overflow-x:auto }} a {{ color:var(--destaque) }}
footer {{ color:var(--suave); font-size:13px; margin-top:40px }}
</style></head>
<body><main>
<h1>Evals do P.H.: agente SDR da BRAX</h1>
<p class="sub">Bateria de {_e(atual['data'][:16].replace('T', ' '))} · conversa: <b>{_e(atual['modelo_conversa'])}</b> ·
juiz: {_e(atual['modelo_juiz'])} · lead simulado: {_e(atual['modelo_lead_simulado'])}.
Uma IA faz o papel de cada lead, seguindo a ficha do cenário; o código confere o que é objetivo e o juiz dá notas ao resto.</p>
<div class="cartoes">{_cartoes(resumo)}</div>
<h2>Notas do juiz por critério</h2>
<div class="painel">{_barras(resumo['notas_por_criterio'])}</div>
<h2>Cenários</h2>
{_cenarios(atual['resultados'])}
<h2>Histórico das baterias</h2>
<div class="tabela">{_historico(baterias)}</div>
<footer>BRAX é uma empresa fictícia. Projeto de portfólio:
<a href="https://github.com/michelxxx2323/brax-sdr-agent">código, decisões e diários de validação no GitHub</a>.</footer>
</main></body></html>
"""


def gerar_painel(pasta: Path = PASTA_RESULTADOS, destino: Path = ARQUIVO_PAINEL) -> Path:
    destino.write_text(gerar_html(carregar_baterias(pasta)), encoding="utf-8")
    return destino
