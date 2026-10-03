"""Copia os leads salvos no PC (data/local/leads) para o Supabase (Fase 5b, decisão 043).

Uso:
    .venv\\Scripts\\python.exe migrar_para_supabase.py           mostra o que seria copiado (não grava nada)
    .venv\\Scripts\\python.exe migrar_para_supabase.py --gravar  copia de verdade

Pode rodar mais de uma vez: leads que já existem no banco são atualizados, não duplicados.
Os arquivos do PC não são apagados.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from brax_sdr import config, supabase_leads  # noqa: E402


def main() -> None:
    banco = supabase_leads.cliente()
    if not banco:
        sys.exit("Erro: faltam SUPABASE_URL e SUPABASE_SECRET_KEY no .env.")
    arquivos = sorted(config.PASTA_LEADS.glob("*.json")) if config.PASTA_LEADS.exists() else []
    gravar = "--gravar" in sys.argv
    print(f"{len(arquivos)} lead(s) em {config.PASTA_LEADS}" + ("" if gravar else " (simulação: use --gravar para copiar)"))
    for arquivo in arquivos:
        estado = json.loads(arquivo.read_text(encoding="utf-8"))
        resumo = f"{estado['id']:<40} {estado.get('canal', ''):<9} {estado.get('faixa') or '-'}"
        if gravar:
            banco.gravar(estado)
            print(f"  copiado  {resumo}")
        else:
            print(f"  {resumo}")
    if gravar:
        print(f"Pronto: {len(banco.listar_ids())} lead(s) no Supabase.")


if __name__ == "__main__":
    main()
