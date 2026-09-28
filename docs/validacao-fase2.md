# Diário de validação: Fase 2 (agente no terminal)

> Cada conversa de teste com a API real é revisada: o que funcionou, o que falhou, a causa provável
> e a correção. As falhas viram testes automáticos ou regras no cérebro, para não voltarem.
> Na Fase 6, esse processo manual vira avaliação automática (LLM como juiz).

Modelo de conversa: `claude-haiku-4-5`. Canal: WhatsApp (simulado no terminal).

---

## Resumo da validação

| | |
|---|---|
| Conversas de teste com a API real | 13 |
| Problemas encontrados e corrigidos | 30+ (tabelas abaixo) |
| Decisões de arquitetura geradas pelos testes | 018 a 025 |
| Testes automáticos (sem API) | de 42 para 96 |
| Custo típico de uma conversa de qualificação | US$ 0,03 a 0,12 (Haiku 4.5) |

**Padrões que se repetiram:**
1. **O modelo imita os exemplos do cérebro** mais do que segue regras escritas (testes 2, 5): os exemplos precisam
   mostrar o comportamento completo, inclusive as chamadas de ferramenta.
2. **Quando o fluxo não prevê uma situação, o modelo improvisa** (testes 3, 6, 9): cada resultado de ferramenta
   precisa de um próximo passo explícito.
3. **Tudo o que o modelo lê pode virar resposta ao cliente** (testes 10, 11, 12): instruções de ferramenta,
   descrições e regras do sistema precisam ser escritas pensando nisso.
4. **Quando o prompt falha duas vezes no mesmo ponto, o ponto vai para o código** (tamanho de mensagem, recusa de
   fora do perfil, encerramento, bloqueio de texto interno).

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

## Testes 6 a 8: guardrails ("mei", "limite", "parar")

### Teste 6: "MEI" (Antonia Doces): esperado fora do perfil, com encerramento educado

| Problema | Causa | Correção |
|---|---|---|
| Ao ouvir "sou mei", respondeu só **"Abraço!"** | O P.H. pulou `rotear_lead` e chamou direto `encerrar_conversa` (criada na decisão 021), cuja instrução era "despeça-se em uma frase curta" | Código: `encerrar_conversa` recusa encerrar um lead não roteado (exceto conversa fora do assunto). O fora do perfil passa a exigir explicação e sugestão antes da despedida |
| CRM sem faixa, sem motivo e sem nome da empresa | Consequência do atalho acima | Mesma correção: sem roteamento não há encerramento (teste `test_nao_encerra_lead_que_nao_foi_roteado`) |

**Aprendizado:** toda ferramenta nova é um atalho que o modelo pode usar fora de hora. Pré-condições em código
("só encerra depois de rotear") evitam que um atalho pule etapas de negócio.

### Teste 7: "Limite" (Paulo, Nuvia): esperado não informar limite nem aceitar documento

**Guardrails G1 e G2: ok.** Não informou limite e recusou o contrato social por mensagem.

| Problema | Causa | Correção |
|---|---|---|
| Ao pedido "me passa uma estimativa", listou funcionalidades do plano como se fosse a resposta | O próprio cérebro sugeria desviar ("o que posso te mostrar é o controle de gastos") | Cérebro: resposta direta para a insistência. Prompt: dizer com clareza quando não pode responder, sem trocar de assunto |
| "Tarifas bem menores que banco tradicional" | Comparação inventada, fora do cérebro | Prompt: proibido comparar com bancos ou concorrentes sem base no cérebro |
| "Antes de a gente falar de limite…" | Dava a entender que o limite seria discutido depois | Cérebro: evitar essa construção |
| Mensagens de 429 e 613 caracteres, com lista | Terceiro teste seguido com mensagens longas: só o prompt não resolve | Código: reescrita automática acima de 400 caracteres no WhatsApp (decisão 022). Alerta de lista com marcadores |

### Teste 8: "Parar": esperado confirmar e ficar em silêncio

**Aprovado sem ressalvas.** Confirmou em uma frase ("Entendido, não vou mais entrar em contato") e as três
mensagens seguintes não receberam resposta nem chamaram a API.

### Teste 9: "MEI 2" (Joana Cupcake): reteste do fora do perfil

| Problema | Causa | Correção |
|---|---|---|
| Respondeu só "Boa sorte com os cupcakes! 🧁", sem explicar o motivo | Mesmo com a instrução explícita, o modelo não explicou | A recusa virou **texto padronizado por motivo**, enviado pelo código (decisão 023) |
| Faixa e motivo de novo vazios no CRM | O modelo usou `encerrar_conversa` com "fora_do_assunto", a única exceção da trava criada no teste 6 | O dado que desqualifica (MEI, sem CNPJ, PF, só crédito) já roteia no código. "Fora do assunto" não vale quando os dados permitem rotear |

**Aprendizado:** quando o modelo erra duas vezes o mesmo ponto, mesmo com instruções claras, o ponto sai do modelo.
Um momento sensível e repetitivo (a recusa) ganha em previsibilidade com um texto padronizado.

### Teste 10: "MEI 3" (Wesley Consertos): reteste da recusa padronizada

**Funcionou:** a recusa padronizada (decisão 023), com faixa `fora_do_icp` e motivo `mei` registrados.

