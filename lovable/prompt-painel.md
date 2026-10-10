# Painel do P.H. (BRAX): ajustes no banco + prompts do Lovable

Layout de referência: a **experiência de WhatsApp** do hub da Woba (lista de conversas + chat) com o
**painel de análise do lead** à direita, no estilo das plataformas de atendimento com IA.
Identidade visual própria da BRAX: inspirar-se no layout, não copiar marcas, cores ou ícones de ninguém.

---

## Parte A: ajustes no banco (feitos antes do Lovable)

✅ **Feito** em 09/10/2026 (decisão 048; diário em `docs/validacao-fase7.md`, teste 3). O pedido feito ao Claude Code:

> Vou construir no Lovable um painel em três colunas (lista de conversas, chat estilo WhatsApp e painel de
> análise do lead). Para isso, preciso destes ajustes. Explique cada um antes de fazer, registre as decisões
> no `docs/decisoes.md` e, no fim, atualize `supabase/painel.sql` e `lovable/esquema-banco.md`.
>
> 1. **Horário de cada mensagem.** Gravar a data e hora de cada mensagem no estado do lead (lead e P.H.) e
>    expor como `quando` (timestamptz) em `painel_mensagens`. Mensagens antigas sem horário podem ficar nulas.
> 2. **Resumo da conversa.** Gerar e guardar um resumo curto (2 a 4 frases) da conversa sempre que a faixa
>    for definida ou a conversa for encerrada, usando o modelo leve. Expor como `resumo` em `painel_leads`.
> 3. **Temperatura do lead.** Calcular na view `painel_leads`, a partir de `prioridade`, uma coluna
>    `temperatura` (`quente`, `morno`, `frio`). Proponha os limites e registre como hipótese a calibrar.
> 4. **Links do HubSpot.** Se o código já guarda os IDs de contato e de negócio do HubSpot, expor
>    `hubspot_contato_id` e `hubspot_negocio_id` em `painel_leads`. Se não guarda, passe a guardar.
> 5. **Última mensagem.** Expor em `painel_leads` as colunas `ultima_mensagem` (texto) e
>    `ultima_mensagem_autor` (`lead` ou `ph`), para a lista de conversas não precisar carregar todas as mensagens.
>
> Mantenha tudo somente leitura para o painel e as mesmas regras de acesso (views com security_invoker,
> nada para anon). Rode os testes e me mostre o que mudou.

**Diferenças em relação ao pedido:**
- Acesso: as visões **não** usam `security_invoker`. Com ele, o usuário logado precisaria ler a tabela `leads`
  inteira (com o estado interno), que foi o problema achado na revisão da decisão 047. As visões rodam com a
  permissão do dono, a tabela fica fechada e nada vai para anon (verificação: `verificar_acesso_painel.py`, 11/11).
- A mais: `hubspot_empresa_id`, `ultima_mensagem_quando` e `resumo_em`. O prefixo técnico
  `[Nome no perfil do WhatsApp: ...]` já sai do texto nas visões.

---

## Parte B: prompts do Lovable

> Crie o projeto no Lovable conectado ao **projeto Supabase existente** (`brax-sdr`) e ao GitHub.
> Confirme a conexão antes (pergunte ao Lovable qual projeto Supabase está conectado; o ID deve ser o do `.env`).
> Cole o **Prompt 1** e, logo abaixo, o conteúdo inteiro de `lovable/esquema-banco.md`.
> Só envie o Prompt 2 quando o 1 estiver funcionando, e o 3 depois do 2.
> Quando o Lovable for montar os botões do HubSpot, informe a ele o **ID da conta do HubSpot** (o número depois de
> `/contacts/` na barra de endereço do HubSpot). Ele não fica no repositório.

### Prompt 1: login e tela de Conversas

Quero um painel web interno, em português do Brasil, para o time comercial da **BRAX**, uma fintech
**fictícia** de conta PJ para startups. O painel mostra as conversas do **P.H.**, um assistente virtual de
IA de pré-vendas (SDR) que atende leads por WhatsApp e e-mail, qualifica e roteia cada um.

