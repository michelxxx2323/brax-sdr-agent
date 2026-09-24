# Registro de decisões

> Cada decisão relevante do projeto fica aqui, no formato: **contexto → opções consideradas → decisão → motivo**.
> Decisões podem ser revistas; quando isso acontecer, a antiga é marcada como *substituída* e uma nova é criada.
> (Formato inspirado em ADRs, *Architecture Decision Records*.)

| # | Decisão | Status | Data |
|---|---|---|---|
| 001 | Um agente com ferramentas, sem subagentes | Aceita | 2026-09-24 |
| 002 | Python com o SDK oficial da Anthropic | Aceita | 2026-09-24 |
| 003 | Dois modelos configuráveis em um único arquivo | Aceita | 2026-09-24 |
| 004 | WhatsApp somente pela API oficial da Meta | Aceita | 2026-09-24 |
| 005 | Supabase para dados e memória | Aceita | 2026-09-24 |
| 006 | HubSpot gratuito como CRM | Aceita | 2026-09-24 |
| 007 | Hospedagem só na fase de canais | Aceita | 2026-09-24 |
| 008 | Cérebro em Markdown versionado no repositório | Aceita | 2026-09-24 |
| 009 | Aprovação humana no Slack antes de agendar com executivo | Aceita | 2026-09-24 |
| 010 | Roteamento por faixas como hipótese a calibrar | Aceita | 2026-09-24 |
| 011 | Marca fictícia inspirada em empresa real | Aceita | 2026-09-24 |

---

## 001: Um agente com ferramentas, sem subagentes

**Contexto:** a Bruna, da Woba, coordena vários agentes. Isso é poderoso, mas aumenta a complexidade de construir,
depurar e medir, e este projeto é construído por uma pessoa, com orçamento baixo.

**Opções consideradas:**
1. Vários subagentes especializados (qualificação, pesquisa, follow-up) coordenados por um orquestrador.
2. Um único agente com ferramentas (tools) para cada ação.
3. Fluxo fixo (árvore de decisão) sem LLM decidindo os passos.

**Decisão:** opção 2.

**Motivo:** um agente só tem um único ponto de entrada e um único histórico, o que torna os erros fáceis de rastrear.
As ferramentas dão modularidade suficiente. O fluxo fixo seria previsível, mas quebraria com leads que não seguem o roteiro,
que é justamente o valor de um SDR. Subagentes podem vir depois, se alguma ferramenta crescer demais (ex.: pesquisa).

---

## 002: Python com o SDK oficial da Anthropic

**Contexto:** é preciso escolher linguagem e forma de acessar o modelo.

**Opções consideradas:**
1. Python + SDK oficial `anthropic`.
2. TypeScript/Node + SDK oficial.
3. Frameworks de agentes (LangChain e similares).
4. Ferramentas no-code (n8n, Make).

**Decisão:** opção 1.

**Motivo:** Python é a linguagem mais comum em dados e IA e a mais legível para quem está começando. O SDK oficial
reduz dependências e acompanha os recursos da API (ferramentas, cache de prompt) sem uma camada extra de abstração.
No-code seria mais rápido no início, mas mostra menos do raciocínio técnico que o case quer evidenciar.

---

## 003: Dois modelos configuráveis em um único arquivo

**Contexto:** a maior parte das mensagens de um SDR é simples; poucas tarefas exigem raciocínio mais forte.
O custo por conversa importa para o case ("mais barato que um SDR humano").

**Opções consideradas:**
1. Um modelo forte para tudo.
2. Um modelo leve para tudo.
3. Modelo leve para a conversa e modelo forte para tarefas complexas e avaliações.

**Decisão:** opção 3.
- Conversa: `claude-haiku-4-5-20251001`
- Tarefas complexas e avaliações (LLM como juiz): `claude-sonnet-5`

**Motivo:** equilibra custo e qualidade. Deixar os nomes em **um único arquivo de configuração** permite trocar de modelo
sem mexer no código e comparar modelos nos evals da Fase 6.

**Observação:** os IDs acima conferem com a lista de modelos atual da Anthropic que eu, Claude, conhecia nesta sessão.
Ainda assim, devem ser checados na documentação oficial (docs.anthropic.com, página de modelos) na Fase 2,
antes da primeira chamada real à API.

---

## 004: WhatsApp somente pela API oficial da Meta

**Contexto:** existem bibliotecas não oficiais que automatizam o WhatsApp Web.

**Opções consideradas:**
1. Meta WhatsApp Cloud API (oficial), com número de teste gratuito.
2. Provedores oficiais (BSPs), como Twilio.
3. Bibliotecas não oficiais (automação do WhatsApp Web).

