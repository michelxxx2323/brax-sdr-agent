# Arquitetura

> Documento vivo. Descreve o desenho **alvo** do sistema; cada fase implementa uma parte.
> O porquê de cada escolha está em [decisoes.md](decisoes.md).

## Visão geral

```
WhatsApp (Meta Cloud API) ─┐
                           ├──> Agente SDR "P.H." (Claude API + ferramentas)
E-mail (Gmail API) ────────┘            │
                                        ├── Cérebro (Markdown no GitHub + Supabase)
                                        ├── Pesquisa (empresa e decisor)
                                        ├── CRM (HubSpot gratuito)
                                        └── Aprovação humana (Slack)
```

## Componentes

### 1. Canais (entrada e saída)

| Canal | Tecnologia | Como chega a mensagem | Fase |
|---|---|---|---|
| Terminal | Python (entrada/saída padrão) | Digitação local, para testes | 2 |
| E-mail | Gmail API | Leitura periódica da caixa de entrada ou notificação | 3 |
| WhatsApp | Meta Cloud API (número de teste) | Webhook HTTP da Meta | 4 |

Cada canal só **traduz** a mensagem para um formato comum (`lead`, `canal`, `texto`, `data`) e entrega ao agente.
O agente não sabe de onde a mensagem veio além do campo `canal`, o que permite ajustar o tom (WhatsApp curto, e-mail mais completo).

### 2. Agente P.H.

Um único agente usando a Claude API com **ferramentas (tools)**. A cada mensagem recebida:

1. Identifica o lead (telefone ou e-mail) e **carrega o histórico** dele (memória por lead).
2. Monta o contexto: instruções do sistema + trechos relevantes do cérebro + histórico + nova mensagem.
3. Chama o modelo de conversa (leve). O modelo pode decidir usar ferramentas.
4. Executa as ferramentas pedidas, devolve o resultado ao modelo e repete até ter a resposta final.
5. Aplica as checagens de guardrails na resposta antes de enviar.
6. Salva a mensagem e a resposta no histórico e atualiza o CRM.

**Modelos** (definidos em um único arquivo de configuração):

| Uso | Modelo | Por quê |
|---|---|---|
| Conversa com o lead | `claude-haiku-4-5` | Rápido e barato, suficiente para diálogo guiado (comparação na Fase 6, decisão 012) |
| Tarefas complexas (resumo para o executivo, pesquisa) e avaliações | `claude-sonnet-5` | Mais capacidade de raciocínio |

### 3. Ferramentas

| Ferramenta | O que faz | Status |
|---|---|---|
| `registrar_qualificacao` | Salva os dados descobertos (funcionários, gasto, setor, persona, sinais de compra) | ✅ Fase 2 |
| `rotear_lead` | Aplica a tabela de roteamento **em código** e registra faixa + motivo (decisão 013) | ✅ Fase 2 |
| `solicitar_aprovacao_executivo` | Pede aprovação humana antes de agendar com executivo | ✅ Fase 2 (terminal) → Slack na Fase 5 |
| `transferir_para_humano` | Encaminha a conversa para uma pessoa | ✅ Fase 2 (registro local) → Fase 5 |
| `registrar_opt_out` | Registra pedido de parada (LGPD); o código bloqueia novas respostas | ✅ Fase 2 (registro local) → Fase 5 |
| `atualizar_crm` | Cria/atualiza contato, empresa e negócio no HubSpot | Fase 5 |
| `agendar_followup` | Programa uma nova mensagem se o lead sumir | Fases 3/4 |
| `pesquisar_empresa` | Busca informações públicas da empresa e do decisor | A definir |
| `consultar_cerebro` | Busca trechos relevantes do cérebro | Só se o cérebro crescer (decisão 016) |

O link do app (self-service) e o link de agenda (executivo) são devolvidos pelas ferramentas `rotear_lead` e
`solicitar_aprovacao_executivo`: o modelo nunca inventa um link, e a agenda só é liberada depois da aprovação humana.