Este é um **case de portfólio** com dados fictícios. Mostre no topo: logo em texto "BRAX", avatar do P.H.
(iniciais "PH" num círculo), o título "P.H. · SDR de IA" e o subtítulo "Conversas com leads".

#### Regras obrigatórias
- O painel é **somente leitura**. Nenhum campo de digitação, botão de enviar ou operação que grave,
  altere ou apague dados.
- Use **apenas** as visões `painel_leads`, `painel_mensagens` e `painel_eventos`. **Nunca** consulte a
  tabela `leads` (o banco recusa: o usuário do painel não tem acesso a ela).
- **Não crie tabelas, colunas, visões, funções, políticas, Edge Functions nem migrações** no Supabase.
  O banco já está pronto e é usado por outro sistema em produção.
- Use só a chave pública (anon/publishable), **nunca** a secreta (service_role).
- Login com **Supabase Auth, e-mail e senha**. Sem tela de cadastro e sem "esqueci a senha" (os usuários são
  criados pelo administrador). Sem login, nada além do login é acessível. Botão "Sair" no topo.

#### Formatação
- Datas e horas em America/Sao_Paulo, formato brasileiro. Na lista, hoje mostra só a hora (22:44);
  ontem mostra "Ontem"; antes disso, a data (07/10).
- Reais como R$ 15.000; custo de IA como US$ 0,0312.
- Mostre sempre os **rótulos** em português do esquema, nunca os valores técnicos. Vazios aparecem como "—".

#### Abas no topo
"Conversas" (esta tela) e "Métricas" (vazia por enquanto).

#### Tela Conversas: três colunas

**Coluna 1: lista de conversas** (como a lista do WhatsApp)
- Busca por nome, empresa ou id (o id é o telefone, no WhatsApp, ou o e-mail).
- Chips de filtro rápido: Todas, WhatsApp, E-mail. Botão "Filtros" com etapa, faixa, temperatura e período
  (`criado_em`, com duas datas).
- Cada item: avatar com iniciais (cor estável derivada do id), nome do contato (ou o id, se não houver nome),
  horário de `atualizado_em`, prévia de `ultima_mensagem` em uma linha (com "✓" quando `ultima_mensagem_autor`
  for `ph`), e pequenas etiquetas: canal, etapa e faixa.
- Ordenada por `atualizado_em`, mais recente primeiro. Item selecionado destacado.

**Coluna 2: chat**
- Cabeçalho: avatar, nome, e-mail ou telefone (o id), etiqueta de canal; e um interruptor
  **"Mostrar bastidores da IA"**, desligado por padrão.
- Fundo levemente texturizado, no clima do WhatsApp. Mensagens do **lead à esquerda em balões brancos**;
  do **P.H. à direita em balões verde-claro**; horário (`quando`) no canto inferior de cada balão;
  quebras de linha preservadas. O texto já vem limpo das visões (sem prefixos técnicos).
- Ordene as mensagens por `ordem`. Separadores de data centralizados ("23 de setembro de 2026") quando o dia
  muda, usando `quando`.
- **Conversas antigas não têm horário** (`quando` vazio): nesses balões, não mostre hora nem separador de data.
- Com **"Mostrar bastidores da IA" ligado**, intercale os eventos de `painel_eventos` na conversa, na ordem
  de `quando`, como pílulas centralizadas e discretas (ex.: "Faixa definida: Executivo · 22 funcionários (> 20)").
  Se a conversa tiver mensagens sem horário, não intercale: mostre os eventos só na aba "Linha do tempo".
  Eventos de qualidade e segurança (`alerta_*`, `vazamento_bloqueado`, `erro_ferramenta`, `crm_erro`,
  `resumo_erro`) em cor de alerta.
