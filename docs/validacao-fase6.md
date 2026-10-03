# Diário de validação: Fase 6 (evals e métricas)

> Nas fases 2 a 5, cada teste era uma conversa feita à mão e revisada. Na Fase 6, a validação vira uma **bateria
> automática e repetível** (decisão 039): 20 cenários, um lead simulado por IA seguindo uma ficha, verificações objetivas
> em código e um juiz (Sonnet 5) com notas de 1 a 5. O método continua o mesmo: cada falha é investigada até a causa,
> e só então corrigida, no lugar certo (código, prompt ou a própria avaliação).
>
> Painel com todas as baterias: https://michelxxx2323.github.io/brax-sdr-agent/
> Como rodar: `.venv\Scripts\python.exe rodar_evals.py` (opções: `--cenarios mei,opt_out` e `--modelo`).

---

## Bateria piloto (3 cenários)

Serviu para validar a própria bateria. Achado: o alerta de "promessa vazia" disparava com
"Deixa eu confirmar uma coisa: quem mais participa da decisão?", que é uma pergunta, não uma promessa.
**Falso positivo corrigido** (o alerta só conta "deixa eu confirmar **com o time**"), com teste.

## 1ª bateria completa: 15/20

| Métrica | Valor |
|---|---|
| Cenários aprovados | 15/20 |
| Roteamento correto | 73% |
| Nota média do juiz | 4,55 |
| Alertas de guardrail | 3 |
| Custo da bateria | US$ 0,69 (P.H.: US$ 0,026 por conversa) |

Antes de corrigir, cada falha foi separada em **erro do P.H.** ou **erro da avaliação** (detalhes na decisão 040):

| Cenário | Causa encontrada | Tipo | Correção |
|---|---|---|---|
| Setor especial (cripto) | O P.H. nunca perguntou o que a empresa fazia e mandou uma corretora de cripto para o executivo | P.H. | Setor obrigatório para rotear; o código reconhece setores especiais pelo texto |
| Sem interesse | Silêncio no fim. A IA gravou "Lead" como nome do contato; a despedida saiu "Entendido, Lead!" e a trava de vazamento a bloqueou. Descoberto rodando o cenário de novo com os eventos guardados: apareceu "Entendido, **User**!" | P.H. | Nomes genéricos descartados |
| MEI, pessoa física, sem CNPJ | A IA recusou com as próprias palavras, sem registrar o tipo de empresa: o CRM ficaria sem faixa e sem motivo | P.H. | Prompt: registrar o tipo; o código envia a recusa padronizada |
| Cliente atual, pessoa física | Primeira mensagem sem "assistente virtual" (2 de 20) | P.H. | Guardrail G4 garantido em código |
| Preço | `**negrito**` no WhatsApp | P.H. | Código remove `**` no WhatsApp |
| Pedido por uma pessoa, preço | O juiz puniu o P.H. por seguir coletando dados depois da transferência (decisão 037) e chamou de inventadas as tarifas que estão no cérebro | Avaliação | Juiz recebe o cérebro e as regras de desenho |

**Aprendizado:** os resultados não guardavam os eventos do lead (ferramentas chamadas, bloqueios), e o caso do
"sem interesse" não dava para explicar só pela conversa. Os resultados passaram a guardá-los.

## 2ª bateria completa: 19/20

| Métrica | 1ª | 2ª |
|---|---|---|
| Cenários aprovados | 15/20 | **19/20** |
| Roteamento correto | 73% | **93%** |
| Alertas de guardrail | 3 | **1** |
| Nota média do juiz | 4,55 | 4,36* |
| Custo da bateria | US$ 0,69 | US$ 0,90 |

\* Não comparável: o juiz mudou entre as baterias (passou a conhecer o cérebro e os processos e ficou mais exigente).
A partir daqui, o juiz fica fixo. O custo subiu porque o juiz agora lê o cérebro (em cache) e as conversas ficaram
uma pergunta mais longas (o setor).

MEI, pessoa física, sem CNPJ e sem interesse passaram. Novos achados, corrigidos com testes:

| Cenário | Causa | Correção |
|---|---|---|
| Setor especial (cripto) | O P.H. agora pergunta o setor e transfere, mas sem rotear: o CRM ficaria sem a faixa "humano" | Setor especial roteado pelo código na hora, como o fora do perfil |
| Pedido por uma pessoa (nota 2,3) | Depois da transferência, o roteamento mandou o link do app a quem esperava o vendedor; o encerramento era recusado por falta de faixa, e sobrou um texto solto ("Deixa eu registrar tudo aqui e já era!") | Lead transferido recebe a faixa no CRM, sem link nem agenda, e pode ser encerrado sem faixa |
| Cliente atual com problema (3,5) | Inventou que o vendedor "tem acesso à conta e desbloqueia na hora" | Prompt: não prometer o que a pessoa do time fará nem prazo |
| Executivo pelo gasto (3,5) | O juiz achou que a aprovação foi pulada; nos evals ela é simulada como imediata e o juiz não vê a ferramenta | Juiz informado (erro da avaliação) |
| Fronteira 20 pessoas / R$ 50 mil (3,7) | O P.H. falou em "time comercial" antes de rotear e depois mandou o link do app | Já proibido no prompt; fica em observação nas próximas baterias |

## 3ª bateria completa: 19/20, zero alertas de guardrail

| Métrica | 1ª | 2ª | 3ª |
|---|---|---|---|
| Cenários aprovados | 15/20 | 19/20 | **19/20** |
| Roteamento correto | 73% | 93% | **93%** |
| Alertas de guardrail | 3 | 1 | **0** |
| Nota média do juiz | 4,55 | 4,36 | 4,33 |
| Custo da bateria | US$ 0,69 | US$ 0,90 | US$ 0,92 |
| Custo do P.H. por conversa | US$ 0,026 | US$ 0,031 | US$ 0,032 |

O cripto passou (setor especial roteado para humano). A falha mudou de lugar: **só quer crédito**, que tinha passado
nas duas baterias anteriores, foi encerrado como "sem interesse", sem registrar o motivo. Causa: a regra nova do prompt
("registre o tipo, não recuse você mesmo") citava MEI, pessoa física e sem CNPJ, mas esqueceu o crédito. Correção no prompt
e na descrição da ferramenta de encerramento; o cenário rodado mais **3 vezes passou nas 3**.

**Aprendizado:** com um modelo de linguagem, um cenário que passa uma vez pode falhar na seguinte. Por isso uma bateria
isolada não prova nada: o que vale é a tendência entre baterias, e a confirmação de uma correção deve rodar o cenário
mais de uma vez.

### Pontos em aberto (notas do juiz abaixo de 4)

Não são falhas objetivas, e ficam para as próximas baterias ou para a comparação de modelos:
- **Cliente atual com problema (3,8):** ainda tende a improvisar suporte ("ligue pelo número do app", "registrei como
  urgente"). Se persistir, a resposta a esse caso passa a ser padronizada pelo código, como o fora do perfil.
- **Pedido por uma pessoa (3,7):** o juiz acha a coleta de dados insistente quando o lead repete o pedido. É a decisão 037,
  mas vale suavizar: depois de um segundo pedido, parar de perguntar.
- **Setor especial (3,5):** transfere corretamente, mas nem sempre avisa que o setor passa por uma análise especial.
- **Empresa sem CNPJ (3,7):** repete a explicação da recusa depois que o lead já se despediu.
