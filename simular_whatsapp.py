"""Converse com o P.H. como se fosse um lead no WhatsApp, sem número de telefone (a Meta é simulada).

Antes, em outro terminal:  .venv\\Scripts\\python.exe servidor_whatsapp.py
Depois:                    .venv\\Scripts\\python.exe simular_whatsapp.py --nome "Ana" --telefone 5511900000002
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from brax_sdr.simulador_whatsapp import main  # noqa: E402

main()
