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
| Conversa com o lead | `claude-haiku-4-5-20251001` | Rápido e barato, suficiente para diálogo guiado |
| Tarefas complexas (resumo para o executivo, pesquisa) e avaliações | `claude-sonnet-5` | Mais capacidade de raciocínio |

### 3. Ferramentas previstas

| Ferramenta | O que faz | Fase |
|---|---|---|
| `consultar_cerebro` | Busca trechos relevantes nos arquivos do cérebro | 2 |
| `registrar_qualificacao` | Salva os dados descobertos (funcionários, gasto, setor, persona) | 2 |
| `rotear_lead` | Aplica a tabela de roteamento e registra faixa + motivo | 2 |
| `pesquisar_empresa` | Busca informações públicas da empresa e do decisor | 2 ou 5 |
| `enviar_link_app` | Envia o link oficial de abertura de conta (self-service) | 3/4 |
| `solicitar_aprovacao` | Pede aprovação humana no Slack antes de agendar com executivo | 5 |
| `atualizar_crm` | Cria/atualiza contato, empresa e negócio no HubSpot | 5 |
| `transferir_para_humano` | Encaminha a conversa para uma pessoa | 2 (simulado) / 5 |
| `registrar_opt_out` | Registra pedido de parada (LGPD) e bloqueia novos contatos | 2 (simulado) / 5 |
| `agendar_followup` | Programa uma nova mensagem se o lead sumir | 3/4 |

### 4. Cérebro: três camadas

| Camada | Onde fica | Conteúdo |
|---|---|---|
| **Conceito** | `cerebro/*.md` no GitHub | Empresa, produto, ICP, objeções, tom de voz, regras. Versionado, revisável em PR |
| **Dados** | Supabase (Postgres) | Leads, empresas, conversas, qualificação |
| **Memória por lead** | Supabase | Histórico de mensagens e resumo do lead, lido **antes de cada resposta**, em qualquer canal |

Na Fase 2 o cérebro pode ser carregado inteiro no prompt (são poucos arquivos). Busca semântica
(pgvector no Supabase) só entra se o volume de conteúdo justificar.

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
