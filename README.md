# BRAX SDR Agent: o "P.H."

> Um agente de IA que faz pré-vendas (SDR) inbound por WhatsApp e e-mail para uma fintech B2B,
> qualificando leads, roteando para o canal certo e registrando tudo no CRM.

**Status:** 🟢 Fase 1 (Fundação) concluída. Próxima: Fase 2 (agente no terminal).

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
- sempre se apresenta como **assistente virtual** e oferece falar com uma pessoa;
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
| 2 | Agente no terminal | Conversar com o P.H. no terminal como se fosse um lead | ⚪ |
| 3 | Canal e-mail | Gmail API | ⚪ |
| 4 | Canal WhatsApp | Meta Cloud API (número de teste) | ⚪ |
| 5 | CRM e aprovação humana | HubSpot + Slack | ⚪ |
| 6 | Evals e métricas | Conversas de teste com LLM como juiz e painel de taxa de qualificação | ⚪ |

## Estrutura do repositório

```
brax-sdr-agent/
├── cerebro/          # o que o agente sabe sobre a BRAX
│   ├── empresa/      # visão geral, produto, planos, concorrentes
│   ├── vendas/       # ICP, qualificação, objeções, handoff
│   ├── voz/          # tom de voz e exemplos por canal
│   └── regras/       # guardrails e FAQ
├── docs/             # arquitetura e registro de decisões
├── src/              # código do agente (a partir da Fase 2)
├── tests/            # testes e evals
├── .env.example      # nomes das variáveis de ambiente (sem valores)
└── CLAUDE.md         # contexto para sessões com o Claude Code
```

## Stack

Python · Anthropic SDK (Claude) · Supabase · HubSpot · Slack · Meta WhatsApp Cloud API · Gmail API · Railway/Render

## Sobre este case

Projeto de portfólio para vagas de **GTM Engineer / Operações de Receita**. O objetivo não é só o código:
é mostrar como eu penso a operação de pré-vendas (ICP, qualificação, roteamento, métricas e governança)
e como transformo isso em um sistema que dá para medir e melhorar.
