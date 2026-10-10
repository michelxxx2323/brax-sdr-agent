# Arquitetura

> Estado atual: Fases 1 a 6 e 5b concluídas: o P.H. está **no ar 24h** (Railway + Supabase). Fase 7 (painel do time
> comercial no Lovable) em andamento; Fase 8 (página pública para conversar com o P.H.) planejada.
> O porquê de cada escolha está em [decisoes.md](decisoes.md); o que cada teste real revelou, nos diários de validação
> ([Fase 2](validacao-fase2.md), [3](validacao-fase3.md), [4](validacao-fase4.md), [5](validacao-fase5.md),
> [6](validacao-fase6.md), [5b](validacao-fase5b.md), [7](validacao-fase7.md)).

## Visão geral

```
                              ┌──────────── Railway: iniciar_brax.py, um processo só, 24h (decisões 034, 043, 044) ────────────┐
WhatsApp (Meta Cloud API) ────┼─▶ webhook FastAPI ──┐                                                                           │
  (endereço fixo do Railway)  │   (assinatura HMAC,  │                                                                          │
                              │    avisos repetidos) ├─▶ Agente P.H. ──▶ HubSpot (contato, empresa, negócio, notas)            │
E-mail (Gmail API) ───────────┼─▶ atendente: confere │   (Claude +       Slack (aprovação com botões, alertas)                 │
                              │   a caixa a cada 30s ┘    ferramentas)    Supabase: memória de cada lead (tabela leads)         │
                              └──────────────────────────────────────────────────────┬────────────────────────────────────────┘
                                                                                      │ chave secreta (só o servidor grava)
                                                                                      ▼
                                                     Supabase (Postgres) ── visões somente leitura ──▶ Painel comercial
                                                     leads · evals          (RLS + login, 046/047)      (Lovable, Fase 7)

Terminal (conversar.py) ──▶ mesmo agente, no PC, para testes rápidos (leads em arquivos locais ou no Supabase)
Evals (rodar_evals.py) ───▶ mesmo agente, com lead simulado e juiz ──▶ JSON no repositório ──▶ painel no GitHub Pages
                                                                                            └──▶ cópia no Supabase (050)
```

**Princípio que guiou o projeto: a IA escreve, o código garante.** O modelo conduz a conversa e extrai dados; tudo o que é
regra de negócio, segurança ou custo fica em código, testado sem chamar a API. Quando uma instrução no prompt falhou duas
vezes no mesmo ponto nos testes reais ou nos evals, ela virou código (ver os diários).

| O modelo decide | O código garante |
|---|---|
| Como falar com o lead (tom, ordem das perguntas, explicações) | Faixa de roteamento (013), **roteamento assim que os dados ficam completos** (049), recusa de fora do perfil (023), setor especial (040), "sem interesse" (029) |
| Quais dados extrair de cada mensagem | Opt-out (G5), limites de custo e de mensagens, despedidas sem chamar a API (021) |
| Quando chamar cada ferramenta | Transferência quando o lead pede uma pessoa (037), horário comercial no aviso, identificação como assistente virtual na 1ª mensagem (040) |
| O texto do retorno depois da aprovação no Slack | Link obrigatório, nada de texto interno, tamanho no WhatsApp, formato da reunião (034, 035) |
| O texto do resumo para o painel | Só é gerado quando a faixa muda ou a conversa encerra; se falhar, a conversa segue (048) |

## O caminho de uma mensagem

`agente.responder()` aplica, nesta ordem:

```
mensagem do lead (com o horário em que chegou, 048)
 1. opt-out?                         → silêncio (G5), sem chamar a IA
 2. pediu uma pessoa?                → transfere em código (alerta no Slack) e segue para a IA com uma nota explícita (037)
 3. proteção (protecao.py)           → limite diário, limite de custo, mensagem gigante, despedida após encerramento (021)
 4. IA + ferramentas (laço manual)   → até 8 rodadas; ferramentas validam os dados e aplicam regras (015);
                                       o registro que completa a qualificação já roteia o lead (049)
 5. qual texto vale (027, 049)       → o escrito depois de ferramentas que mudam a resposta (inclusive um registro que roteou)
 6. texto padronizado, se for o caso → fora do perfil (023), sem interesse (029)
 7. WhatsApp longo?                  → reescrita curta, com travas (022)
 8. transferência sem horário?       → o código acrescenta "vendedor em horário comercial" (037)
 9. 1ª mensagem sem identificação?   → o código completa "assistente virtual"; ** sai do WhatsApp (040)
10. texto interno?                   → bloqueado: silêncio ou mensagem de segurança (024)
11. alertas                          → guardrails G1–G4, estilo, confiabilidade (registrados para medir)
12. horário em cada mensagem; resumo curto se a faixa mudou ou a conversa encerrou (048)
13. salva a memória (Supabase) → sincroniza o HubSpot (sem travar a conversa, 033) → o canal envia
```

