r"""Roda a bateria de avaliação do P.H. e atualiza o painel (docs/index.html). Custa créditos da API.

    .venv\Scripts\python.exe rodar_evals.py                       # os 20 cenários
    .venv\Scripts\python.exe rodar_evals.py --cenarios mei opt_out  # só alguns (ex.: rodada-piloto)
    .venv\Scripts\python.exe rodar_evals.py --modelo claude-sonnet-5  # outro modelo de conversa
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from brax_sdr import config, supabase_leads  # noqa: E402
from brax_sdr.evals import PASTA_EVALS, carregar_cenarios, rodar_bateria  # noqa: E402
from brax_sdr.painel import gerar_painel  # noqa: E402
from brax_sdr.supabase_evals import gravar_bateria  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

parser = argparse.ArgumentParser(description="Roda os evals do P.H.")
parser.add_argument("--cenarios", nargs="*", help="ids dos cenários (padrão: todos)")
parser.add_argument("--modelo", help="modelo de conversa do P.H. (padrão: o do config.py)")
args = parser.parse_args()

if args.modelo:
    config.MODELO_CONVERSA = args.modelo
cenarios = carregar_cenarios(args.cenarios)
print(f"Rodando {len(cenarios)} cenário(s) com o P.H. em {config.MODELO_CONVERSA} (juiz: {config.MODELO_AVANCADO})\n")


def mostrar(resultado: dict) -> None:
    falhas = [nome for nome, ok in resultado["verificacoes"].items() if not ok]
    notas = resultado["notas"]
    media = round(sum(v for k, v in notas.items() if isinstance(v, int)) / 6, 1) if "erro" not in notas else "-"
    status = "PASSOU" if resultado["passou"] else f"FALHOU ({', '.join(falhas)})"
    print(f"  {resultado['id']:38} {status:40} nota {media}  US$ {resultado['custo_usd']:.3f}", flush=True)


bateria = rodar_bateria(cenarios, ao_terminar_cenario=mostrar)
pasta = PASTA_EVALS / "resultados"
pasta.mkdir(parents=True, exist_ok=True)
arquivo = pasta / f"{datetime.now():%Y%m%d-%H%M%S}-{config.MODELO_CONVERSA}.json"
arquivo.write_text(json.dumps(bateria, ensure_ascii=False, indent=2), encoding="utf-8")

r = bateria["resumo"]
print(f"\nAprovados: {r['aprovados']}/{r['cenarios']} | roteamento correto: {r['taxa_roteamento_correto']:.0%} | "
      f"nota média: {r['nota_media']} | alertas de guardrail: {r['alertas_de_guardrail']}")
print(f"Custo da bateria: US$ {r['custo_total_usd']:.2f} (P.H. por conversa: US$ {r['custo_medio_ph_usd']:.3f})")
print(f"Resultados: {arquivo.relative_to(config.RAIZ)} | painel: {gerar_painel().relative_to(config.RAIZ)}")

# Cópia no Supabase para a aba "Qualidade" do painel comercial (decisão 050). Se falhar, o JSON já está salvo.
banco = supabase_leads.cliente()
if banco:
    try:
        print(f"Supabase: {gravar_bateria(banco.http, bateria, arquivo.stem)} cenário(s) enviados")
    except Exception as erro:
        print(f"Supabase: não consegui enviar ({type(erro).__name__}: {erro}). Rode enviar_evals_supabase.py depois.")
