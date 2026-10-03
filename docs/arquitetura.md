# Arquitetura

> Estado atual: Fases 1 a 5 concluídas, Fase 6 (evals) em andamento; hospedagem (5b) por último.
> O porquê de cada escolha está em [decisoes.md](decisoes.md); o que cada teste real revelou, nos diários de validação
> ([Fase 2](validacao-fase2.md), [3](validacao-fase3.md), [4](validacao-fase4.md), [5](validacao-fase5.md)).

## Visão geral

```
                           ┌─────────────────── iniciar_brax.py (um programa só, decisão 034) ───────────────────┐
WhatsApp (Meta Cloud API) ─┼─▶ webhook FastAPI ─┐                                                                 │
                           │   (assinatura,      │                                                                │
                           │    avisos repetidos)├─▶ Agente P.H. ──▶ HubSpot (contato, empresa, negócio, notas)  │
E-mail (Gmail API) ────────┼─▶ atendente: confere│   (Claude +       Slack (aprovação com botões, alertas)       │
                           │   a caixa a cada 30s┘    ferramentas)    Memória por lead (JSON local → Supabase)    │
                           └────────────────────────────────────────────────────────────────────────────────────┘
Terminal (conversar.py) ─────▶ mesmo agente, para testes rápidos
Evals (rodar_evals.py) ──────▶ mesmo agente, com lead simulado e juiz ──▶ painel (docs/index.html, GitHub Pages)
```

**Princípio que guiou o projeto: a IA escreve, o código garante.** O modelo conduz a conversa e extrai dados; tudo o que é
regra de negócio, segurança ou custo fica em código, testado sem chamar a API. Quando uma instrução no prompt falhou duas
vezes no mesmo ponto nos testes reais, ela virou código (ver os diários).

| O modelo decide | O código garante |
|---|---|
| Como falar com o lead (tom, ordem das perguntas, explicações) | Faixa de roteamento (013), recusa de fora do perfil (023), "sem interesse" (029) |
| Quais dados extrair de cada mensagem | Opt-out (G5), limites de custo e de mensagens, despedidas sem chamar a API (021) |
| Quando chamar cada ferramenta | Transferência quando o lead pede uma pessoa (037), horário comercial no aviso |
| O texto do retorno depois da aprovação no Slack | Link obrigatório, nada de texto interno, tamanho no WhatsApp, formato da reunião (034, 035) |

## O caminho de uma mensagem

`agente.responder()` aplica, nesta ordem:

```
mensagem do lead
 1. opt-out?                        → silêncio (G5), sem chamar a IA
 2. pediu uma pessoa?               → transfere em código (alerta no Slack) e segue para a IA com uma nota explícita (037)
 3. proteção (protecao.py)          → limite diário, limite de custo, mensagem gigante, despedida após encerramento (021)
 4. IA + ferramentas (laço manual)  → até 8 rodadas; ferramentas validam os dados e aplicam regras (015)
 5. qual texto vale (027)           → o escrito depois de ferramentas que mudam a resposta
 6. texto padronizado, se for o caso → fora do perfil (023), sem interesse (029)
 7. WhatsApp longo?                 → reescrita curta, com travas (022)
 8. transferência sem horário?      → o código acrescenta "vendedor em horário comercial" (037)
 9. texto interno?                  → bloqueado: silêncio ou mensagem de segurança (024)
10. alertas                         → guardrails G1–G4, estilo, confiabilidade (registrados para medir)
11. salva a memória → sincroniza o HubSpot (sem travar a conversa, 033) → o canal envia
```

## Componentes

### Canais

| Canal | Como chega a mensagem | Detalhes | Status |
|---|---|---|---|
| Terminal | Digitação (`conversar.py`) | Aprovações simuladas no terminal | ✅ |
| E-mail | Gmail API, a caixa conferida a cada 30s (025) | Resposta na mesma thread; filtros anti-loop; anexos nunca abertos; follow-up | ✅ |
| WhatsApp | Webhook da Meta (FastAPI) | Assinatura HMAC; avisos repetidos ignorados; uma mensagem por vez por lead; áudio e documentos nunca abertos | ✅ simulado (030); recebimento real validado (032) |

