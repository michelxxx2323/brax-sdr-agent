# Diário de validação: Fase 2 (agente no terminal)

> Cada conversa de teste com a API real é revisada: o que funcionou, o que falhou, a causa provável
> e a correção. As falhas viram testes automáticos ou regras no cérebro, para não voltarem.
> Na Fase 6, esse processo manual vira avaliação automática (LLM como juiz).

Modelo de conversa: `claude-haiku-4-5`. Canal: WhatsApp (simulado no terminal).

---

## Teste 1: "Nexora" (founder, 12 pessoas, R$ 35 mil/mês): esperado self-service

**Funcionou:** apresentação como assistente virtual, oferta de humano, uma pergunta por mensagem,
dados extraídos corretamente (LTDA, 12 pessoas, R$ 35 mil).

| Problema | Causa | Correção |
|---|---|---|
| Resposta vazia no terminal | O modelo escreveu a pergunta **e** chamou uma ferramenta na mesma rodada; o código só mostrava o texto da última rodada (vazia) | Bug de código: o texto de todas as rodadas é somado. Teste `test_texto_escrito_junto_com_ferramenta_nao_se_perde` |
| Campo `nome_contato: "Não informado"` | O modelo preencheu um dado desconhecido com texto | Prompt: omitir campos desconhecidos. Código: valores como "não informado" são descartados (teste `test_qualificacao_descarta_textos_sem_informacao`) |
| Dados registrados só no fim | O modelo esperou juntar tudo | Prompt: registrar cada dado na mesma resposta em que aparece |
| Não roteou, mesmo com os 3 dados | Instrução ambígua sobre quando rotear | Prompt: rotear **assim que** tiver tipo, funcionários e gasto |

---

## Teste 2: "Lumen" (CEO, 28 pessoas, R$ 70 mil/mês): esperado executivo com aprovação

**Funcionou:** faixa correta (executivo) com motivo registrado, aprovação humana antes do link de agenda,
dados completos, dor bem resumida.

| Problema | Causa | Correção |
|---|---|---|
| "Um momentinho! 🔄" e parou: o lead teve que cobrar | O modelo **anunciou** a aprovação em vez de chamar a ferramenta. No sistema, o lead só vê a mensagem depois que as ferramentas rodam | Prompt: nunca anunciar ação para depois; chamar a ferramenta na mesma resposta |
| Pergunta de confirmação e link na mesma resposta | Efeito do problema anterior | Idem |
| Disse "faz sentido falar com o time comercial" antes de rotear | O modelo antecipou a decisão que cabe ao código (decisão 013). O exemplo do cérebro mostrava esse padrão | Prompt: não falar da faixa antes de `rotear_lead`. Exemplo do cérebro reescrito mostrando as ferramentas |
| Sinal `gastos_em_dolar` sem o lead mencionar dólar | Dedução a partir de "Facebook Ads" | Descrição da ferramenta: só sinais ditos explicitamente |
| "CEO decisora" para um lead que disse "Sou **o** CEO" | Copiado do exemplo da "Ana" no cérebro | Tom de voz: não presumir gênero; exemplos com "decisor: sim" |
| Mensagens de 370 a 500 caracteres e `**negrito**` | Tom de voz sem limite objetivo; markdown não funciona no WhatsApp | Tom de voz: até ~300 caracteres, sem markdown. Código: alerta de estilo acima de 400 caracteres ou com `**` |

**Aprendizado:** o modelo copia padrões dos exemplos com mais força do que segue regras escritas.
Exemplos do cérebro precisam mostrar o comportamento **inteiro**, inclusive as chamadas de ferramenta.

---

## Teste 3: "Lumen 2" (Sara, 28 pessoas, R$ 70 mil/mês, quer conversar "hoje"): esperado executivo

Na aprovação, o time (simulado) respondeu: "não consigo hoje, sugerir amanhã às 15h".

**Funcionou:** as correções dos testes 1 e 2 fizeram efeito. Os dados foram registrados durante a conversa,
o roteamento aconteceu assim que havia os três dados e a aprovação foi pedida na resposta certa.

