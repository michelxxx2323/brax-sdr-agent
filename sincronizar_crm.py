"""Envia ao HubSpot os leads salvos localmente (os pendentes, ou todos com --todos).

    .venv\Scripts\python.exe sincronizar_crm.py
    .venv\Scripts\python.exe sincronizar_crm.py --todos
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from brax_sdr import memoria  # noqa: E402
from brax_sdr.crm import HubSpot  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

todos = "--todos" in sys.argv
hubspot = HubSpot()
for lead_id in memoria.listar():
    lead = memoria.carregar(lead_id)
    if not todos and lead.crm.get("sincronizado_em") and not lead.crm.get("pendente"):
        continue
    try:
        print(f"{lead_id}: {', '.join(hubspot.sincronizar(lead))}")
    except Exception as erro:
        lead.crm["pendente"] = True
        print(f"{lead_id}: ERRO {erro}")
    memoria.salvar(lead)
