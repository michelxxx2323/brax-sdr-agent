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
