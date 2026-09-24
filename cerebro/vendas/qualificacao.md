# Qualificação

> Transforma os critérios do [ICP](icp.md) em perguntas e regras de decisão.
> O objetivo é chegar a uma **faixa de roteamento** (self-service, executivo ou fora do ICP) com o menor número de perguntas possível.

## Princípios

1. **Uma pergunta por mensagem** no WhatsApp; no máximo duas no e-mail.
2. **Não repetir** o que o lead já disse (ler o histórico antes de perguntar).
3. **Dar antes de pedir**: responder a dúvida do lead primeiro e só depois fazer a próxima pergunta.
4. **Desqualificar cedo**: se aparecer um critério de "fora do ICP", não continuar o questionário.
5. **Nunca pedir** CNPJ completo, documentos, senhas ou dados bancários. Nome da empresa e site bastam.
6. Se o lead não quiser responder algo, seguir em frente e registrar como "não informado".

## Dados a descobrir

| # | Dado | Por quê | Pergunta sugerida | Obrigatório para rotear? |
|---|---|---|---|---|
| 1 | Nome da empresa e site | Pesquisa e CRM | "Qual o nome da empresa? Se tiver site, me manda que eu dou uma olhada." | Sim |
| 2 | Tem CNPJ? Qual tipo (LTDA, S.A., MEI)? | Elimina PF e MEI | "A empresa já tem CNPJ? É LTDA, S.A. ou MEI?" | **Sim** |
| 3 | Número de funcionários | Roteamento | "Quantas pessoas trabalham na empresa hoje, mais ou menos?" | **Sim** |
| 4 | Gasto mensal com cartão/despesas | Roteamento | "Quanto a empresa gasta por mês com cartão e despesas do time, numa estimativa?" | **Sim** |
| 5 | Papel de quem conversa | Persona e decisor | "Qual o seu papel na empresa?" | Sim |
| 6 | Dor principal | Argumento e CRM | "O que te fez procurar a BRAX agora?" | Recomendado |
| 7 | Solução atual | Objeções e CRM | "Hoje vocês usam qual banco ou cartão para as despesas?" | Recomendado |
| 8 | Setor | ICP e setores de análise especial | Inferir do site; perguntar só se não der | Recomendado |
| 9 | Sinais de compra | Prioridade | Observar na conversa (rodada, contratações, 1ª pessoa de finanças) | Não |
| 10 | Quem decide | Handoff | Se não for founder/CFO: "Quem mais participa dessa decisão?" | Para faixa executivo |

## Ordem recomendada

```
1. Apresentação (assistente virtual + oferta de humano)
2. Entender o motivo do contato (dor)
3. CNPJ e tipo de empresa        → se PF/MEI: fora do ICP
4. Número de funcionários
5. Gasto mensal estimado
6. Papel de quem conversa         → se não decide: descobrir quem decide
7. Rotear (ver tabela abaixo)
```

A ordem é flexível: se o lead já trouxer os dados na primeira mensagem, pular direto para o roteamento.

## Regra de roteamento (*hipótese*, ver [icp.md](icp.md))

```
SE  sem CNPJ OU MEI OU pessoa física OU só quer crédito/empréstimo
    → FORA DO ICP (registrar motivo)
SE  setor exige análise especial (ver lista abaixo)
    → HUMANO (o agente não decide)
SE  funcionários > 20 OU gasto mensal > R$ 50 mil
    → EXECUTIVO
SE  funcionários <= 20 E gasto mensal <= R$ 50 mil
    → SELF-SERVICE
SE  faltam dados depois de 2 tentativas
    → Perguntar se prefere falar com uma pessoa; se não, enviar self-service
```

**Setores de análise especial** <!-- REVISAR: lista inventada; validar com compliance -->:
câmbio e criptoativos, apostas e jogos, bebidas alcoólicas e tabaco, armas, ONGs e entidades religiosas,
empresas com sede fora do Brasil.

## Pontuação de prioridade (para ordenar a fila do executivo) <!-- REVISAR -->

| Sinal | Pontos |
|---|---|
| Captou rodada nos últimos 12 meses | +3 |
| Está contratando rápido | +2 |
| Contratou a 1ª pessoa de finanças | +2 |
| Abriu escritório ou cidade nova | +1 |
| Paga muito software em dólar | +2 |
| Reclamou do banco atual | +1 |
| Quem conversa é o decisor (founder/CFO) | +2 |

A pontuação **não muda a faixa**, só a prioridade e o que vai no resumo para o executivo.

## O que registrar no CRM ao final

- Faixa (self-service / executivo / fora do ICP / humano) e **motivo**
- Dados da tabela acima (preenchidos ou "não informado")
- Persona e se é o decisor
- Sinais de compra identificados e pontuação
- Resumo da conversa em 3 linhas
