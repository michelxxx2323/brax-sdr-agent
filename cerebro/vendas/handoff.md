# Handoff: para onde o lead vai depois da qualificação

> Usa a tabela de roteamento do [ICP](icp.md) e as regras de [qualificacao.md](qualificacao.md).
> Em todos os casos, o agente registra no CRM a **faixa** e o **motivo**.

## 1. Self-service

**Quando:** até 20 funcionários **e** gasto mensal até R$ 50 mil, dentro do ICP.

**O que o agente faz:**
1. Explica em uma frase que o plano Start é feito para o momento da empresa.
2. Envia o **link oficial** do app (variável `BRAX_LINK_APP`).
3. Reforça que cadastro e documentos acontecem **só no app**.
4. Oferece ajuda se travar no cadastro e agenda follow-up (ver abaixo).
5. Registra no CRM: faixa `self-service`, motivo, dados coletados.

## 2. Executivo (com aprovação humana)

**Quando:** mais de 20 funcionários **ou** gasto mensal acima de R$ 50 mil.

**O que o agente faz:**
1. Diz que vai conectar o lead com uma pessoa do time comercial.
2. Pergunta a disponibilidade (período do dia, dias da semana).
3. **Pede aprovação no Slack** com o resumo abaixo. Enquanto espera, avisa o lead: "Vou confirmar a agenda e te retorno em seguida".
4. **Aprovado:** envia o link de agenda do executivo (`BRAX_LINK_AGENDA_EXECUTIVO`).
   **Recusado:** segue a orientação do humano (ex.: mandar para self-service) e registra o motivo.
5. Registra no CRM: faixa `executivo`, motivo, resumo, status da aprovação.

**Resumo para o Slack / executivo (modelo):**

```
🟢 Novo lead para executivo: {empresa}
Quem: {nome}, {cargo} (decisor: sim/não)
Empresa: {setor} · {funcionarios} pessoas · gasto ~R$ {gasto}/mês
Dor principal: {dor}
Solução atual: {solucao_atual}
Sinais de compra: {sinais} (prioridade {pontos})
Motivo da faixa: {motivo}
Canal: {whatsapp|email} · Disponibilidade: {disponibilidade}
[Aprovar] [Recusar]
```

<!-- REVISAR: tempo máximo de espera pela aprovação antes de avisar o lead de novo (sugestão: 2 horas úteis) -->

## 3. Fora do ICP

**Quando:** pessoa física, sem CNPJ, MEI/autônomo, ou quer só crédito/empréstimo.

**O que o agente faz:**
1. Agradece com educação e explica, sem julgamento, que o produto é feito para empresas com outro perfil.
2. MEI e autônomos: pode sugerir procurar uma conta PJ para MEI, **sem indicar marca e sem prometer nada**.
3. Encerra a conversa.
4. Registra no CRM: faixa `fora_do_icp`, motivo (`pessoa_fisica`, `sem_cnpj`, `mei`, `so_credito`).

## 4. Transferência para humano (a qualquer momento)

**Quando:**
- O lead pede para falar com uma pessoa.
- Setor de análise especial (ver [qualificacao.md](qualificacao.md)).
- Pergunta que o cérebro não responde, reclamação, tom agressivo ou assunto jurídico/regulatório.
- Lead que já é cliente com problema na conta (o SDR não é suporte).

**O que o agente faz:** avisa que vai passar para uma pessoa, informa o horário de atendimento
<!-- REVISAR: horário de atendimento humano (sugestão: seg a sex, 9h às 18h) --> e registra o motivo no CRM.

## 5. Pedido de parada (LGPD)

Se o lead pedir para parar ("não quero mais mensagens", "sai da lista", "pare"):
1. Confirma em uma única mensagem curta que não vai mais entrar em contato.
2. Marca `opt_out = true` e registra no CRM.
3. **Nenhum** follow-up é enviado depois disso, em nenhum canal.

## Follow-up <!-- REVISAR: cadência inventada -->

| Situação | Quando | Máximo de tentativas |
|---|---|---|
| Lead parou de responder durante a qualificação | 1 dia útil depois, depois 3 dias úteis | 2 |
| Self-service recebeu o link e não abriu conta | 2 dias úteis depois | 1 |
| Executivo: lead não agendou | 1 dia útil depois | 1 |

Depois do máximo, o lead fica como "sem resposta" no CRM. Nunca enviar follow-up para quem pediu parada.
No WhatsApp, respeitar a janela de 24 horas e usar apenas modelos de mensagem aprovados pela Meta fora dela.
