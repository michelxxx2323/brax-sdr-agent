"""Atalho para conversar com o P.H. no terminal.

    .venv\\Scripts\\python.exe conversar.py --help
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from brax_sdr.terminal import main  # noqa: E402

main()