**Decisão:** opção 1.

**Motivo:** APIs não oficiais violam os termos do WhatsApp e podem levar ao banimento do número, o que é inaceitável
para uma fintech. A Cloud API é oficial, tem número de teste gratuito e dispensa intermediários. Um BSP pode ser considerado
se for necessário algum recurso que a Cloud API não ofereça.

---

## 005: Supabase para dados e memória

**Contexto:** o agente precisa guardar leads, empresas, conversas e a memória de cada lead, acessíveis de qualquer canal.

**Opções consideradas:**
1. Supabase (Postgres gerenciado, plano gratuito).
2. SQLite local.
3. Guardar tudo só no HubSpot.

**Decisão:** opção 1.

**Motivo:** Postgres é padrão de mercado, o plano gratuito é suficiente e o Supabase oferece painel visual, API pronta e
extensão de busca vetorial (pgvector) caso o cérebro cresça. SQLite não funciona bem quando o agente estiver hospedado
com mais de um processo. O HubSpot não foi feito para guardar cada mensagem e tem limites de API.

---

## 006: HubSpot gratuito como CRM

**Contexto:** o case precisa mostrar integração com CRM, que é o centro de uma operação de receita.

**Opções consideradas:**
1. HubSpot (plano gratuito).
2. Pipedrive (teste gratuito limitado).
3. Salesforce (Developer Edition).

**Decisão:** opção 1.

**Motivo:** plano gratuito permanente, API bem documentada e muito usado por startups brasileiras, que são o ICP da BRAX
e também as empresas que contratam GTM Engineers. Salesforce seria relevante para vagas enterprise, mas tem configuração bem mais pesada.

---

## 007: Hospedagem só na fase de canais

**Contexto:** o agente só precisa de uma URL pública quando começar a receber webhooks (WhatsApp e, possivelmente, e-mail).

**Opções consideradas:**
1. Hospedar desde o início.
2. Rodar local até a Fase 2 e hospedar (Railway ou Render) a partir das Fases 3/4.

**Decisão:** opção 2.

**Motivo:** evita custo e complexidade antes de haver algo para hospedar. A escolha entre Railway e Render fica para a Fase 3,
com base no plano gratuito vigente na época.

---

## 008: Cérebro em Markdown versionado no repositório

**Contexto:** o agente precisa de conhecimento sobre a empresa, e esse conhecimento muda (preços, objeções, regras).

**Opções consideradas:**
1. Tudo escrito direto no prompt do sistema, dentro do código.
2. Arquivos Markdown no repositório, carregados pelo agente.
3. Ferramenta externa (Notion, Google Docs).

**Decisão:** opção 2, com dados dinâmicos no Supabase.

**Motivo:** Markdown é legível por pessoas de vendas, versionado no Git (dá para ver quem mudou o quê e reverter)
e revisável em pull request. Separa **o que o agente sabe** de **como o agente funciona**. Uma ferramenta externa
adicionaria outra integração sem ganho real nesta escala.

---

## 009: Aprovação humana no Slack antes de agendar com executivo

**Contexto:** agendar com um executivo consome tempo caro do time comercial, e um erro de qualificação nesse ponto custa mais.

**Opções consideradas:**
1. Agente agenda direto.
2. Agente pede aprovação no Slack e só agenda depois do "ok".
3. Humano revisa todas as mensagens antes do envio.

**Decisão:** opção 2.

**Motivo:** mantém o humano no ponto de maior risco e custo sem travar o restante da conversa, como faz a Woba com propostas.
Revisar toda mensagem eliminaria o ganho de velocidade.

---

## 010: Roteamento por faixas como hipótese a calibrar

**Contexto:** os limites (20 funcionários, R$ 50 mil/mês) foram definidos sem dados reais.

**Decisão:** usar a tabela de [cerebro/vendas/icp.md](../cerebro/vendas/icp.md) como hipótese e registrar no CRM **a faixa e o motivo**
de cada roteamento.

**Motivo:** permite medir depois (Fase 6) se os limites fazem sentido, por exemplo, se leads self-service acima de 15
funcionários convertem pior sem executivo. É assim que um time de RevOps calibra regras de roteamento.

---

## 011: Marca fictícia inspirada em empresa real

**Contexto:** o case precisa de um produto realista, sem usar marca ou dados de empresa real.

**Decisão:** criar a **BRAX**, inspirada na Brex, e deixar isso explícito no README. Informações inventadas no cérebro
ficam marcadas com `<!-- REVISAR -->` até serem validadas.

**Motivo:** um produto real dá contexto de mercado crível; a marca fictícia evita confusão, uso indevido de marca e
promessas em nome de terceiros.
