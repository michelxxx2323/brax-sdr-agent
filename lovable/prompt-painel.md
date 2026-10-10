# Prompt inicial do painel comercial no Lovable (Fase 7, decisão 046)

> Como usar: crie o projeto no Lovable, conecte o projeto `brax-sdr` do Supabase e cole o texto abaixo (da linha
> "Crie um painel..." até o fim) como primeira mensagem. Os ajustes seguintes são feitos conversando com o Lovable,
> uma tela por vez.

---

Crie um painel web, em português do Brasil, para o time comercial da BRAX acompanhar o trabalho do P.H., um assistente
virtual de pré-vendas (SDR) que atende leads por WhatsApp e e-mail. A BRAX é uma fintech fictícia (conta PJ e cartões
corporativos para startups) e todos os dados são fictícios.

## Regras obrigatórias sobre o banco (Supabase já existente)

- O banco já existe e é usado por outro sistema em produção. **Não crie, altere ou apague tabelas, colunas, visões,
  funções, políticas (RLS), gatilhos ou dados. Não rode migrações. Não crie Edge Functions.**
- O painel é **somente leitura**. Use apenas estas três visões, com o cliente do Supabase e a chave pública (anon/publishable):
  - `painel_leads`: um lead por linha. Colunas: `id`, `canal` (whatsapp | email), `nome_contato`, `empresa`, `cargo`,
    `setor`, `tipo_empresa`, `funcionarios`, `gasto_mensal` (R$/mês), `dor`, `solucao_atual`, `sinais_de_compra` (lista),
    `motivo_encerramento`, `faixa` (self_service | executivo | fora_do_icp | humano | vazio), `motivo_faixa`,
    `aprovacao` (pendente | aprovada | novo_horario | recusada | vazio), `prioridade` (número), `opt_out`, `encerrada`,
    `transferido_para_vendedor`, `sem_resposta`, `custo_total_usd`, `total_mensagens`, `etapa`, `criado_em`, `atualizado_em`.
  - `painel_mensagens`: a conversa. Colunas: `lead_id`, `ordem`, `autor` (lead | ph), `texto`. Ordenar por `ordem`.
  - `painel_eventos`: a linha do tempo. Colunas: `lead_id`, `quando`, `tipo`, `detalhe`.
- Etapas (`etapa`) e rótulos para exibir: `em_qualificacao` → "Em qualificação", `qualificado_app` → "Qualificado (app)",
  `reuniao_solicitada` → "Reunião solicitada", `reuniao_aprovada` → "Reunião aprovada", `com_vendedor` → "Com vendedor",
  `fora_do_perfil` → "Fora do perfil", `perdido` → "Perdido".
- Faixas: `self_service` → "Self-service (app)", `executivo` → "Executivo", `fora_do_icp` → "Fora do perfil",
  `humano` → "Análise humana".

## Acesso

- Tela de login com e-mail e senha (Supabase Auth). **Sem cadastro, sem "criar conta"**: os usuários são criados pelo
  administrador no Supabase. Sem login, nenhuma tela do painel aparece.
- Botão de sair no menu.

## Telas

1. **Visão geral**
   - Cartões no topo: total de leads; leads qualificados (faixa self_service ou executivo); taxa de qualificação
     (qualificados ÷ leads com faixa definida); reuniões aprovadas; leads com vendedor; custo médio de IA por lead (US$).
   - Funil por etapa (barras horizontais, na ordem das etapas acima).
   - Leads por faixa e leads por canal.
   - Leads criados por dia (últimos 30 dias).
2. **Leads**
   - Tabela: empresa, contato, canal, faixa, etapa, funcionários, gasto mensal, prioridade, última atualização.
   - Busca por empresa ou contato; filtros por faixa, etapa e canal; ordenar por última atualização (padrão) ou prioridade.
   - Clicar numa linha abre o detalhe.
3. **Detalhe do lead**
   - Cabeçalho com empresa, contato, cargo, canal, faixa, etapa e motivo da faixa.
   - Bloco de qualificação: tipo de empresa, setor, funcionários, gasto mensal, dor, solução atual, sinais de compra,
     prioridade, custo de IA.
   - A conversa no estilo de chat: mensagens do lead à esquerda, do P.H. à direita, com quebras de linha preservadas.
   - Linha do tempo com os eventos, do mais antigo ao mais novo.

## Visual

- Limpo e profissional, com bastante espaço em branco, tons neutros e um verde-escuro como cor de destaque.
- Modo claro e escuro. Funciona bem no celular.
- Valores em reais no formato brasileiro (R$ 15.000) e datas como 07/10/2026 14:30.
- Rodapé discreto em todas as telas: "Dados fictícios · A BRAX é uma empresa fictícia criada para um projeto de portfólio."
