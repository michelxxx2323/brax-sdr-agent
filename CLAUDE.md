# CLAUDE.md: contexto do projeto BRAX SDR Agent

Este arquivo é lido automaticamente pelo Claude Code no início de cada sessão.

## Como trabalhar comigo (obrigatório)

Sou iniciante e não sou desenvolvedor, mas entendo um pouco de arquitetura de software e IA.

- **Idioma:** sempre português simples. Antes de cada etapa, explique o que vai fazer e por quê.
- **Confirmação:** peça minha confirmação antes de instalar qualquer coisa ou rodar comandos que alterem meu computador (instalar pacotes, criar ambientes, mudar configurações globais, deletar arquivos).
- **Commits:** pequenos e frequentes, com mensagens claras em português (ex.: `Cérebro: adiciona objeções da persona CFO`).
- **Push:** autorizado a fazer `git push` para o GitHub ao fim de cada etapa, sem perguntar antes. O repositório é **público**
  (https://github.com/michelxxx2323/brax-sdr-agent): antes de cada push, confira que nada sensível (.env, chaves, data/local/) está versionado.
  Nunca use `push --force` sem pedir.
- **Segredos:** nunca coloque chaves de API, senhas ou tokens no código. Use `.env` (já no `.gitignore`) e documente o nome da variável em `.env.example`, sem valor.
- **Erros:** se algo der errado, explique o erro e o que vai tentar. Não esconda falhas.
- **Fases:** não avance para a próxima fase sem minha aprovação explícita da atual.
- **Portfólio:** o repositório é um case para vagas de GTM Engineer / RevOps. Toda decisão relevante vai para `docs/decisoes.md` (contexto, opções, motivo). Documentar o raciocínio importa tanto quanto o código.

## O projeto

Agente de IA que atua como SDR (pré-vendas) inbound para a **BRAX**, fintech **fictícia** inspirada na Brex.
Inspiração: a "Bruna", agente SDR da Woba. Esta é uma versão própria, mais simples e barata, em código.

- **Produto BRAX:** conta digital PJ, cartões corporativos, Pix, gestão de despesas, integração contábil.
- **ICP:** startups brasileiras em crescimento. Ver `cerebro/vendas/icp.md`.
- **Agente:** Pedro Henrique, "P.H.". Canais: WhatsApp e e-mail (sem voz).
- **Missão:** atender leads inbound, entender a empresa, qualificar, rotear (self-service / executivo / fora do perfil), registrar no CRM e fazer follow-up.
- P.H. **sempre** se apresenta como assistente virtual da BRAX e oferece falar com uma pessoa.

## Arquitetura (resumo)

```
WhatsApp (Meta Cloud API) ─┐
                           ├──> Agente SDR "P.H." (Claude API + ferramentas)
E-mail (Gmail API) ────────┘            │
                                        ├── Cérebro (Markdown no GitHub + Supabase)
                                        ├── Pesquisa (empresa e decisor)
                                        ├── CRM (HubSpot gratuito)
                                        └── Aprovação humana (Slack)
```

Detalhes: `docs/arquitetura.md`. Decisões: `docs/decisoes.md`.

## Decisões técnicas já tomadas

- Um único agente com ferramentas (tools), sem subagentes por enquanto.
- Python + SDK oficial da Anthropic (`anthropic`).
- Modelos definidos em **um único arquivo de configuração** (não espalhar nomes de modelo pelo código):
  - conversa: `claude-haiku-4-5` (leve e barato; comparar com Sonnet 5 e Opus 5.5 na Fase 6)
  - tarefas complexas e avaliações: `claude-sonnet-5`
  - Confirmar os IDs na documentação oficial da Anthropic antes de usar.
- WhatsApp **somente** pela API oficial da Meta (Cloud API, número de teste). Nunca APIs não oficiais.
- Supabase (gratuito) para leads, conversas e memória. HubSpot (gratuito) como CRM. Slack para aprovação humana.
- Hospedagem (Railway ou Render) só na fase de canais.

## Cérebro (base de conhecimento)

`cerebro/` contém Markdown que explica a BRAX ao agente: `empresa/`, `vendas/`, `voz/`, `regras/`.
Três camadas: **conceito** (esses arquivos), **dados** (Supabase), **memória por lead** (P.H. lê o histórico antes de responder, em qualquer canal).
Informações inventadas sobre a BRAX estão marcadas com `<!-- REVISAR -->` até serem validadas.

## Guardrails (setor financeiro, inegociáveis)

1. Nunca prometer aprovação de conta, limite de cartão ou crédito.
2. Nunca pedir senha, código de verificação, dados de cartão ou documentos por WhatsApp ou e-mail. Cadastro só no app oficial.
3. Nunca apresentar rendimento como garantido.
4. Sempre se identificar como assistente virtual e oferecer atendimento humano.
5. LGPD: se o lead pedir para parar, parar e registrar no CRM.
6. Na dúvida, passar para um humano em vez de inventar.

Texto completo: `cerebro/regras/guardrails.md`.

## Fases

1. **Fundação**: estrutura, documentação e cérebro. ✅ concluída e aprovada
2. **Agente no terminal**: 🟡 implementado, em validação com a API real
3. Canal e-mail
4. Canal WhatsApp (número de teste da Meta)
5. CRM e aprovação humana (HubSpot + Slack)
6. Evals e métricas (LLM como juiz + painel de taxa de qualificação)

## Ambiente local

- Windows 11, PowerShell. Python 3.14. Git 2.55 (instalado na Fase 1).
- Pastas: `cerebro/`, `docs/`, `src/brax_sdr/` (código), `tests/` (testes).
- Ambiente: `.venv` na raiz. Sempre use `.venv\Scripts\python.exe`.
- Testes: `.venv\Scripts\python.exe -m pytest` (não chamam a API; o agente é testado com um cliente falso).
- Conversar: `.venv\Scripts\python.exe conversar.py --detalhes`.
- Decisões de desenho do código: o modelo extrai dados, o código decide a faixa (013); laço manual de ferramentas (015); guardrails em camadas (017).
