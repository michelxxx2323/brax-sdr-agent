"""Gera os leads de demonstração do painel por simulação (Fase 7, decisões 045 e 055).

    .venv\\Scripts\\python.exe gerar_dados_demo.py                 # os 12 leads
    .venv\\Scripts\\python.exe gerar_dados_demo.py <id> [<id>...]  # só os indicados (ex.: para gerar um de novo)

Uma sessão por lead: o P.H. de verdade (o modelo de config.py) conversa com o lead simulado dos evals, que segue
uma ficha com fatos fixos. Grava no Supabase e no HubSpot, como uma conversa real. Cobre os caminhos self-service,
executivo, análise humana, fora do perfil e perdido, nos dois canais, mais dois casos de transferência.

Tudo é fictício: telefones 5511900000301 a 306 e e-mails em subdomínios de example.com (reservado por norma).
As aprovações de executivo são simuladas (sem Slack) e aparecem assim na linha do tempo.
Não sobrescreve: se um id já existir no banco, o script para antes de gerar qualquer coisa.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import anthropic  # noqa: E402

from brax_sdr import memoria, supabase_leads  # noqa: E402
from brax_sdr.agente import Agente  # noqa: E402
from brax_sdr.crm import criar_crm  # noqa: E402
from brax_sdr.evals import FIM, proxima_mensagem_do_lead  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

MAX_TURNOS = 10

# (id, canal, nome no e-mail, caminho esperado, ficha do lead)
LEADS = [
    ("5511900000301", "whatsapp", None, "self-service",
     "Você é Camila Rocha, sócia-fundadora da Fio Digital, um SaaS de gestão para academias. É LTDA, tem 9 pessoas e gasta "
     "uns R$ 14 mil por mês. Hoje o time paga tudo no cartão pessoal e pede reembolso por planilha, e vivem perdendo "
     "comprovantes. Você e seu sócio decidem. Quer resolver isso ainda este mês."),
    ("5511900000302", "whatsapp", None, "executivo",
     "Você é Rodrigo Alves, CEO da Feira Viva, um marketplace de hortifrúti. É LTDA, tem 35 pessoas e gasta uns R$ 90 mil "
     "por mês. Fecharam uma rodada série A há três meses e estão contratando rápido. Você decide sobre banco e cartões. "
     "Se perguntarem disponibilidade, diga terça de manhã."),
    ("5511900000303", "whatsapp", None, "análise humana",
     "Você é Bruno Takeda, sócio da Satoshi Trade, uma corretora de criptoativos. É LTDA, tem 18 pessoas e gasta uns R$ 40 "
     "mil por mês. Quer conta PJ e cartões para o time. Responda de forma curta."),
    ("5511900000304", "whatsapp", None, "fora do perfil",
     "Você é Neusa, dona da Neusa Marmitas, que é MEI (só você trabalha). Quer um cartão para separar as contas do negócio. "
     "Se perguntarem o tipo de empresa, diga que é MEI. Se o assistente explicar que não atende, agradeça e se despeça."),
    ("5511900000305", "whatsapp", None, "perdido",
     "Você é Felipe Costa, gerente financeiro da Rota Certa Logística, uma LTDA com 25 pessoas. Responda às duas primeiras "
     "perguntas normalmente; depois diga que conversaram internamente e não têm interesse em trocar de banco agora."),
    ("5511900000306", "whatsapp", None, "transferência a pedido",
     "Você é Marcos Lima, fundador da Kubo Apps, um SaaS. É LTDA, tem 15 pessoas e gasta uns R$ 25 mil por mês. Na primeira "
     "mensagem, diga que prefere falar com uma pessoa do time. Depois responda normalmente às perguntas."),
    ("juliana.mota@estudiomare.example.com", "email", "Juliana Mota", "self-service",
     "Você é Juliana Mota, sócia do Estúdio Maré, uma agência de branding LTDA com 6 pessoas que gasta uns R$ 8 mil por mês. "
     "Hoje cada um paga ferramentas no próprio cartão e o fechamento do mês vira uma bagunça. Escreva e-mails curtos e cordiais."),
    ("patricia.nogueira@vitalissaude.example.com", "email", "Patrícia Nogueira", "executivo",
     "Você é Patrícia Nogueira, CFO da Vitalis Saúde, uma healthtech S.A. com 60 pessoas que gasta uns R$ 150 mil por mês, "
     "boa parte em dólar com nuvem e software. Você foi a primeira pessoa de finanças contratada, há quatro meses, e decide "
     "sobre banco e cartões. Se perguntarem disponibilidade, diga quinta-feira à tarde. Escreva e-mails curtos e formais."),
    ("andre.matos@palpitebet.example.com", "email", "André Matos", "análise humana",
     "Você é André Matos, sócio da PalpiteBet, uma casa de apostas esportivas online. É LTDA, tem 22 pessoas e gasta uns "
     "R$ 60 mil por mês. Quer conta PJ e cartões corporativos. Escreva e-mails curtos."),
    ("lara.campos@laracampos.example.com", "email", "Lara Campos", "fora do perfil",
     "Você é Lara Campos, designer freelancer. Não tem empresa nem CNPJ, trabalha como pessoa física e quer um cartão para "
     "organizar os gastos do trabalho. Se o assistente explicar que não atende, agradeça e se despeça."),
    ("gustavo.reis@trilhoagro.example.com", "email", "Gustavo Reis", "perdido (opt-out)",
     "Você é Gustavo Reis, sócio da Trilho Agro, uma LTDA com 40 pessoas. Responda à primeira pergunta normalmente; no "
     "e-mail seguinte, peça para não receber mais mensagens da BRAX."),
    ("otavio.prado@pontengenharia.example.com", "email", "Otávio Prado", "transferência (pergunta fora do cérebro)",
     "Você é Otávio Prado, CFO da Ponte Engenharia, uma LTDA com 12 pessoas que gasta uns R$ 15 mil por mês. Logo no começo, "
     "pergunte se dá para usar a conta da BRAX com o CNPJ de uma segunda empresa do mesmo grupo e diga que precisa dessa "
     "resposta. Depois responda normalmente. Escreva e-mails curtos."),
]


def main() -> None:
    banco = supabase_leads.cliente()
    if not banco:
        sys.exit("Erro: faltam SUPABASE_URL e SUPABASE_SECRET_KEY no .env.")
    escolhidos = [lead for lead in LEADS if not sys.argv[1:] or lead[0] in sys.argv[1:]]
    if sys.argv[1:] and len(escolhidos) != len(sys.argv[1:]):
        sys.exit(f"Erro: id desconhecido. Ids possíveis: {[lead_id for lead_id, *_ in LEADS]}")
    existentes = set(banco.listar_ids()) & {lead_id for lead_id, *_ in escolhidos}
    if existentes:
        sys.exit(f"Erro: estes leads já existem no banco, nada foi gerado: {sorted(existentes)}")

    cliente = anthropic.Anthropic()
    agente = Agente(
        client=cliente,
        crm=criar_crm(),
        aprovador=lambda lead, resumo, disp: ("aprovada", "aprovação simulada (dados de demonstração, sem Slack)"),
        alerta_humano=lambda lead, motivo: None,  # transferências registradas no lead, sem alerta no Slack
    )
    for lead_id, canal, nome_email, caminho, persona in escolhidos:
        if nome_email:  # no canal de e-mail, o nome vem do cabeçalho da mensagem
            lead = memoria.carregar(lead_id, canal=canal)
            lead.email_contexto = {"nome": nome_email}
            memoria.salvar(lead)
        conversa, uso = [], {}
        for _ in range(MAX_TURNOS):
            fala = proxima_mensagem_do_lead(cliente, {"canal": canal, "persona": persona}, conversa, uso)
            if not fala or FIM in fala:
                break
            conversa.append(("lead", fala))
            resposta = agente.responder(lead_id, fala, canal=canal)
            conversa.append(("ph", resposta.texto or f"[silêncio: {resposta.motivo_silencio}]"))
        lead = memoria.carregar(lead_id)
        print(f"{lead_id:<44} esperado: {caminho:<40} faixa={lead.faixa or '—':<13} aprovação={lead.aprovacao or '—':<9} "
              f"transferido={'sim' if lead.transferido_para_vendedor else 'não'} opt-out={'sim' if lead.opt_out else 'não'} "
              f"encerramento={lead.dados.get('motivo_encerramento') or '—'} falas={len(conversa)} "
              f"HubSpot={'ok' if lead.crm.get('contato_id') else 'PENDENTE'}")


if __name__ == "__main__":
    main()