Quem fala com o Gmail e com a Meta é o **código**, nunca o modelo (026): um e-mail ou uma mensagem maliciosa não consegue
fazer a IA ler ou enviar outras mensagens.

### Agente P.H.

Um único agente com ferramentas (001), num laço manual (015) que guarda o histórico completo de cada lead.

| Ferramenta | O que faz |
|---|---|
| `registrar_qualificacao` | Salva os dados ditos pelo lead (validados; "não informado" é descartado). Dado que desqualifica (MEI, sem CNPJ...) já roteia |
| `rotear_lead` | Aplica a tabela do ICP **em código** e registra faixa e motivo (013) |
| `solicitar_aprovacao_executivo` | Publica o pedido no Slack e devolve "pendente"; o retorno sai depois do clique (034) |
| `transferir_para_humano` | Um alerta no Slack; o vendedor entra em contato em horário comercial e o P.H. segue coletando (037, 038) |
| `registrar_opt_out` | Pedido de parada (LGPD): nenhum contato depois disso, em nenhum canal |
| `encerrar_conversa` | Exige roteamento antes (exceto fora do assunto); "sem interesse" registra o motivo da perda (029) |

O link do app e o link de agenda vêm sempre das ferramentas: o modelo nunca inventa um link.

**Modelos** (todos em `config.py`, trocáveis pelo `.env`):

| Uso | Modelo | Por quê |
|---|---|---|
| Conversa com o lead, reescrita de mensagens longas | `claude-haiku-4-5` | Rápido e barato; o raciocínio de negócio está no código (012) |
| Resumo do lead para o time (Slack e HubSpot), juiz dos evals | `claude-sonnet-5` | Mais capacidade; sem palpites no resumo |
| Lead simulado nos evals | `claude-haiku-4-5` | Só precisa seguir a ficha do cenário |

### Cérebro (base de conhecimento)

| Camada | Onde fica hoje | Plano |
|---|---|---|
| **Conceito** | `cerebro/*.md`, carregado inteiro no prompt com cache (016) | Busca (pgvector) só se crescer |
| **Dados e memória por lead** | Um arquivo JSON por lead em `data/local/` (fora do Git) (014) | Supabase na hospedagem (5b) |

A memória guarda conversa, dados de qualificação, faixa, aprovação, ids do CRM, mensagem do Slack, estado do follow-up e
um registro de eventos (para auditar e medir). Uma trava por lead impede que dois canais mexam nela ao mesmo tempo.

### HubSpot (CRM, decisão 033)

- Contato (por e-mail ou telefone), empresa (reaproveitada quando já existe: duas pessoas da mesma empresa, uma empresa) e
  negócio no funil próprio **"BRAX Inbound"**: Qualificado – app · Reunião solicitada · Reunião aprovada · Perdido.
- Campos da BRAX: faixa, motivo, prioridade, sinais de compra, dor, solução atual, motivo da perda, opt-out.
- A etapa do funil é uma **função pura** (`etapa_do_negocio`). Sincroniza depois de cada resposta; se o HubSpot cair,
  o lead fica pendente e a conversa continua.
- Resumo do lead (Sonnet) vira **nota** associada ao contato, à empresa e ao negócio.

### Slack (aprovação humana e alertas, decisão 034)

- **Socket Mode**: a conexão sai do computador; sem endereço público.
- Pedido de aprovação com resumo e botões **Aprovar · Sugerir outro horário · Indicar o app**. Depois do clique, a IA
  escreve o retorno ao lead (com travas e texto de reserva), ele vai pelo canal da conversa e a mensagem do Slack mostra
  quem decidiu. Um segundo clique não gera um segundo retorno.
- Alerta de **transferência** sem botões; o que o lead disser depois aparece na thread do alerta.

### Follow-up (decisão 028)

Dois lembretes padronizados (1 e 3 dias úteis, só em horário comercial, na mesma thread de e-mail) quando o P.H. fez uma
pergunta e o lead sumiu. Nunca para quem pediu parada, foi encerrado, transferido, bloqueado ou está fora do perfil.
No WhatsApp, fica para depois: fora da janela de 24h, a Meta exige modelos aprovados.

### Avaliação (Fase 6, decisão 039)

