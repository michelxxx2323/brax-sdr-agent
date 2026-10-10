"""Envia ao Supabase as baterias de evals já salvas em evals/resultados (Fase 7, decisão 050).

    .venv\\Scripts\\python.exe enviar_evals_supabase.py

Pode rodar mais de uma vez: baterias que já estão no banco são atualizadas, não duplicadas. Não chama a API do Claude.
A partir daqui, o rodar_evals.py envia cada bateria nova sozinho.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from brax_sdr import supabase_leads  # noqa: E402
from brax_sdr.evals import PASTA_EVALS  # noqa: E402
from brax_sdr.supabase_evals import gravar_bateria  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

banco = supabase_leads.cliente()
if not banco:
    sys.exit("Erro: faltam SUPABASE_URL e SUPABASE_SECRET_KEY no .env.")
arquivos = sorted((PASTA_EVALS / "resultados").glob("*.json"))
for arquivo in arquivos:
    bateria = json.loads(arquivo.read_text(encoding="utf-8"))
    print(f"  {arquivo.stem}: {gravar_bateria(banco.http, bateria, arquivo.stem)} cenário(s)")
print(f"Pronto: {len(arquivos)} bateria(s) no Supabase.")