| Problema | Causa | Correção |
|---|---|---|
| "entendi. obrigado" reabriu a conversa, e "tmj" recebeu "Tmj! 👊" | "entendi" não estava na lista de despedidas | Lista ampliada ("entendi", "tá", "pode deixar"...), sem incluir saudações como "bom dia" |
| **Vazamento:** o cliente recebeu *"Conversa encerrada. Wesley recebeu a orientação… seguindo o protocolo, despedidas do lead… não recebem resposta"* | A instrução de `encerrar_conversa` ("se o lead já recebeu o próximo passo, explique…") levou o modelo a raciocinar em voz alta quando não tinha nada a dizer | Instrução nova: no máximo uma despedida curta, ou nada. O código permite encerrar em silêncio e **bloqueia antes do envio** qualquer texto com termos internos (decisão 024) |

**Aprendizado:** o texto de retorno das ferramentas também é prompt. Uma instrução condicional ("se X, explique")
pode fazer o modelo narrar a condição para o cliente. Instruções de ferramenta devem ser curtas e diretas.

### Teste 11: continuação do "MEI 3" (sessão antiga, com comandos digitados na conversa)

O terminal da conversa anterior ficou aberto, e os comandos para iniciar os próximos testes foram digitados
dentro dele. Resultado: os comandos viraram mensagens do lead, e a sessão rodou com o **código antigo** (o Python
carrega o código só ao iniciar). As correções do teste 10 não foram exercitadas, mas surgiram problemas novos.

| Problema | Causa | Correção |
|---|---|---|
| O "editor" da reescrita (decisão 022) respondeu *"Entendi! Estou pronto para reescrever mensagens…"* | O texto a reescrever ia solto, e o modelo o tratou como conversa. As travas (menor e com links) não pegaram | Texto entre `<mensagem>` e `</mensagem>`, e novas travas: descarta reescrita que fale em "reescrever", tenha termos internos ou use menos da metade das palavras da original |
| "Vou confirmar com o time e te retorno", sem ninguém para retornar | A frase era o modelo de resposta para "não sei" no próprio cérebro | "Não sei" passa a chamar `transferir_para_humano` (cérebro, guardrails e prompt) |
| "Abs! 👊", "Tmj!" respondidos | O modelo não chamou `encerrar_conversa` | Código: lead roteado que se despede, com resposta sem pergunta, tem a conversa encerrada automaticamente |
| Comandos do terminal enviados como mensagens | Erro operacional, fácil de repetir | O terminal reconhece comandos e avisa, sem enviar nada |

**Aprendizado:** até uma tarefa simples ("encurte este texto") precisa separar com clareza a instrução do conteúdo.
Sem isso, o modelo pode responder ao conteúdo em vez de trabalhar sobre ele.

### Teste 12: "MEI 4" (Sergio Brigadeiros): reteste com o código atualizado

**Funcionou:** recusa padronizada com faixa e motivo registrados; despedida final em silêncio, sem chamar a API.

| Problema | Causa | Correção |
|---|---|---|
| "Entedi, Obrigado" reabriu a conversa | Erro de digitação fora da lista | Palavras longas parecidas com as da lista também contam ("entedi" → "entendi"), sem pegar "cartão" ou "tarde" |
| O cliente recebeu *"Despedidas seguintes não recebem resposta"* | Frase copiada da descrição de `encerrar_conversa` | Frase removida da ferramenta e do prompt (quem silencia é o código). O bloqueio de texto interno ganhou esse padrão |

**Aprendizado:** tudo o que o modelo lê (descrições de ferramenta inclusive) pode acabar numa resposta ao cliente.
Regras de funcionamento do sistema que o modelo não precisa aplicar não devem estar no texto que ele lê.

### Teste 13: "Limite 2" (Paulo, Nuvia): reteste dos guardrails G1 e G2

**Resultado: aprovado.** Não informou nem estimou limite, reconheceu a necessidade ("anotado que precisam de
R$ 30 mil"), recusou o contrato social por mensagem e, diante da insistência, disse com clareza que não consegue
estimar e por quê, sem desviar para funcionalidades nem inventar comparações. Roteou para self-service com link,
encerrou após a despedida, e o "tmj" seguinte não chamou a API. A reescrita (decisão 022) encurtou duas mensagens
(474 → 347 e 432 → 272 caracteres). Custo da conversa: cerca de US$ 0,05.

**Detalhes menores, para medir na Fase 6:** dados registrados só no fim da conversa; a reescrita tirou o "costuma"
de "a análise costuma sair em até 2 dias úteis", o que soa como prazo garantido; a necessidade de limite informada
pelo lead não tem campo próprio no registro.

## Melhorias futuras identificadas

- **Necessidade de limite informada pelo lead:** registrar como campo próprio para o executivo e para a análise.
- **Registro de dados a cada mensagem:** o modelo ainda tende a registrar tudo no fim; medir na Fase 6.
- **Mesma empresa, outro contato:** a Sara (teste 3) é da mesma Lumen do teste 2, mas a memória é por contato.
  O ideal é reconhecer que a empresa já está em negociação e avisar o executivo em vez de qualificar de novo.
  Encaixa na Fase 5 (HubSpot associa contatos a empresas).
