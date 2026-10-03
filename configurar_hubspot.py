"""Cria no HubSpot os campos da BRAX e o funil "BRAX Inbound". Rode uma vez (pode repetir sem duplicar).

    .venv\Scripts\python.exe configurar_hubspot.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from brax_sdr.crm import ErroHubSpot, HubSpot  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

try:
    for linha in HubSpot().configurar():
        print(f"  {linha}")
    print("\nHubSpot configurado.")
except ErroHubSpot as erro:
    print(f"Erro: {erro}")
    print("Confira a chave (HUBSPOT_ACCESS_TOKEN) e se os 12 escopos foram marcados na chave de serviço.")
    sys.exit(1)
