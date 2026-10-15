# Case: um SDR de IA para inbound B2B, do desenho à operação

> Resumo de uma página para quem avalia o projeto. Detalhes no [README](../README.md) e no
> [diário de decisões](decisoes.md) (61 decisões, cada uma com contexto, opções e motivo).

**Experimente:** [converse com o P.H.](https://sdr-brax.lovable.app/simular) como se fosse um lead · [painel do time
comercial](https://sdr-brax.lovable.app/login) (`demo@brax-sdr.dev` / `BraxDemo2026!`) · [painel dos evals](https://michelxxx2323.github.io/brax-sdr-agent/)

## O problema

Numa fintech B2B que cresce por inbound, o SDR gasta o dia em tarefas repetitivas: responder "como funciona?",
descobrir o tamanho da empresa, separar MEI de startup com rodada e copiar tudo para o CRM. O lead esfria em minutos,
a qualificação muda de pessoa para pessoa e contas pequenas ocupam a agenda do executivo.

## O que eu construí

O **P.H.**, assistente virtual de pré-vendas da BRAX (fintech fictícia inspirada na Brex), no ar 24h:

- atende por **WhatsApp** (API oficial da Meta) e **e-mail** (Gmail, com follow-up automático);
- qualifica pelo ICP e **roteia** para três caminhos: self-service (link do app), executivo (reunião com aprovação
  humana no Slack) ou fora do perfil (encerramento educado, motivo no CRM);
- registra contato, empresa e negócio no **HubSpot**, num funil próprio;
- alimenta um **painel do time comercial** (conversas, funil, temperatura, métricas e qualidade) e uma **página pública**
  onde qualquer pessoa conversa com ele e vê os bastidores ao vivo.

Stack: Python, Claude (Anthropic), Supabase, HubSpot, Slack, Meta WhatsApp Cloud API, Gmail API, Railway, Lovable.

## Decisões que mais importaram

1. **O modelo extrai, o código decide.** A IA conversa e extrai os dados; a faixa (self-service, executivo, fora do
   perfil) sai de uma regra em código, testável e auditável. Um time de RevOps consegue mudar o corte de 20 pessoas
   sem mexer em prompt (decisão 013).
2. **"A IA escreve, o código garante."** Quando uma regra do prompt falha duas vezes, ela vira código: roteamento
   automático quando os dados ficam completos, bloqueio de texto interno antes de chegar ao lead, identificação como
   assistente virtual garantida e promessa de retorno convertida numa transferência real (017, 049, 054).
3. **Guardrails de setor financeiro em camadas:** nunca prometer aprovação ou limite, nunca pedir documentos por
   mensagem, LGPD com opt-out registrado no CRM e, na dúvida, uma pessoa assume.
4. **Humano no ponto certo, não em todo lugar.** Aprovação assíncrona no Slack só para reuniões de executivo; o lead
   recebe a resposta quando o time aprova, escrita pela IA com travas (034, 037).
5. **Custo como requisito.** Proteção de custo antes de chamar a API, teto diário no simulador público e troca de modelo
   guiada por evals: o custo por conversa caiu de US$ 0,03 para **US$ 0,004** sem perder qualidade (021, 051).
6. **Dados fictícios por desenho.** Nada real no painel ou no repositório público; no simulador, CPF, CNPJ, telefone,
   e-mail e cartão viram `[removido]` antes de chegar à IA (045, 060).

## Como eu sei que funciona

Cada mudança passa por uma **bateria de evals**: um lead simulado conversa com o P.H., o código confere o resultado
e um modelo mais forte dá notas como juiz. Cada falha real vira primeiro um cenário, e só depois é corrigida.

| | 1ª bateria | Hoje |
|---|---|---|
| Cenários aprovados | 15/20 | **23/25** |
| Roteamento correto | 73% | 94% a 100% |
| Custo por conversa | US$ 0,026 | **US$ 0,004** |

Além disso: 271 testes automáticos (sem chamar a API), um diário de validação por fase com os testes reais e os erros
encontrados, e um experimento que **piorou** os evals e foi revertido e documentado (decisão 056). Medir também serve
para descartar ideias.

## O que eu aprendi

- **O prompt não é o lugar para regra de negócio.** Tudo que precisa ser sempre verdade (faixa, opt-out, links) foi
  para o código. O prompt ficou com o tom e a conversa.
- **Usuários reais acham o que os testes não acham.** O primeiro teste no simulador público revelou um dado deduzido
  ("LTDA" sem a lead dizer), uma temperatura contraintuitiva para o time comercial e dúvidas simples (IOF, cashback)
  indo para um vendedor. Viraram cenários novos e correções no mesmo dia (061).
- **Em planos gratuitos, ficar parado é um modo de falha.** O banco pausou sem tráfego e derrubou tudo em silêncio;
  um sinal de vida a cada 6 horas resolveu (5b).

## Limites honestos

A BRAX e todos os leads são fictícios. O WhatsApp recebe mensagens da Meta de verdade, mas o envio fica desligado (sem
número real). Os critérios de ICP e a pontuação de temperatura são hipóteses, para calibrar com dados reais de conversão.

## Próximos passos, se fosse para produção

Calibrar ICP e temperatura com dados de conversão do HubSpot; medir tempo de resposta e taxa de qualificação contra a
linha de base do SDR humano; ligar o envio no WhatsApp com número verificado; e rodar os evals a cada deploy.
