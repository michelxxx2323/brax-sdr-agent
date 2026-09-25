"""Carrega a camada de conceito do cérebro (os arquivos Markdown de cerebro/).

Fase 2: o cérebro inteiro vai no prompt (são poucos arquivos). A ordem é sempre
a mesma para o texto ficar idêntico entre chamadas e aproveitar o cache de prompt.
"""

from pathlib import Path

from brax_sdr import config


def carregar_cerebro(pasta: Path = config.PASTA_CEREBRO) -> str:
    arquivos = sorted(pasta.rglob("*.md"), key=lambda p: p.relative_to(pasta).as_posix())
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo .md encontrado em {pasta}")
    partes = []
    for arquivo in arquivos:
        caminho = arquivo.relative_to(pasta).as_posix()
        conteudo = arquivo.read_text(encoding="utf-8").strip()
        partes.append(f'<arquivo caminho="{caminho}">\n{conteudo}\n</arquivo>')
    return "\n\n".join(partes)
