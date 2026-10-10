# Esquema do banco para o painel (Supabase, somente leitura)

> Fonte: `supabase/painel.sql` (decisão 046). O painel usa **só** as três visões abaixo, com a chave pública
> (anon/publishable) e um usuário logado. Ele não lê a tabela `leads` diretamente e não grava nada.
> Todos os dados são fictícios (decisão 045).

## Regras de acesso

| Quem | O que vê |
|---|---|
| Visitante **sem login** (chave anon, papel `anon`) | Nada: as visões não têm permissão para `anon`, e a tabela não tem regra de leitura para ele |
| Usuário **logado** (chave anon + sessão do Supabase Auth, papel `authenticated`) | Lê as três visões. Não pode criar, alterar nem apagar nada (não existe regra de escrita) |
| Servidor do P.H. (chave secreta) | Lê e grava a tabela `leads`. Nunca é usada no painel |

Os usuários do painel são criados pelo administrador no Supabase; o cadastro público está desligado.

## Relações

```
painel_leads (id) ──< painel_mensagens (lead_id)   uma conversa por lead, ordenada por "ordem"
                 └──< painel_eventos (lead_id)     uma linha do tempo por lead, ordenada por "quando"
```

## `painel_leads`: um lead por linha

| Coluna | Tipo | Significado | Exemplos |
|---|---|---|---|
| `id` | text | Identificador do lead: telefone (WhatsApp) ou e-mail; nos testes, um apelido | `5511900000099`, `lumen` |
| `canal` | text | Canal de origem | `whatsapp`, `email` |
| `nome_contato` | text | Nome da pessoa (pode ser vazio) | `Rafael` |
| `empresa` | text | Nome da empresa (pode ser vazio) | `Nuvem Azul` |
| `cargo` | text | Cargo informado | `CFO`, `Sócio/Founder` |
| `setor` | text | Setor informado | `SaaS`, `e-commerce` |
| `tipo_empresa` | text | Tipo jurídico | `ltda`, `sa`, `outro_cnpj`, `mei`, `sem_cnpj`, `pessoa_fisica` |
| `funcionarios` | integer | Número aproximado de pessoas | `12` |
| `gasto_mensal` | numeric | Gasto mensal estimado com cartão e despesas, em reais | `15000` |
| `dor` | text | Principal motivo do contato | `Cartão do sócio e reembolso manual` |
| `solucao_atual` | text | Banco ou ferramenta usada hoje | `Cartão pessoal do sócio` |
| `sinais_de_compra` | jsonb (lista de textos) | Sinais citados pelo lead | `["rodada_recente", "gastos_em_dolar"]` |
| `motivo_encerramento` | text | Por que a conversa acabou sem venda | `sem_interesse` |
| `faixa` | text | Resultado da qualificação, decidido pelo código | `self_service`, `executivo`, `fora_do_icp`, `humano`, vazio (ainda qualificando) |
| `motivo_faixa` | text | Explicação da faixa | `22 funcionários (> 20)`, `mei` |
| `aprovacao` | text | Pedido de reunião com executivo (aprovado pelo time no Slack) | `pendente`, `aprovada`, `novo_horario`, `recusada`, vazio |
| `prioridade` | integer | Pontos por sinais de compra (maior = mais quente) | `0` a `13` |
| `opt_out` | boolean | Pediu para não receber mais mensagens (LGPD) | `false` |
| `encerrada` | boolean | Conversa encerrada | `true` |
| `transferido_para_vendedor` | boolean | Passado para um vendedor humano | `false` |
| `sem_resposta` | boolean | Recebeu todos os lembretes (follow-up) e não respondeu | `false` |
| `custo_total_usd` | numeric | Custo estimado de IA com este lead, em dólares | `0.0312` |
| `total_mensagens` | integer | Mensagens no histórico (inclui as internas) | `7` |
| `etapa` | text | Etapa do funil, calculada pela visão | ver tabela abaixo |
| `criado_em` | timestamptz | Primeiro contato | `2026-10-07 15:20:00+00` |
| `atualizado_em` | timestamptz | Última atividade | `2026-10-07 15:35:14+00` |

### Etapas do funil (`etapa`), na ordem de exibição

| Valor | Rótulo | Quando |
|---|---|---|
| `em_qualificacao` | Em qualificação | Ainda sem faixa |
| `qualificado_app` | Qualificado (app) | Faixa self-service, ou executivo com reunião recusada (indicado o app) |
| `reuniao_solicitada` | Reunião solicitada | Executivo aguardando a aprovação do time |
| `reuniao_aprovada` | Reunião aprovada | Executivo com reunião aprovada (ou com outro horário sugerido) |
| `com_vendedor` | Com vendedor | Transferido para um humano ou setor de análise especial |
| `fora_do_perfil` | Fora do perfil | MEI, pessoa física, sem CNPJ ou só quer crédito |
| `perdido` | Perdido | Sem interesse, pediu para parar ou não respondeu aos lembretes |

### Faixas (`faixa`)

| Valor | Rótulo |
|---|---|
| `self_service` | Self-service (app) |
| `executivo` | Executivo |
| `fora_do_icp` | Fora do perfil |
| `humano` | Análise humana |
| vazio | Em qualificação |

## `painel_mensagens`: a conversa

| Coluna | Tipo | Significado |
|---|---|---|
| `lead_id` | text | Liga ao `painel_leads.id` |
| `ordem` | integer | Posição na conversa (ordenar crescente). Pode pular números: mensagens internas não aparecem |
| `autor` | text | `lead` ou `ph` (o assistente virtual) |
| `texto` | text | Texto da mensagem, com quebras de linha. No WhatsApp, pode começar com `[Nome no perfil do WhatsApp: ...]` |

## `painel_eventos`: a linha do tempo

| Coluna | Tipo | Significado |
|---|---|---|
| `lead_id` | text | Liga ao `painel_leads.id` |
| `quando` | timestamptz | Momento do evento |
| `tipo` | text | Tipo do evento (ver abaixo) |
| `detalhe` | text | Detalhe livre (ex.: o motivo da faixa) |

Tipos mais comuns e rótulos sugeridos: `qualificacao` (Dados registrados), `roteamento` (Faixa definida),
`aprovacao_aprovada` / `aprovacao_novo_horario` / `aprovacao_recusada` / `aprovacao_pendente` (Aprovação do time),
`transferencia_humano` (Transferido para vendedor), `opt_out` (Pediu para parar), `conversa_encerrada` (Conversa encerrada),
`conversa_reaberta` (Conversa reaberta), `followup` (Lembrete enviado), `sem_resposta` (Sem resposta aos lembretes),
`retorno_enviado` (Retorno do time enviado ao lead), `alerta_guardrail` / `alerta_estilo` / `alerta_confiabilidade`
(Alerta de qualidade), `vazamento_bloqueado` (Mensagem bloqueada pela segurança), `mensagem_encurtada` (Mensagem encurtada),
`erro_ferramenta` / `crm_erro` (Erro técnico). Outros tipos podem aparecer: mostrar o próprio nome.