## Componentes

### Canais

| Canal | Como chega a mensagem | Detalhes | Status |
|---|---|---|---|
| Terminal | Digitação (`conversar.py`) | Aprovações simuladas no terminal | ✅ |
| E-mail | Gmail API, a caixa conferida a cada 30s (025) | Resposta na mesma thread; filtros anti-loop; anexos nunca abertos; follow-up. App OAuth em produção (o token não vence a cada 7 dias) | ✅ no ar |
| WhatsApp | Webhook da Meta (FastAPI) no endereço fixo do Railway | Assinatura HMAC; avisos repetidos ignorados; uma mensagem por vez por lead; áudio e documentos nunca abertos | ✅ recebimento real no ar; envio desligado (032) |

Quem fala com o Gmail e com a Meta é o **código**, nunca o modelo (026): um e-mail ou uma mensagem maliciosa não consegue
fazer a IA ler ou enviar outras mensagens.

### Agente P.H.

Um único agente com ferramentas (001), num laço manual (015) que guarda o histórico completo de cada lead.

| Ferramenta | O que faz |
|---|---|
| `registrar_qualificacao` | Salva os dados ditos pelo lead (validados; "não informado" e nomes genéricos como "User" são descartados). Quando os dados permitem decidir a faixa, já roteia (023, 040, 049) |
| `rotear_lead` | Aplica a tabela do ICP **em código** e registra faixa e motivo (013); exige o setor (040) |
| `solicitar_aprovacao_executivo` | Publica o pedido no Slack e devolve "pendente"; o retorno sai depois do clique (034) |
| `transferir_para_humano` | Um alerta no Slack; o vendedor entra em contato em horário comercial e o P.H. segue coletando (037, 038) |
| `registrar_opt_out` | Pedido de parada (LGPD): nenhum contato depois disso, em nenhum canal |
| `encerrar_conversa` | Exige roteamento antes (exceto fora do assunto e lead já transferido); "sem interesse" registra o motivo da perda (029) |

O link do app e o link de agenda vêm sempre das ferramentas: o modelo nunca inventa um link.

**Modelos** (todos em `config.py`, trocáveis pelo `.env`):

| Uso | Modelo | Por quê |
|---|---|---|
| Conversa com o lead, reescrita de mensagens longas, resumo curto do painel | `claude-haiku-5-5`, sem pensamento, esforço medium | Rápido e barato; o raciocínio de negócio está no código (012, 048, 051) |
| Resumo do lead para o executivo (Slack e HubSpot), juiz dos evals | `claude-sonnet-5` | Mais capacidade; sem palpites no resumo |
| Lead simulado nos evals | `claude-haiku-4-5` | Só precisa seguir a ficha do cenário |

A troca do Haiku 4.5 para o 5.5 foi decidida por uma bateria comparativa de evals (051): 20/20 e custo 9x menor.

### Cérebro e memória

| Camada | Onde fica |
|---|---|
| **Conceito** | `cerebro/*.md`, carregado inteiro no prompt com cache (016). Busca (pgvector) só se crescer |
| **Memória por lead** | Supabase, tabela `leads` (043): o lead completo numa coluna JSON + colunas de resumo. Sem as variáveis do Supabase (testes, evals, PC), um arquivo JSON por lead em `data/local/` (014) |

A memória guarda conversa (com o horário de cada mensagem), dados de qualificação, faixa, aprovação, ids do CRM, mensagem
do Slack, estado do follow-up, resumo curto e um registro de eventos (para auditar e medir). Uma trava por lead impede que
dois canais mexam nela ao mesmo tempo. O horário de cada mensagem é retirado antes de o histórico ir à API do Claude, que
recusa campos extras (048).

### HubSpot (CRM, decisão 033)

- Contato (por e-mail ou telefone), empresa (reaproveitada quando já existe: duas pessoas da mesma empresa, uma empresa) e
  negócio no funil próprio **"BRAX Inbound"**: Qualificado – app · Reunião solicitada · Reunião aprovada · Perdido.
- Campos da BRAX: faixa, motivo, prioridade, sinais de compra, dor, solução atual, motivo da perda, opt-out.
- A etapa do funil é uma **função pura** (`etapa_do_negocio`). Sincroniza depois de cada resposta; se o HubSpot cair,
  o lead fica pendente e a conversa continua.
- Resumo do lead (Sonnet) vira **nota** associada ao contato, à empresa e ao negócio.

### Slack (aprovação humana e alertas, decisão 034)