- 20 cenários (`evals/cenarios.json`); uma IA faz o lead seguindo uma ficha com fatos fixos.
- O código confere o objetivo (faixa, transferência, opt-out, alertas, vazamentos, custo); um juiz (Sonnet 5) dá notas de
  1 a 5 para tom, uma pergunta por vez, não repetir perguntas, honestidade, guardrails e condução.
- Resultados em `evals/resultados/` e painel em `docs/index.html` (GitHub Pages), com histórico.

## Segurança e privacidade

| Risco | Proteção |
|---|---|
| Chaves e tokens vazarem | Só no `.env` (fora do Git); repositório público conferido antes de cada envio |
| Mensagem maliciosa manipular a IA | A IA não acessa caixa de e-mail nem a Meta (026); guardrail G7 no prompt; texto interno bloqueado antes do envio (024) |
| Alguém se passar pela Meta | Assinatura HMAC conferida em todo aviso do webhook; sem ela, nada é processado |
| Dados sensíveis do lead | Documentos e áudios nunca abertos; o P.H. nunca pede senha, código ou documento (G2) |
| LGPD | Opt-out garantido em código, em todos os canais; só os dados necessários são coletados |
| Custo descontrolado | Limites por lead (mensagens/dia, custo, tamanho) aplicados antes da API (021) |

## Arquivos

| Arquivo | Papel |
|---|---|
| `src/brax_sdr/config.py` | Modelos, limites, links, preços e integrações (único lugar) |
| `src/brax_sdr/agente.py` | O caminho da mensagem: laço com ferramentas e todas as travas pós-modelo |
| `src/brax_sdr/prompt.py`, `cerebro.py` | Instruções do P.H. (com cache) e leitura do cérebro |
| `src/brax_sdr/ferramentas.py`, `roteamento.py` | Ferramentas com validação; tabela do ICP e prioridade |
| `src/brax_sdr/protecao.py`, `guardrails.py`, `mensagens.py` | Proteção antes da API; alertas e bloqueio de texto interno; textos padronizados |
| `src/brax_sdr/memoria.py`, `travas.py` | Memória por lead e trava por lead |
| `src/brax_sdr/gmail.py`, `canal_email.py`, `atendente_email.py` | Canal de e-mail |
| `src/brax_sdr/canal_whatsapp.py`, `webhook_whatsapp.py`, `simulador_whatsapp.py` | Canal de WhatsApp (real e simulado) |
| `src/brax_sdr/followup.py` | Regras e textos do follow-up |
| `src/brax_sdr/crm.py`, `resumo.py` | HubSpot e resumo do lead (Sonnet) |
| `src/brax_sdr/slack_brax.py` | Aprovação, retorno ao lead e alertas no Slack |
| `src/brax_sdr/evals.py`, `painel.py` | Avaliação automática e painel |
| `iniciar_brax.py` | Programa único: WhatsApp + e-mail + Slack + HubSpot |
| `conversar.py`, `simular_whatsapp.py`, `atender_email.py`, `servidor_whatsapp.py` | Terminal, simulador e canais avulsos |
| `autorizar_gmail.py`, `configurar_hubspot.py`, `sincronizar_crm.py`, `diagnosticar_whatsapp.py`, `rodar_evals.py` | Configuração, diagnóstico e evals |
| `tests/` | Mais de 200 testes automáticos, sem chamar nenhuma API (clientes falsos de Claude, Gmail, Meta, HubSpot e Slack) |

## Hospedagem (5b, planejada)

Hoje tudo roda no computador (e-mail sem endereço público, WhatsApp por túnel). Na hospedagem (Railway ou Render), o
`iniciar_brax.py` vira o serviço único, a memória vai para o Supabase (os servidores apagam arquivos locais) e a proteção
contra empresas duplicadas no HubSpot precisa de uma trava entre processos.

## Limitações conhecidas e próximos passos

- Responder ao lead de dentro do Slack (hoje o vendedor usa os próprios canais) (038).
- Agenda real ligada ao CRM (reuniões do HubSpot), deixada de fora por privacidade (035).
- Follow-up no WhatsApp com modelos aprovados pela Meta (030).
- Comparação Haiku × Sonnet × Opus nos evals (012).
- Pesquisa automática da empresa e do decisor (planejada desde a Fase 1).
