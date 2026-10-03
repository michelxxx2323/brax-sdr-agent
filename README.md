# BRAX SDR Agent: o "P.H."

> Um agente de IA que faz pré-vendas (SDR) inbound por WhatsApp e e-mail para uma fintech B2B,
> qualificando leads, roteando para o canal certo e registrando tudo no CRM.

**Status:** 🟢 Fases 1 a 4 concluídas: o P.H. qualifica e roteia leads no terminal, **por e-mail** (Gmail, com
follow-up automático) e **por WhatsApp** (webhook validado com um simulador da Meta), testado com a API real
([Fase 2](docs/validacao-fase2.md), [Fase 3](docs/validacao-fase3.md), [Fase 4](docs/validacao-fase4.md)).
Próxima: Fase 5 (HubSpot + aprovação no Slack). A hospedagem vem depois dela (decisão 031).

> ⚠️ **A BRAX é uma empresa fictícia**, criada para este case e **inspirada na [Brex](https://www.brex.com/)**.
> Nome, planos, preços e funcionalidades são inventados. Não há relação com a Brex nem com nenhuma empresa real.

---

## O problema

Em uma fintech B2B que cresce por inbound, o SDR humano gasta a maior parte do tempo em tarefas repetitivas:
responder "como funciona?", descobrir quantos funcionários a empresa tem, separar quem é MEI de quem é
startup com rodada, e copiar tudo para o CRM. Isso cria três problemas de receita:

1. **Tempo de resposta alto**: o lead inbound esfria em minutos, mas o SDR responde em horas.
2. **Qualificação inconsistente**: cada SDR pergunta coisas diferentes, e o CRM fica incompleto.
3. **Executivo mal alocado**: contas pequenas, que poderiam abrir conta sozinhas no app, ocupam agenda do time comercial.

## A inspiração

A Woba apresentou a **"Bruna"**, uma agente SDR de inbound que qualifica leads por WhatsApp, e-mail e telefone,
coordena outros agentes, consulta um "cérebro" com o conhecimento da empresa e pede aprovação humana no Slack
antes de enviar propostas. Segundo a Woba, a taxa de qualificação dela ficou acima da do SDR humano.

Este projeto é uma **versão própria, mais simples e barata**, construída em código para mostrar como eu
desenharia essa operação do zero, com as decisões documentadas.

## A solução: P.H.

**Pedro Henrique ("P.H.")** é o assistente virtual de pré-vendas da BRAX. Ele:

- atende leads inbound por **WhatsApp** e **e-mail**;
- se apresenta como **assistente virtual** numa frase curta (e confirma sempre que perguntarem);
- oferece falar com uma pessoa quando faz sentido: lead da faixa executivo, algo fora do fluxo ou pedido do lead;
- entende a empresa do lead e **qualifica** com base no [ICP](cerebro/vendas/icp.md);
- **roteia** o lead para um de três caminhos:

| Caminho | Critério (hipótese) | O que o P.H. faz |
|---|---|---|
| Self-service | Até 20 funcionários **e** gasto mensal até R$ 50 mil | Envia o link para abrir a conta no app |
| Executivo | Mais de 20 funcionários **ou** gasto acima de R$ 50 mil | Agenda com um executivo humano, com aprovação no Slack |
| Fora do perfil | Pessoa física, MEI, só quer crédito etc. | Agradece, registra o motivo no CRM e encerra |

- registra tudo no **CRM** e faz **follow-up**.

## Arquitetura

```
WhatsApp (Meta Cloud API) ─┐
                           ├──> Agente SDR "P.H." (Claude API + ferramentas)
E-mail (Gmail API) ────────┘            │
                                        ├── Cérebro (Markdown no GitHub + Supabase)
                                        ├── Pesquisa (empresa e decisor)
                                        ├── CRM (HubSpot gratuito)
                                        └── Aprovação humana (Slack)
```

- **Um agente, várias ferramentas**: mais simples de construir e depurar do que vários subagentes.
- **Dois modelos**: um leve e barato para conversar e um mais forte para tarefas complexas e avaliações.
- **Cérebro em três camadas**: conceito (Markdown versionado), dados (Supabase) e memória por lead.

Detalhes em [docs/arquitetura.md](docs/arquitetura.md). O porquê de cada escolha está em [docs/decisoes.md](docs/decisoes.md).

## Guardrails (setor financeiro)

O P.H. **nunca** promete aprovação de conta, limite ou crédito; **nunca** pede senha, código, dados de cartão
ou documentos por mensagem; **nunca** apresenta rendimento como garantido; respeita pedidos de parada (LGPD);
e, na dúvida, passa para um humano. Ver [cerebro/regras/guardrails.md](cerebro/regras/guardrails.md).

## Fases

| # | Fase | Entrega | Status |
|---|---|---|---|
| 1 | Fundação | Estrutura, documentação e cérebro | ✅ Concluída |
| 2 | Agente no terminal | Conversar com o P.H. no terminal como se fosse um lead | ✅ Concluída |
| 3 | Canal e-mail | Gmail API, resposta na mesma thread e follow-up | ✅ Concluída |
| 4 | Canal WhatsApp | Webhook da Meta Cloud API, validado com simulador (decisão 030) | ✅ Concluída |
| 5 | CRM e aprovação humana | HubSpot + Slack | ⚪ Próxima |
| 5b | Hospedagem | Railway ou Render + Supabase, com tudo integrado (decisão 031) | ⚪ |
| 6 | Evals e métricas | Conversas de teste com LLM como juiz e painel de taxa de qualificação | ⚪ |

## Como rodar (Windows)

Pré-requisitos: Python 3.10+ e uma chave da API da Anthropic ([console.anthropic.com](https://console.anthropic.com/)).

```powershell
# 1. Criar o ambiente isolado e instalar as dependências
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Configurar a chave: copie .env.example para .env e preencha ANTHROPIC_API_KEY
copy .env.example .env

# 3. Rodar os testes (não chamam a API, custo zero)
.venv\Scripts\python.exe -m pytest

# 4. Conversar com o P.H. como se você fosse um lead
.venv\Scripts\python.exe conversar.py --detalhes
.venv\Scripts\python.exe conversar.py --lead ana-lumen --canal email
```

No terminal você faz dois papéis: o **lead** e o **time humano**. Quando o P.H. pedir aprovação para agendar
com um executivo, o terminal mostra o resumo como se fosse o Slack e pergunta se você aprova.
Use `/estado` para ver o que o P.H. já registrou sobre o lead. O histórico fica em `data/local/leads/`
(fora do Git), e usar o mesmo `--lead` continua a conversa.
Para trocar de lead, digite `/sair` antes de rodar o próximo comando. Depois de atualizar o código,
abra uma conversa nova: uma sessão aberta continua com o código antigo.

### Canal de WhatsApp (Fase 4, modo simulado)

Sem número de telefone: um simulador faz o papel da Meta (decisão 030). Use dois terminais:
```powershell
# Terminal 1: o servidor do webhook (aprovações de executivo aparecem aqui)
.venv\Scripts\python.exe servidor_whatsapp.py
# Terminal 2: você conversa como lead (/audio, /foto, /documento, /repetir, /estado)
.venv\Scripts\python.exe simular_whatsapp.py --nome "Ana" --telefone 5511900000002
```

### Canal de WhatsApp com a Meta de verdade (recebimento)

Com um app na Meta (número de teste da WhatsApp Cloud API) e um túnel [ngrok](https://ngrok.com) para expor o servidor:
1. No `.env`: `WHATSAPP_MODO=meta`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET` e um
   `WHATSAPP_VERIFY_TOKEN` inventado. O envio fica **desligado** (`WHATSAPP_ENVIO_HABILITADO` vazio): as respostas só
   aparecem no terminal (decisão 032).
2. Confira as credenciais (só leitura): `.venv\Scripts\python.exe diagnosticar_whatsapp.py`
3. Terminal 1: `.venv\Scripts\python.exe servidor_whatsapp.py` · Terminal 2: `ngrok http --url=SEU-DOMINIO 8000`
4. Na Meta (WhatsApp → Configuração → Webhook): URL **com `https://`**, por exemplo `https://seu-dominio.ngrok-free.dev/webhook`,
   e o mesmo token de verificação. Assine o campo `messages` e use o botão **Testar**.

### Canal de e-mail (Fase 3)

O P.H. atende uma caixa do Gmail dedicada à BRAX: confere e-mails novos a cada 30s, responde na mesma thread e envia
até dois lembretes (follow-up) quando o lead para de responder.

1. Crie uma conta Gmail para a BRAX e, no Google Cloud, um projeto com a **Gmail API** ativada e um **ID do cliente OAuth**
   do tipo *App para computador*. Coloque no `.env`: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET` e `GMAIL_REMETENTE`.
2. Autorize uma vez (em modo de teste do Google, a autorização vale 7 dias):
   ```powershell
   .venv\Scripts\python.exe autorizar_gmail.py
   ```
3. Ligue o atendente (`Ctrl+C` para parar). Para testar, preencha `EMAIL_REMETENTES_PERMITIDOS` com o seu e-mail:
   o P.H. só responde a quem está na lista.
   ```powershell
   .venv\Scripts\python.exe atender_email.py
   ```
4. Para testar o follow-up sem esperar dias, use `BRAX_FOLLOWUP_MINUTOS_TESTE=1` no `.env` (1 dia útil vira 1 minuto).

## Estrutura do repositório

```
brax-sdr-agent/
├── cerebro/          # o que o agente sabe sobre a BRAX
│   ├── empresa/      # visão geral, produto, planos, concorrentes
│   ├── vendas/       # ICP, qualificação, objeções, handoff
│   ├── voz/          # tom de voz e exemplos por canal
│   └── regras/       # guardrails e FAQ
├── docs/             # arquitetura e registro de decisões
├── src/brax_sdr/     # código do agente (ver docs/arquitetura.md)
├── tests/            # testes automáticos (sem chamar a API)
├── conversar.py      # conversa com o P.H. no terminal
├── autorizar_gmail.py  # autoriza a conta do Gmail da BRAX (uma vez)
├── atender_email.py  # atendimento por e-mail + follow-up
├── .env.example      # nomes das variáveis de ambiente (sem valores)
└── CLAUDE.md         # contexto para sessões com o Claude Code
```

## Stack

Python · Anthropic SDK (Claude) · Supabase · HubSpot · Slack · Meta WhatsApp Cloud API · Gmail API · Railway/Render

## Sobre este case

Projeto de portfólio para vagas de **GTM Engineer / Operações de Receita**. O objetivo não é só o código:
é mostrar como eu penso a operação de pré-vendas (ICP, qualificação, roteamento, métricas e governança)
e como transformo isso em um sistema que dá para medir e melhorar.