| Problema | Causa | Correção |
|---|---|---|
| Duas mensagens contraditórias numa resposta ("qual horário hoje?" + "o time não consegue hoje") | O modelo escreveu antes de pedir a aprovação e de novo depois do resultado. A correção do teste 1 somava os dois textos | Código: o lead vê só o texto escrito **depois** das ferramentas; o texto anterior sai do histórico (decisão 019). Teste `test_texto_antes_da_ferramenta_nao_aparece_quando_ha_texto_depois` |
| Pediu confirmação duas vezes, sendo que o horário veio do time | O fluxo só tinha aprovar/recusar: a contraproposta de horário virou "recusada", e o P.H. ficou sem caminho | Nova decisão **"sugerir outro horário"**: o lead está aprovado, e o link vai junto com a sugestão (decisão 018) |
| **Inventou uma confirmação:** "O time confirmou: amanhã às 15h está fechado" + `[link será enviado pelo time]` | Sem caminho definido, o modelo improvisou. Nenhuma aprovação tinha acontecido | Prompt: nunca afirmar o que não veio de uma ferramenta nem usar texto de exemplo. Código: novos alertas de **Confiabilidade** (teste `test_confirmacao_inventada_gera_alerta`) |
| "Vou confirmar com o time e te mando o link", sem chamar ferramenta | Promessa de ação sem ação | Alerta de Confiabilidade quando há promessa e nenhuma ferramenta foi chamada |

**Aprendizado:** quando o fluxo não prevê uma situação, o modelo **improvisa**, e improviso em fintech é risco.
Cada resultado possível de uma ferramenta precisa ter um próximo passo explícito.

## Teste 4: "Lumen 3" (Ricardo, CFO, mesmo cenário do teste 3): reteste das correções

Na aprovação, o time (simulado) escolheu "sugerir outro horário: segunda que vem às 16h".

**Resultado: aprovado.** As correções dos testes 1 a 3 funcionaram com a API real:
- Uma única mensagem depois da aprovação, com o horário sugerido e o link (decisões 018 e 019).
- Nenhum alerta de guardrail, estilo ou confiabilidade na conversa.
- A regra em código evitou um erro: o P.H. tentou rotear sem o tipo de empresa, recebeu "falta: tipo_empresa"
  e perguntou antes de seguir (decisão 013 funcionando na prática).

**Detalhes menores, para medir na Fase 6:** duas perguntas numa mesma mensagem; reenviou o link depois da
confirmação; "Até segunda!" (quem vai na reunião é o executivo); continuou respondendo a mensagens de despedida
("tmj", "é nois") em vez de encerrar.

## Teste 5: "Seletax" (Ricardo, 10 pessoas, R$ 5 mil/mês): reteste com identificação curta e encerramento

**Funcionou:** apresentação curta, sem oferta de humano logo de cara (decisão 020); encerramento depois da
despedida, com as mensagens seguintes de despedida sem chamar a API (decisão 021).

| Problema | Causa | Correção |
|---|---|---|
| O lead disse "Aqui é o Ricardo da Seletax" e o P.H. perguntou "qual o nome da empresa?" | Todos os exemplos de primeira mensagem terminavam com essa pergunta; o modelo seguiu o roteiro sem ler a mensagem. A regra de não repetir perguntas só citava o histórico | Prompt: conferir a mensagem atual antes de perguntar. Cérebro: exemplo 2b, com o lead já se apresentando pela empresa |

**Aprendizado (reforço do teste 2):** o modelo imita os exemplos. A variedade dos exemplos importa tanto quanto as regras.

## Melhorias futuras identificadas

- **Mesma empresa, outro contato:** a Sara (teste 3) é da mesma Lumen do teste 2, mas a memória é por contato.
  O ideal é reconhecer que a empresa já está em negociação e avisar o executivo em vez de qualificar de novo.
  Encaixa na Fase 5 (HubSpot associa contatos a empresas).
