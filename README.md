<div align="center">

**Português (Brasil)** · [English](README_en.md)

</div>

# BRAX SDR Agent: o "P.H."

> Um agente de IA que faz pré-vendas (SDR) inbound por WhatsApp e e-mail para uma fintech B2B,
> qualificando leads, roteando para o canal certo e registrando tudo no CRM.

**Status:** 🟢 **No ar 24h** (Railway + Supabase). O P.H. atende **por e-mail** (Gmail, com follow-up automático) e
**por WhatsApp** (webhook da Meta), registra tudo no **HubSpot** (funil "BRAX Inbound") e pede decisões humanas no
**Slack**. O time comercial acompanha num **painel** (Lovable), e qualquer pessoa pode **conversar com o P.H.** numa
página pública. A qualidade é medida por **evals automáticos**: 25 cenários, de 15/20 para **23/25** aprovados.

> ⚠️ **A BRAX é uma empresa fictícia**, criada para este case e **inspirada na [Brex](https://www.brex.com/)**.
> Nome, planos, preços e funcionalidades são inventados. Não há relação com a Brex nem com nenhuma empresa real.

## Experimente

| O quê | Onde | Acesso |
|---|---|---|
| 💬 **Converse com o P.H.** como se fosse um lead, por WhatsApp ou e-mail, vendo os bastidores ao vivo (dados, faixa, temperatura, eventos) | [sdr-brax.lovable.app/simular](https://sdr-brax.lovable.app/simular) | Aberto. Use só dados fictícios |
| 📊 **Painel do time comercial**: conversas, funil, métricas e a aba Qualidade | [sdr-brax.lovable.app](https://sdr-brax.lovable.app/) | `demo@brax-sdr.dev` / `BraxDemo2026!` (só leitura, dados fictícios) |
| 🧪 **Painel dos evals**: cada bateria, cenário a cenário | [GitHub Pages](https://michelxxx2323.github.io/brax-sdr-agent/) | Aberto |

No simulador, dados pessoais (CPF, CNPJ, telefone, e-mail, cartão) são trocados por `[removido]` antes de chegar à IA,
as conversas ficam fora do funil e do HubSpot e são apagadas em 7 dias, e há limites por conversa e um teto de custo
diário ([decisão 060](docs/decisoes.md), [validação](docs/validacao-fase8.md)). A conta demo é pública de propósito
e o servidor restaura a senha a cada 6 horas (decisão 058).

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
                           ├──> Agente SDR "P.H." (Claude API + ferramentas) ── no ar 24h no Railway
E-mail (Gmail API) ────────┘            │
Simulador público (Lovable) ────────────┤
                                        ├── Cérebro (Markdown versionado no GitHub)
                                        ├── Memória por lead (Supabase)
                                        ├── CRM (HubSpot gratuito)
                                        └── Aprovação humana (Slack)

Supabase ── visões somente leitura ──▶ Painel do time comercial (Lovable)
Evals ──▶ resultados em JSON ──▶ painel no GitHub Pages (+ cópia no Supabase)
```

- **Um agente, várias ferramentas**: mais simples de construir e depurar do que vários subagentes.
- **Dois modelos**: um leve e barato para conversar e um mais forte para tarefas complexas e avaliações.
- **Cérebro em três camadas**: conceito (Markdown versionado), dados (Supabase) e memória por lead.

Detalhes em [docs/arquitetura.md](docs/arquitetura.md). O porquê de cada escolha está em [docs/decisoes.md](docs/decisoes.md).

## Guardrails (setor financeiro)

O P.H. **nunca** promete aprovação de conta, limite ou crédito; **nunca** pede senha, código, dados de cartão
ou documentos por mensagem; **nunca** apresenta rendimento como garantido; respeita pedidos de parada (LGPD);
e, na dúvida, passa para um humano. Ver [cerebro/regras/guardrails.md](cerebro/regras/guardrails.md).

O princípio do projeto é **"a IA escreve, o código garante"**: quando uma regra do prompt falha duas vezes, ela vira
código. Exemplos: o código decide a faixa (a IA só extrai os dados), roteia sozinho quando os dados ficam completos,
bloqueia texto interno ("rotear", nomes de ferramentas) antes de chegar ao lead, garante a identificação como
assistente virtual e transforma uma promessa de retorno numa transferência de verdade.

## Qualidade: como o P.H. é medido

Cada mudança passa por uma **bateria de evals**: um lead simulado (outro modelo, com uma persona) conversa com o P.H.,
o código confere o resultado (faixa, transferência, opt-out, dados inventados, texto proibido) e um modelo mais forte dá
notas como juiz. Toda falha real vira um cenário novo, e só então é corrigida: **falha → cenário → correção**.

| Bateria | Modelo do P.H. | Aprovados | Roteamento correto | Custo por conversa | O que mudou |
|---|---|---|---|---|---|
| 1ª | Haiku 4.5 | 15/20 | 73% | US$ 0,026 | Linha de base |
| 2ª e 3ª | Haiku 4.5 | 19/20 | 93% | US$ 0,03 | Setor obrigatório, guardrails em camadas |
| 4ª | **Haiku 5.5** | 20/20 | 100% | **US$ 0,0035** | Troca de modelo: 9x mais barato (decisão 051) |
| 5ª a 7ª | Haiku 5.5 | 21/23 → 22/23 | 100% | US$ 0,0035 | 3 cenários novos de falhas reais; um experimento piorou e foi revertido (056) |
| 8ª | Haiku 5.5 | 23/25 | 94% | US$ 0,004 | 2 cenários vindos do simulador público (061) |

As falhas restantes mudam de cenário a cada bateria (variação do modelo, não um defeito fixo), e as travas em código
seguram o pior caso: quando a IA narra o próprio planejamento, a mensagem é bloqueada e uma pessoa assume. Detalhes:
[validação da Fase 6](docs/validacao-fase6.md) e aba Qualidade do painel.

## Fases

| # | Fase | Entrega | Status |
|---|---|---|---|
| 1 | Fundação | Estrutura, documentação e cérebro | ✅ Concluída |
| 2 | Agente no terminal | Conversar com o P.H. no terminal como se fosse um lead | ✅ Concluída |
| 3 | Canal e-mail | Gmail API, resposta na mesma thread e follow-up | ✅ Concluída |
| 4 | Canal WhatsApp | Webhook da Meta Cloud API, validado com simulador (decisão 030) | ✅ Concluída |
| 5 | CRM e aprovação humana | HubSpot (CRM) + Slack (aprovação assíncrona e alertas) | ✅ Concluída |
| 6 | Evals e métricas | Cenários com lead simulado, verificações em código, LLM como juiz e [painel](https://michelxxx2323.github.io/brax-sdr-agent/) | ✅ Concluída |
| 5b | Hospedagem | Railway (Hobby) + Supabase, com tudo integrado (decisões 043 e 044, [validação](docs/validacao-fase5b.md)) | ✅ Concluída |
| 7 | Painel comercial | Front end no Lovable para o time comercial: conversas, funil, métricas e Qualidade, lendo visões somente leitura do Supabase (decisões 041, 045 a 059; [validação](docs/validacao-fase7.md)) | 🟡 Em encerramento |
| 8 | Simulador público | Página para qualquer pessoa conversar com o P.H., com bastidores ao vivo (decisões 060 e 061; [validação](docs/validacao-fase8.md)) | 🟡 Em encerramento |

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

### No ar: Railway + Supabase (Fase 5b)

O P.H. roda 24h no **Railway** (`https://brax-sdr-agent-production.up.railway.app`, rotas `/webhook`, `/saude` e `/simulador/mensagem`), com os
leads no **Supabase**. Cada push no `main` publica a versão nova sozinho. As chaves ficam nas variáveis do Railway
(as mesmas do `.env`, com `WHATSAPP_MODO=meta`, `PORT=8080` e `PYTHONUNBUFFERED=1`). Detalhes: decisões 043 e 044 e
[validação da Fase 5b](docs/validacao-fase5b.md).

⚠️ Não rode o `iniciar_brax.py` no PC enquanto o Railway estiver no ar: os dois leriam o mesmo Gmail e responderiam duas vezes.

### Tudo junto: WhatsApp + e-mail + Slack + HubSpot (Fase 5)

```powershell
.venv\Scripts\python.exe configurar_hubspot.py   # uma vez: campos da BRAX e funil "BRAX Inbound"
.venv\Scripts\python.exe iniciar_brax.py         # liga só o que estiver configurado no .env
```
- **HubSpot:** chave de serviço (`HUBSPOT_ACCESS_TOKEN`) com 12 escopos: `crm.objects.{contacts,companies,deals}.{read,write}`
  e `crm.schemas.{contacts,companies,deals}.{read,write}`.
- **Slack:** app criado pelo manifesto (Socket Mode, escopo `chat:write`), com `SLACK_BOT_TOKEN` (xoxb-), `SLACK_APP_TOKEN`
  (xapp-, escopo `connections:write`) e `SLACK_CANAL_APROVACAO` (ID do canal). Convide o bot para o canal.
- Para testar pelo WhatsApp simulado, em outro terminal: `.venv\Scripts\python.exe simular_whatsapp.py`.

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
2. Autorize uma vez. Publique o app OAuth ("Em produção") para a autorização não vencer a cada 7 dias, como acontece
   no modo de teste do Google:
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
├── docs/             # arquitetura, decisões, validação de cada fase e painel dos evals
├── evals/            # cenários e resultados das baterias
├── lovable/          # prompts e esquema usados para construir o painel no Lovable
├── supabase/         # tabelas e visões somente leitura do painel
├── src/brax_sdr/     # código do agente (ver docs/arquitetura.md)
├── tests/            # testes automáticos (sem chamar a API)
├── conversar.py      # conversa com o P.H. no terminal
├── autorizar_gmail.py  # autoriza a conta do Gmail da BRAX (uma vez)
├── atender_email.py  # atendimento por e-mail + follow-up
├── .env.example      # nomes das variáveis de ambiente (sem valores)
└── CLAUDE.md         # contexto para sessões com o Claude Code
```

## Stack

Python · Anthropic SDK (Claude) · Supabase · HubSpot · Slack · Meta WhatsApp Cloud API · Gmail API · Railway · Lovable

## Sobre este case

Projeto de portfólio para vagas de **GTM Engineer / Operações de Receita**. O objetivo não é só o código:
é mostrar como eu penso a operação de pré-vendas (ICP, qualificação, roteamento, métricas e governança)
e como transformo isso em um sistema que dá para medir e melhorar.