- **Socket Mode**: a conexão sai do servidor; o Slack não precisa de endereço público.
- Pedido de aprovação com resumo e botões **Aprovar · Sugerir outro horário · Indicar o app**. Depois do clique, a IA
  escreve o retorno ao lead (com travas e texto de reserva), ele vai pelo canal da conversa e a mensagem do Slack mostra
  quem decidiu. Um segundo clique não gera um segundo retorno.
- Alerta de **transferência** sem botões; o que o lead disser depois aparece na thread do alerta.

### Follow-up (decisão 028)

Dois lembretes padronizados (1 e 3 dias úteis, só em horário comercial, na mesma thread de e-mail) quando o P.H. fez uma
pergunta e o lead sumiu. Nunca para quem pediu parada, foi encerrado, transferido, bloqueado ou está fora do perfil.
No WhatsApp, fica para depois: fora da janela de 24h, a Meta exige modelos aprovados.

### Avaliação (Fase 6, decisões 039, 040 e 050)

- 20 cenários (`evals/cenarios.json`); uma IA faz o lead seguindo uma ficha com fatos fixos.
- O código confere o objetivo (faixa, transferência, opt-out, alertas, vazamentos, custo); um juiz (Sonnet 5, que recebe
  o cérebro e as regras de desenho) dá notas de 1 a 5 para tom, uma pergunta por vez, não repetir perguntas,
  honestidade, guardrails e condução.
- Resultados em `evals/resultados/` (a fonte da verdade), painel em `docs/index.html` (GitHub Pages) e cópia no
  Supabase para a aba "Qualidade" do painel comercial.
- Histórico: 15/20 → 19/20 → 19/20 aprovados com o Haiku 4.5; **20/20** com o Haiku 5.5 (051). Alertas de guardrail 3 → 1 → 0 → 0.

### Banco e painel comercial (Fase 7, decisões 045 a 050)

O painel (gerado no Lovable) **só lê**, e só por visões. Quem escreve é o servidor do P.H., com a chave secreta.

| Objeto | O que é |
|---|---|
| `leads` (tabela) | Memória de cada lead. Fechada para o painel |
| `evals` (tabela) | Um cenário de cada bateria de evals. Fechada para o painel |
| `painel_leads` | Um lead por linha: qualificação, etapa do funil (mesma regra do HubSpot), temperatura, resumo, IDs do HubSpot, última mensagem |
| `painel_mensagens` | A conversa, só o texto e o horário (sem os detalhes internos das ferramentas) |
| `painel_eventos` | A linha do tempo (roteamento, aprovação, transferência, alertas...) |
| `painel_evals`, `painel_evals_baterias` | Qualidade: cada cenário com as notas do juiz; a evolução bateria a bateria |

**Acesso** (conferido por `verificar_acesso_painel.py`, 17/17):

| Quem | Pode |
|---|---|
| Visitante sem login (com a chave pública, que fica no front) | Nada: nem visões, nem tabelas, nem cadastro, nem gravação |
| Usuário logado (time ou conta demo, criados pelo administrador) | Ler as cinco visões. Não lê as tabelas (não vê o estado interno) e não grava |
| Servidor do P.H. (chave secreta, só no Railway e no `.env`) | Ler e gravar as tabelas |

As visões rodam com a permissão do dono do banco (o Supabase mostra o aviso "security definer view"; aqui é intencional,
porque a visão é o filtro). Todos os dados são fictícios (045). Arquivos: `supabase/esquema.sql`, `painel.sql` e `evals.sql`
(rodados no SQL Editor; podem rodar de novo sem apagar nada) e `lovable/` (roteiro e esquema para o Lovable).

## Segurança e privacidade

| Risco | Proteção |
|---|---|
| Chaves e tokens vazarem | Só no `.env` e nas variáveis do Railway (fora do Git); repositório público conferido antes de cada envio |
| Mensagem maliciosa manipular a IA | A IA não acessa caixa de e-mail nem a Meta (026); guardrail G7 no prompt; texto interno bloqueado antes do envio (024) |
| Alguém se passar pela Meta | Assinatura HMAC conferida em todo aviso do webhook. Na nuvem, o programa se recusa a ligar no modo simulado, cujo segredo de exemplo está no GitHub (044) |
| Acesso indevido aos dados pelo painel | Visões somente leitura, tabelas fechadas, cadastro público desligado, conta demo não publicada (046, 047) |
| Dados reais em telas públicas | Só dados fictícios; a página pública (Fase 8) terá aviso, mascaramento em código e guarda curta (045) |
| Dados sensíveis do lead | Documentos e áudios nunca abertos; o P.H. nunca pede senha, código ou documento (G2) |
| LGPD | Opt-out garantido em código, em todos os canais; só os dados necessários são coletados; política de privacidade publicada |
| Custo descontrolado | Limites por lead (mensagens/dia, custo, tamanho) aplicados antes da API (021) |