### Implementação atual (Fase 2)

| Arquivo | Papel |
|---|---|
| `src/brax_sdr/config.py` | Modelos, limites de roteamento, links e tabela de preços (único lugar) |
| `src/brax_sdr/cerebro.py` | Lê `cerebro/*.md` em ordem fixa (necessário para o cache) |
| `src/brax_sdr/prompt.py` | Instruções do P.H.: bloco fixo com cache + bloco de contexto do lead |
| `src/brax_sdr/roteamento.py` | Tabela de roteamento e pontuação de prioridade |
| `src/brax_sdr/ferramentas.py` | Definição e execução das ferramentas, com validação dos dados |
| `src/brax_sdr/guardrails.py` | Checagem automática das respostas (alertas G1 a G4) |
| `src/brax_sdr/memoria.py` | Memória por lead (arquivo JSON local; Supabase depois) |
| `src/brax_sdr/agente.py` | Laço de conversa com ferramentas (decisão 015) |
| `src/brax_sdr/terminal.py` | Interface de terminal com aprovação humana simulada |

### 4. Cérebro: três camadas

| Camada | Onde fica | Conteúdo |
|---|---|---|
| **Conceito** | `cerebro/*.md` no GitHub | Empresa, produto, ICP, objeções, tom de voz, regras. Versionado, revisável em PR |
| **Dados** | Supabase (Postgres) | Leads, empresas, conversas, qualificação |
| **Memória por lead** | Supabase | Histórico de mensagens e resumo do lead, lido **antes de cada resposta**, em qualquer canal |

Na Fase 2 o cérebro é carregado inteiro no prompt, com cache (decisão 016), e a memória por lead fica em arquivo
local (decisão 014). Busca semântica (pgvector no Supabase) só entra se o volume de conteúdo justificar.

### 5. Dados (rascunho do modelo no Supabase)

| Tabela | Campos principais |
|---|---|
| `leads` | id, nome, email, telefone, cargo, persona, empresa_id, status, faixa, motivo_faixa, opt_out, criado_em |
| `empresas` | id, nome, cnpj, setor, funcionarios, gasto_mensal_estimado, estagio, sinais_de_compra |
| `mensagens` | id, lead_id, canal, direcao (entrada/saída), texto, criado_em |
| `resumos` | lead_id, resumo, atualizado_em |

### 6. CRM (HubSpot) e aprovação humana (Slack)

- O Supabase é a fonte de verdade da conversa; o HubSpot recebe o que o time comercial precisa ver:
  contato, empresa, faixa, motivo e resumo da conversa.
- Antes de agendar com um executivo, o P.H. publica no Slack um resumo do lead com botões **Aprovar / Recusar**.
  Só depois da aprovação o convite é enviado.

### 7. Observabilidade e avaliação (Fase 6)

- Conversas de teste com leads simulados (personas do ICP e casos fora do perfil).
- Um modelo mais forte atua como **juiz** e dá notas: qualificou certo? roteou certo? respeitou os guardrails? tom adequado?
- Painel com taxa de qualificação, distribuição por faixa e violações de guardrail.

## Fluxo típico (exemplo)

```
Lead (WhatsApp): "Oi, quero saber dos cartões corporativos"
  → canal WhatsApp normaliza a mensagem
  → P.H. carrega histórico (vazio) e o cérebro
  → P.H. se apresenta como assistente virtual, oferece humano e faz 1 pergunta
  → ... 3 a 5 trocas depois: 35 funcionários, gasto de R$ 80 mil/mês
  → rotear_lead → faixa "Executivo"
  → solicitar_aprovacao no Slack → aprovado
  → P.H. envia o link de agenda do executivo
  → atualizar_crm com faixa, motivo e resumo
```

## Hospedagem

Até a Fase 2, tudo roda local. A partir dos canais (Fases 3 e 4), o serviço precisa de uma URL pública
para receber webhooks: Railway ou Render (decisão na Fase 3).
