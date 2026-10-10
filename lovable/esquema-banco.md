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
| `total_mensagens` | integer | Mensagens no histórico (inclui as internas; para contar as visíveis, use `painel_mensagens`) | `7` |
| `etapa` | text | Etapa do funil, calculada pela visão | ver tabela abaixo |
| `criado_em` | timestamptz | Primeiro contato | `2026-10-07 15:20:00+00` |
| `atualizado_em` | timestamptz | Última atividade | `2026-10-07 15:35:14+00` |
| `resumo` | text | Resumo de 2 a 4 frases da conversa, escrito pela IA quando a faixa é definida ou a conversa é encerrada (pode ser vazio) | `Rafael, da Nuvem Azul (SaaS, 12 pessoas), quer organizar os gastos do time. Indicado para abrir a conta pelo app.` |
| `resumo_em` | timestamptz | Quando o resumo foi gerado | `2026-10-09 18:02:11+00` |
| `temperatura` | text | Calor do lead, calculado a partir de `prioridade` | `quente`, `morno`, `frio` |
| `hubspot_contato_id` | text | ID do contato no HubSpot (vazio se ainda não sincronizado) | `253636892599` |
| `hubspot_empresa_id` | text | ID da empresa no HubSpot | `59108454708` |
| `hubspot_negocio_id` | text | ID do negócio no HubSpot (só leads qualificados ou perdidos depois de qualificados) | `65799390904` |
| `ultima_mensagem` | text | Texto da última mensagem da conversa, para a lista de conversas | `Valeu, vou abrir agora mesmo` |
| `ultima_mensagem_autor` | text | Quem mandou a última mensagem | `lead`, `ph` |
| `ultima_mensagem_quando` | timestamptz | Horário da última mensagem (vazio em conversas antigas, sem horário gravado) | `2026-10-09 18:02:09+00` |

### Temperatura (`temperatura`), hipótese a calibrar

| Valor | Rótulo | Regra (pontos de `prioridade`) |
|---|---|---|
| `quente` | 🔥 Quente | 5 ou mais (ex.: quem decide + rodada recente) |
| `morno` | 🌤 Morno | 2 a 4 (um sinal forte, ou só ser quem decide) |
| `frio` | ❄️ Frio | 0 ou 1 |

Pontos: rodada recente 3; contratando rápido 2; primeira pessoa de finanças 2; gastos em dólar 2; novo escritório 1;
insatisfeito com o banco 1; quem conversa é quem decide 2.

### Links para o HubSpot

Montar com o ID da conta do HubSpot (informado à parte, não fica no repositório):
- Contato: `https://app.hubspot.com/contacts/<ID_DA_CONTA>/record/0-1/<hubspot_contato_id>`
- Empresa: `https://app.hubspot.com/contacts/<ID_DA_CONTA>/record/0-2/<hubspot_empresa_id>`
- Negócio: `https://app.hubspot.com/contacts/<ID_DA_CONTA>/record/0-3/<hubspot_negocio_id>`

Mostrar o botão só quando o ID existir.

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
| `texto` | text | Texto da mensagem, com quebras de linha (o prefixo técnico do nome no perfil do WhatsApp já vem removido) |
| `quando` | timestamptz | Data e hora da mensagem. **Pode ser vazio** nas conversas antigas (antes de 09/10/2026): nesse caso, não mostrar hora |

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
`erro_ferramenta` / `crm_erro` / `resumo_erro` (Erro técnico). Outros tipos podem aparecer: mostrar o próprio nome.

## Qualidade: resultados dos evals (decisão 050)

Cada bateria de avaliação automática (`rodar_evals.py`) roda 20 conversas simuladas: uma IA faz o papel do lead, o código
confere o resultado objetivo (faixa, transferência, opt-out, vazamentos...) e um juiz (Sonnet 5) dá notas de 1 a 5.
Todas as conversas são simuladas e fictícias.

### `painel_evals_baterias`: uma bateria por linha (evolução da qualidade)

| Coluna | Tipo | Significado |
|---|---|---|
| `bateria` | text | Identificador da bateria (data e modelo) |
| `data` | timestamptz | Quando rodou |
| `modelo_conversa` | text | Modelo do P.H. avaliado (ex.: `claude-haiku-4-5`) |
| `cenarios` | integer | Quantos cenários (20 nas completas; a piloto teve 3) |
| `aprovados` | integer | Cenários com todas as verificações objetivas certas |
| `taxa_aprovacao` | numeric | aprovados ÷ cenários (0 a 1) |
| `nota_media` | numeric | Média das notas do juiz (1 a 5) |
| `cenarios_com_alerta_de_guardrail` | integer | Cenários com algum alerta G1 a G4 |
| `custo_total_usd` | numeric | Custo da bateria (P.H. + lead simulado + juiz) |
| `custo_medio_ph_usd` | numeric | Custo médio do P.H. por conversa |

### `painel_evals`: um cenário de uma bateria por linha

| Coluna | Tipo | Significado |
|---|---|---|
| `bateria`, `data`, `modelo_conversa` | | Como acima (liga a `painel_evals_baterias.bateria`) |
| `cenario` | text | Id do cenário (ex.: `mei`, `pede_humano`) |
| `titulo` | text | Nome legível do cenário |
| `canal` | text | `whatsapp` ou `email` |
| `passou` | boolean | Todas as verificações objetivas certas |
| `falhas` | jsonb (lista) | Verificações que falharam (ex.: `["faixa", "motivo_faixa"]`) |
| `nota_media` | numeric | Média das 6 notas do juiz (vazio se o juiz falhou) |
| `nota_tom_e_clareza`, `nota_uma_pergunta_por_vez`, `nota_nao_repete_perguntas`, `nota_honestidade`, `nota_guardrails`, `nota_conducao` | integer | Notas do juiz por critério (1 a 5) |
| `problemas` | jsonb (lista de textos) | Problemas apontados pelo juiz |
| `resumo_juiz` | text | Avaliação geral em uma frase |
| `alertas` | jsonb (lista de textos) | Alertas de guardrail e de estilo durante a conversa |
| `esperado`, `obtido` | jsonb | O resultado esperado do cenário e o que aconteceu |
| `mensagens_do_lead` | integer | Quantas mensagens o lead simulado mandou |
| `custo_usd`, `custo_ph_usd` | numeric | Custo do cenário (total e só do P.H.) |
| `conversa` | jsonb | Lista de pares `["lead" ou "ph", "texto"]`, na ordem |

Rótulos dos critérios: tom e clareza; uma pergunta por vez; não repete perguntas; honestidade; guardrails; condução.

