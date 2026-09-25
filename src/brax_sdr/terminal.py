"""Converse com o P.H. no terminal, fazendo o papel do lead.

Uso (na pasta do projeto):
    .venv\\Scripts\\python.exe conversar.py
    .venv\\Scripts\\python.exe conversar.py --lead ana-lumen --canal email --detalhes
"""

import argparse
import os
import sys

import anthropic

from brax_sdr import config, memoria
from brax_sdr.agente import Agente
from brax_sdr.memoria import Lead

AJUDA = """Comandos:
  /estado   mostra o que o P.H. já registrou sobre o lead
  /ajuda    mostra esta ajuda
  /sair     encerra (o histórico fica salvo; use o mesmo --lead para continuar)"""


def aprovador_no_terminal(lead: Lead, resumo: str, disponibilidade: str) -> tuple[str, str]:
    """Simula a aprovação no Slack: você decide no terminal."""
    print("\n" + "=" * 60)
    print("🟢 [SLACK SIMULADO] Pedido de aprovação: lead para executivo")
    print(f"Faixa: {lead.faixa} | Motivo: {lead.motivo_faixa} | Prioridade: {lead.prioridade}")
    print(f"Disponibilidade: {disponibilidade}")
    print(f"Resumo do P.H.:\n{resumo}")
    print("=" * 60)
    while True:
        escolha = input("Aprovar? [s] sim / [n] não / [p] decidir depois: ").strip().lower()
        if escolha in ("s", "n", "p"):
            break
    observacao = input("Observação para o P.H. (opcional, Enter para pular): ").strip()
    decisao = {"s": "aprovada", "n": "recusada", "p": "pendente"}[escolha]
    print()
    return decisao, observacao


def mostrar_estado(lead_id: str) -> None:
    lead = memoria.carregar(lead_id)
    print(f"\n--- Estado do lead '{lead.id}' ---")
    print(f"Canal: {lead.canal} | Faixa: {lead.faixa or '-'} | Motivo: {lead.motivo_faixa or '-'}")
    print(f"Prioridade: {lead.prioridade} | Aprovação: {lead.aprovacao or '-'} | Opt-out: {'sim' if lead.opt_out else 'não'}")
    print("Dados coletados:")
    for campo, valor in lead.dados.items():
        print(f"  {campo}: {valor}")
    if lead.eventos:
        print("Últimos eventos:")
        for evento in lead.eventos[-5:]:
            print(f"  [{evento['tipo']}] {evento['detalhe']}")
    print("---\n")


def _credencial_configurada() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def main() -> None:
    for fluxo in (sys.stdout, sys.stdin):
        try:
            fluxo.reconfigure(encoding="utf-8")  # acentos corretos no terminal do Windows
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Converse com o P.H. como se fosse um lead.")
    parser.add_argument("--lead", default="lead-teste", help="identificador do lead (ex.: e-mail ou telefone)")
    parser.add_argument("--canal", choices=("whatsapp", "email"), default="whatsapp")
    parser.add_argument("--detalhes", action="store_true", help="mostra ferramentas usadas, tokens e custo")
    args = parser.parse_args()

    if not _credencial_configurada():
        print("Falta a chave da API. Copie .env.example para .env e preencha ANTHROPIC_API_KEY.")
        sys.exit(1)

    agente = Agente(aprovador=aprovador_no_terminal)
    lead = memoria.carregar(args.lead, canal=args.canal)
    print(f"Conversando com o P.H. | lead: {lead.id} | canal: {args.canal} | modelo: {config.MODELO_CONVERSA}")
    if lead.mensagens:
        print(f"(Continuando conversa anterior: {len(lead.mensagens)} mensagens no histórico)")
    print(AJUDA + "\n")

    custo_total = 0.0
    while True:
        try:
            texto = input("Você (lead): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not texto:
            continue
        if texto == "/sair":
            break
        if texto == "/ajuda":
            print(AJUDA)
            continue
        if texto == "/estado":
            mostrar_estado(args.lead)
            continue

        try:
            resposta = agente.responder(args.lead, texto, canal=args.canal)
        except anthropic.AuthenticationError:
            print("Erro: a chave da API foi recusada. Confira ANTHROPIC_API_KEY no .env.")
            break
        except anthropic.PermissionDeniedError:
            print("Erro: a chave não tem permissão para este modelo ou a conta está sem créditos.")
            break
        except anthropic.RateLimitError:
            print("Erro: limite de uso da API atingido. Espere um pouco e tente de novo.")
            continue
        except anthropic.APIConnectionError:
            print("Erro de conexão com a API. Confira sua internet e tente de novo.")
            continue
        except anthropic.APIStatusError as erro:
            print(f"Erro da API ({erro.status_code}): {erro.message}. Nada foi salvo desta mensagem.")
            continue

        if resposta.texto is None:
            print("[O P.H. não responde: este lead pediu para não receber mensagens (opt-out).]\n")
            continue

        print(f"\nP.H.: {resposta.texto}\n")
        custo_total += resposta.custo_usd
        for alerta in resposta.alertas:
            print(f"⚠️  Alerta de guardrail: {alerta}")
        if args.detalhes:
            uso = resposta.uso
            print(
                f"   [ferramentas: {', '.join(resposta.ferramentas_usadas) or '-'}] "
                f"[tokens: entrada {uso.get('input_tokens', 0)}, cache lido {uso.get('cache_read_input_tokens', 0)}, "
                f"cache escrito {uso.get('cache_creation_input_tokens', 0)}, saída {uso.get('output_tokens', 0)}] "
                f"[custo ~US$ {resposta.custo_usd:.4f}]\n"
            )

    print(f"Até mais! Custo estimado desta sessão: ~US$ {custo_total:.4f}")


if __name__ == "__main__":
    main()