## Hospedagem (Fase 5b, decisões 043 e 044)

- **Railway (Hobby):** o `iniciar_brax.py` roda 24h como serviço único (`railway.json`: comando de início, verificação de
  saúde em `/saude`, reinício em caso de falha). Cada push no `main` publica a versão nova sozinho. A porta vem da
  variável `PORT`; as chaves, das variáveis do Railway.
- **Supabase (gratuito):** memória dos leads e resultados dos evals. O plano gratuito pausa projetos parados; o P.H. faz
  uma consulta leve a cada 6 horas para isso não acontecer (achado na Fase 5b).
- **Gmail:** app OAuth publicado em produção, com página inicial e política de privacidade no GitHub Pages.
- O P.H. **não pode** rodar no PC e no Railway ao mesmo tempo: os dois leriam o mesmo Gmail e responderiam duas vezes.

## Arquivos

| Arquivo | Papel |
|---|---|
| `src/brax_sdr/config.py` | Modelos, limites, links, preços e integrações (único lugar) |
| `src/brax_sdr/agente.py` | O caminho da mensagem: laço com ferramentas e todas as travas pós-modelo |
| `src/brax_sdr/prompt.py`, `cerebro.py` | Instruções do P.H. (com cache) e leitura do cérebro |
| `src/brax_sdr/ferramentas.py`, `roteamento.py` | Ferramentas com validação; tabela do ICP, setores especiais e prioridade |
| `src/brax_sdr/protecao.py`, `guardrails.py`, `mensagens.py` | Proteção antes da API; alertas e bloqueio de texto interno; textos padronizados e identificação garantida |
| `src/brax_sdr/memoria.py`, `travas.py`, `supabase_leads.py` | Memória por lead (Supabase ou arquivos), trava por lead e sinal de vida do banco |
| `src/brax_sdr/gmail.py`, `canal_email.py`, `atendente_email.py` | Canal de e-mail |
| `src/brax_sdr/canal_whatsapp.py`, `webhook_whatsapp.py`, `simulador_whatsapp.py` | Canal de WhatsApp (real e simulado) |
| `src/brax_sdr/followup.py` | Regras e textos do follow-up |
| `src/brax_sdr/crm.py`, `resumo.py` | HubSpot; resumo para o executivo (Sonnet) e resumo curto para o painel (Haiku) |
| `src/brax_sdr/slack_brax.py` | Aprovação, retorno ao lead e alertas no Slack |
| `src/brax_sdr/evals.py`, `painel.py`, `supabase_evals.py` | Avaliação automática, painel do GitHub Pages e cópia no Supabase |
| `iniciar_brax.py`, `railway.json`, `.python-version` | Programa único e configuração da hospedagem |
| `supabase/*.sql`, `lovable/*.md` | Banco (tabelas, visões e permissões) e roteiro do painel no Lovable |
| `conversar.py`, `simular_whatsapp.py`, `atender_email.py`, `servidor_whatsapp.py` | Terminal, simulador e canais avulsos |
| `autorizar_gmail.py`, `configurar_hubspot.py`, `sincronizar_crm.py`, `diagnosticar_whatsapp.py` | Configuração e diagnóstico |
| `rodar_evals.py`, `enviar_evals_supabase.py`, `migrar_para_supabase.py`, `verificar_acesso_painel.py` | Evals, envio ao banco, migração e verificação de acesso |
| `tests/` | Mais de 230 testes automáticos, sem chamar nenhuma API (clientes falsos de Claude, Gmail, Meta, HubSpot, Slack e Supabase) |

## Limitações conhecidas e próximos passos

- **Painel no Lovable** em construção (Fase 7); a aba "Qualidade" já tem os dados no banco.
- **Página pública** para conversar com o P.H. (Fase 8): passa pelo servidor do P.H., nunca grava direto no banco (045, 047).
- Temperatura do lead é uma **hipótese a calibrar**: só soma sinais de compra e se a pessoa decide (048).
- Qualquer usuário logado no painel vê **todos** os leads (sem separação por vendedor); aceitável para um time pequeno.
- Mensagens anteriores a 09/10/2026 não têm horário nem resumo.
- O webhook responde "ok" à Meta antes de processar: se o banco estiver fora do ar, aquela mensagem se perde (Fase 5b).
- Responder ao lead de dentro do Slack (hoje o vendedor usa os próprios canais) (038).
- Agenda real ligada ao CRM (reuniões do HubSpot), deixada de fora por privacidade (035).
- Follow-up no WhatsApp com modelos aprovados pela Meta (030).
- Comparar o Haiku 5.5 com o Sonnet 5.5 nos evals, se a qualidade precisar subir (051).
- Pesquisa automática da empresa e do decisor (planejada desde a Fase 1).