- No rodapé, no lugar da caixa de digitação, uma barra fixa: "🔒 Somente leitura · histórico do P.H. · canal: <canal>".

**Coluna 3: análise do lead**, com abas "Resumo", "Dados" e "Linha do tempo"
- Topo: nome, cargo e empresa; botões **"Ver contato"** e **"Ver negócio"** que abrem o HubSpot em nova aba
  quando houver `hubspot_contato_id` / `hubspot_negocio_id` (escondidos quando vazios). O formato do link está
  no esquema; o ID da conta do HubSpot eu informo à parte.
- **Resumo**:
  - "Resumo da conversa" com o texto de `resumo` (ou "Resumo ainda não gerado").
  - "Análise do lead": **temperatura** (ícone + rótulo Quente/Morno/Frio) e **prioridade** num medidor
    semicircular de 0 a 13.
  - "Roteamento": etapa e faixa em badges, com `motivo_faixa` abaixo.
  - "Qualificação": checklist dos seis dados que o P.H. precisa coletar (tipo de empresa, funcionários,
    gasto mensal, cargo/decisor, dor e solução atual), com ✓ e o valor quando preenchido, ou
    "falta descobrir" em cinza quando vazio. Mostre o progresso no título ("4 de 6").
  - "Sinais de compra" como chips (trocar `_` por espaço e capitalizar).
- **Dados**: todos os campos do lead em pares rótulo/valor, mais os indicadores de opt-out (LGPD), sem resposta,
  transferido para vendedor, custo de IA e total de mensagens.
- **Linha do tempo**: todos os eventos em ordem cronológica, com os rótulos do esquema.

#### Visual
Fintech B2B moderna: limpa, clara, uma cor de destaque própria da BRAX para botões e seleção, e o verde-claro
reservado aos balões do P.H. Cantos arredondados, sombras suaves. Modo claro e escuro. No celular, mostrar uma
coluna por vez (lista → chat → análise, com botão de voltar). Rodapé discreto: "Dados fictícios · A BRAX é uma
empresa fictícia criada para um projeto de portfólio."

[COLE AQUI O CONTEÚDO DE lovable/esquema-banco.md]

---

### Prompt 2: aba Métricas

Agora preencha a aba **Métricas**. Calcule tudo no front a partir de `painel_leads` e `painel_eventos`, sem
criar nada no banco. Filtro de período no topo (7 dias, 30 dias, tudo), aplicado sobre `criado_em`.

**Cartões:**
- **Leads atendidos** no período.
- **Taxa de qualificação**: faixa `self_service` ou `executivo` ÷ leads com faixa definida, com os números
  absolutos ("18 de 40").
- **Reuniões com executivo**: solicitadas e aprovadas.
- **Custo de IA**: médio por lead e por lead qualificado.
- **Alertas de qualidade**: eventos `alerta_*` e `vazamento_bloqueado`; verde quando zero.

**Gráficos:**
- Funil por etapa (barras horizontais, na ordem do esquema). Clicar numa barra abre a aba Conversas
  filtrada por aquela etapa.
- Distribuição por faixa e por temperatura.
- Leads por dia, separados por canal.
- Motivos de "fora do perfil" mais frequentes (`motivo_faixa` dos leads com faixa `fora_do_icp`).

Cada gráfico com título claro e estado vazio amigável.

---

### Prompt 3: acabamento

- Página "Sobre o P.H." (link no topo): o que o agente faz, as três faixas de roteamento e seus critérios
  (self-service: até 20 pessoas e até R$ 50 mil/mês; executivo: acima de um dos dois, com aprovação humana;
  fora do perfil: MEI, pessoa física, sem CNPJ ou só crédito), os guardrails do setor financeiro e o link do
  repositório: https://github.com/michelxxx2323/brax-sdr-agent
- Revise contraste, carregamento (skeletons), mensagens de erro e o layout no celular.
- Confirme que não existe nenhuma operação de escrita no código e nenhuma referência à tabela `leads`.
