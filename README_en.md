<div align="center">

[Português (Brasil)](README.md) · **English**

</div>

# BRAX SDR Agent: "P.H."

> An AI agent that does inbound pre-sales (SDR) over WhatsApp and email for a B2B fintech:
> it qualifies leads, routes each one to the right path and records everything in the CRM.

**Status:** 🟢 Phases 1 to 6 and 5b complete, **live 24/7** (Railway + Supabase). P.H. qualifies and routes leads in the
terminal, **over email** (Gmail, with automatic follow-up) and **over WhatsApp** (Meta webhook, validated with a simulator
and with Meta's real test payloads), tested against the real Claude API
([Phase 2](docs/validacao-fase2.md), [Phase 3](docs/validacao-fase3.md), [Phase 4](docs/validacao-fase4.md),
[Phase 5](docs/validacao-fase5.md)). Everything lands in **HubSpot** (contact, company and deal in the "BRAX Inbound"
pipeline), and human decisions happen in **Slack** (executive-meeting approval with buttons, handoff alerts).
Quality is measured by **automated evals** ([Phase 6](docs/validacao-fase6.md)): 20 scenarios with a simulated lead,
code-based checks and an LLM judge, going from 15/20 to **19/20** passing and zero guardrail alerts
([dashboard](https://michelxxx2323.github.io/brax-sdr-agent/)). In progress: Phase 7 (sales-team dashboard built in
Lovable; the database layer is ready and its access rules are verified).

> ⚠️ **BRAX is a fictional company**, created for this case study and **inspired by [Brex](https://www.brex.com/)**.
> Its name, plans, prices and features are made up. There is no relationship with Brex or any real company.
> All leads shown in the dashboards are fictional.

> 🇧🇷 **Language note:** the agent talks to Brazilian leads, so the code, prompts, knowledge base and detailed docs
> (decision log, validation diaries) are written in **Portuguese**. This page is the English overview.

---

## The problem

In a B2B fintech that grows through inbound, a human SDR spends most of the day on repetitive work: answering
"how does it work?", finding out how many employees a company has, separating sole proprietors from funded startups,
and copying everything into the CRM. That creates three revenue problems:

1. **Slow response time:** an inbound lead goes cold in minutes, but the SDR answers in hours.
2. **Inconsistent qualification:** each SDR asks different questions, and the CRM ends up incomplete.
3. **Misallocated account executives:** small accounts that could open an account by themselves in the app take up
   the sales team's calendar.

## The inspiration

The Brazilian company Woba presented **"Bruna"**, an inbound SDR agent that qualifies leads over WhatsApp, email and
phone, coordinates other agents, queries a "brain" with the company's knowledge and asks for human approval in Slack
before sending proposals. According to Woba, her qualification rate was higher than that of the human SDR.

This project is **my own simpler and cheaper version**, built in code to show how I would design that operation from
scratch, with every decision documented.

## The solution: P.H.

**Pedro Henrique ("P.H.")** is BRAX's virtual pre-sales assistant. He:

- serves inbound leads over **WhatsApp** and **email**;
- introduces himself as a **virtual assistant** in one short sentence (and confirms it whenever asked);
- offers a human only when it makes sense: an executive-tier lead, something outside the flow, or when the lead asks;
- learns about the lead's company and **qualifies** it against the [ICP](cerebro/vendas/icp.md);
- **routes** the lead to one of three paths:

| Path | Criteria (hypothesis) | What P.H. does |
|---|---|---|
| Self-service | Up to 20 employees **and** monthly spend up to R$ 50k | Sends the link to open the account in the app |
| Executive | More than 20 employees **or** spend above R$ 50k | Books a human account executive, with approval in Slack |
| Not a fit | Individuals, sole proprietors (MEI), credit-only requests, etc. | Thanks the lead, logs the reason in the CRM and closes |

- records everything in the **CRM** and runs **follow-ups**.

## Architecture

```
WhatsApp (Meta Cloud API) ─┐
                           ├──> SDR agent "P.H." (Claude API + tools) ── runs 24/7 on Railway
Email (Gmail API) ─────────┘            │
                                        ├── Brain (Markdown knowledge base, versioned on GitHub)
                                        ├── Memory per lead (Supabase)
                                        ├── CRM (HubSpot, free tier)
                                        └── Human approval (Slack)

Supabase ── read-only views ──▶ Sales dashboard (Lovable, Phase 7)
Evals ──▶ JSON results ──▶ GitHub Pages dashboard (+ a copy in Supabase)
```

- **One agent, several tools:** simpler to build and debug than a set of sub-agents.
- **Two models:** a light, cheap one for conversations and a stronger one for summaries for the account executive and
  for judging evals.
- **"The AI writes, the code guarantees":** the model handles the conversation and extracts data; everything that is a
  business rule, a security rule or a cost limit lives in tested code (routing, opt-out, handoffs, blocking internal text).
  When a prompt instruction failed twice at the same point, it became code.
- **Three-layer brain:** concepts (versioned Markdown), data (Supabase) and memory per lead.

Details in [docs/arquitetura.md](docs/arquitetura.md). The reasoning behind every choice is in
[docs/decisoes.md](docs/decisoes.md) (about 50 decisions, each with context, options and rationale; in Portuguese).

## Guardrails (financial sector)

P.H. **never** promises account approval, card limits or credit; **never** asks for passwords, codes, card data or
documents by message; **never** presents returns as guaranteed; respects opt-out requests (LGPD, Brazil's data
protection law); and, when in doubt, hands off to a human. See [cerebro/regras/guardrails.md](cerebro/regras/guardrails.md).

## Phases

| # | Phase | Deliverable | Status |
|---|---|---|---|
| 1 | Foundation | Structure, documentation and the brain | ✅ Done |
| 2 | Agent in the terminal | Talk to P.H. in the terminal as if you were a lead | ✅ Done |
| 3 | Email channel | Gmail API, replies in the same thread, follow-up | ✅ Done |
| 4 | WhatsApp channel | Meta Cloud API webhook, validated with a simulator (decision 030) | ✅ Done |
| 5 | CRM and human approval | HubSpot (CRM) + Slack (async approval and alerts) | ✅ Done |
| 6 | Evals and metrics | 20 scenarios with a simulated lead, code checks, LLM as a judge and a [dashboard](https://michelxxx2323.github.io/brax-sdr-agent/) | ✅ Done |
| 5b | Hosting | Railway (Hobby) + Supabase, everything integrated (decisions 043 and 044, [validation](docs/validacao-fase5b.md)) | ✅ Done |
| 7 | Sales dashboard | Lovable front end for the sales team: leads, conversations, pipeline and metrics, reading Supabase (decisions 041 and 045 to 050; [validation](docs/validacao-fase7.md)) | 🟡 In progress: database ready, screens in Lovable |
| 8 | Public simulator | A web page where anyone can chat with P.H. (design to be defined, decision 041) | ⚪ |

## How to run it (Windows)

Prerequisites: Python 3.10+ and an Anthropic API key ([console.anthropic.com](https://console.anthropic.com/)).

```powershell
# 1. Create the virtual environment and install the dependencies
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Set the key: copy .env.example to .env and fill in ANTHROPIC_API_KEY
copy .env.example .env

# 3. Run the tests (they don't call the API, zero cost)
.venv\Scripts\python.exe -m pytest

# 4. Talk to P.H. as if you were a lead (the conversation is in Portuguese)
.venv\Scripts\python.exe conversar.py --detalhes
.venv\Scripts\python.exe conversar.py --lead ana-lumen --canal email
```

In the terminal you play two roles: the **lead** and the **human team**. When P.H. asks for approval to book an
account executive, the terminal shows the summary as if it were Slack and asks whether you approve.
Type `/estado` to see what P.H. has recorded about the lead. The history is stored in `data/local/leads/`
(outside Git), and reusing the same `--lead` continues the conversation.
To switch leads, type `/sair` before running the next command. After updating the code, start a new conversation:
an open session keeps running the old code.

### Live: Railway + Supabase (Phase 5b)

P.H. runs 24/7 on **Railway** (`https://brax-sdr-agent-production.up.railway.app`, routes `/webhook` and `/saude`,
the health check), with leads stored in **Supabase**. Every push to `main` deploys the new version automatically.
Keys live in Railway's variables (the same as in `.env`, plus `WHATSAPP_MODO=meta`, `PORT=8080` and
`PYTHONUNBUFFERED=1`). Details: decisions 043 and 044 and the [Phase 5b validation](docs/validacao-fase5b.md).

⚠️ Don't run `iniciar_brax.py` on your computer while Railway is live: both would read the same Gmail inbox and reply twice.

### Everything together: WhatsApp + email + Slack + HubSpot (Phase 5)

```powershell
.venv\Scripts\python.exe configurar_hubspot.py   # once: BRAX fields and the "BRAX Inbound" pipeline
.venv\Scripts\python.exe iniciar_brax.py         # starts only what is configured in .env
```
- **HubSpot:** a service key (`HUBSPOT_ACCESS_TOKEN`) with 12 scopes: `crm.objects.{contacts,companies,deals}.{read,write}`
  and `crm.schemas.{contacts,companies,deals}.{read,write}`.
- **Slack:** an app created from the manifest (Socket Mode, `chat:write` scope), with `SLACK_BOT_TOKEN` (xoxb-),
  `SLACK_APP_TOKEN` (xapp-, `connections:write` scope) and `SLACK_CANAL_APROVACAO` (channel ID). Invite the bot to the channel.
- To test through the simulated WhatsApp, in another terminal: `.venv\Scripts\python.exe simular_whatsapp.py`.

### WhatsApp channel (Phase 4, simulated mode)

No phone number needed: a simulator plays Meta's role (decision 030). Use two terminals:
```powershell
# Terminal 1: the webhook server (executive approvals show up here)
.venv\Scripts\python.exe servidor_whatsapp.py
# Terminal 2: you chat as the lead (/audio, /foto, /documento, /repetir, /estado)
.venv\Scripts\python.exe simular_whatsapp.py --nome "Ana" --telefone 5511900000002
```

### WhatsApp channel with the real Meta API (receiving)

With a Meta app (WhatsApp Cloud API test number). Locally, an [ngrok](https://ngrok.com) tunnel exposes the server;
in production, the webhook points to the Railway URL.
1. In `.env`: `WHATSAPP_MODO=meta`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET` and a
   `WHATSAPP_VERIFY_TOKEN` of your choice. Sending stays **off** (`WHATSAPP_ENVIO_HABILITADO` empty): replies only show
   up in the logs (decision 032).
2. Check the credentials (read-only): `.venv\Scripts\python.exe diagnosticar_whatsapp.py`
3. Terminal 1: `.venv\Scripts\python.exe servidor_whatsapp.py` · Terminal 2: `ngrok http --url=YOUR-DOMAIN 8000`
4. In Meta (WhatsApp → Configuration → Webhook): a URL **with `https://`**, e.g. `https://your-domain.ngrok-free.dev/webhook`,
   and the same verify token. Subscribe to the `messages` field and use the **Test** button.

### Email channel (Phase 3)

P.H. serves a Gmail inbox dedicated to BRAX: it checks for new emails every 30 seconds, replies in the same thread and
sends up to two reminders (follow-up) when the lead stops answering.

1. Create a Gmail account for BRAX and, in Google Cloud, a project with the **Gmail API** enabled and an **OAuth client
   ID** of type *Desktop app*. Put `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET` and `GMAIL_REMETENTE` in `.env`.
2. Authorize once. Publish the OAuth app ("In production") so the authorization doesn't expire every 7 days, as it
   does in Google's testing mode:
   ```powershell
   .venv\Scripts\python.exe autorizar_gmail.py
   ```
3. Start the email agent (`Ctrl+C` to stop). To test, set `EMAIL_REMETENTES_PERMITIDOS` to your email address:
   P.H. only replies to senders on that list.
   ```powershell
   .venv\Scripts\python.exe atender_email.py
   ```
4. To test the follow-up without waiting for days, set `BRAX_FOLLOWUP_MINUTOS_TESTE=1` in `.env` (1 business day becomes 1 minute).

## Repository structure

```
brax-sdr-agent/
├── cerebro/          # what the agent knows about BRAX (the "brain")
│   ├── empresa/      # overview, product, plans, competitors
│   ├── vendas/       # ICP, qualification, objections, handoff
│   ├── voz/          # tone of voice and examples per channel
│   └── regras/       # guardrails and FAQ
├── docs/             # architecture, decision log, validation diaries, eval dashboard
├── evals/            # eval scenarios and results
├── lovable/          # prompts and database schema for the Lovable dashboard
├── supabase/         # database schema, read-only views and access rules
├── src/brax_sdr/     # agent code (see docs/arquitetura.md)
├── tests/            # automated tests (no API calls)
├── conversar.py      # chat with P.H. in the terminal
├── iniciar_brax.py   # the single process: WhatsApp + email + Slack + HubSpot
├── rodar_evals.py    # runs the eval battery and updates the dashboard
├── .env.example      # environment variable names (no values)
└── CLAUDE.md         # context for Claude Code sessions
```

## Stack

Python · Anthropic SDK (Claude) · Supabase · HubSpot · Slack · Meta WhatsApp Cloud API · Gmail API · Railway · Lovable

## About this case study

A portfolio project for **GTM Engineer / Revenue Operations** roles. The goal isn't only the code: it's to show how I
think about a pre-sales operation (ICP, qualification, routing, metrics and governance) and how I turn that into a
system that can be measured and improved.
