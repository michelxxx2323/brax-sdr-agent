# Diário de validação: Fase 3 (canal de e-mail)

> Mesmo método da [Fase 2](validacao-fase2.md): cada conversa real é revisada, e as falhas viram testes
> automáticos, regras no cérebro ou decisões.

Modelo de conversa: `claude-haiku-4-5`. Canal: e-mail (Gmail API, conta dedicada da BRAX), com o atendente
conferindo a caixa a cada 30s (decisão 025).

---

## Teste 1: "Paulo, Nuvia" (8 pessoas, R$ 40 mil/mês): esperado self-service por e-mail

**Resultado: o fluxo completo funcionou.** Resposta na mesma thread, qualificação, roteamento para o app com link,
reforço de que documentos são só pelo app, assinatura automática. A regra em código pegou o tipo de empresa que
faltava ("falta: tipo_empresa") antes de rotear. Custo da conversa: cerca de US$ 0,05.

| Problema | Causa | Correção |
|---|---|---|
| O primeiro e-mail foi ignorado | O atendente foi ligado antes de o `.env` estar completo (a lista de remetentes permitidos) e só lê o `.env` ao iniciar | Operacional: reiniciar o atendente após mudar o `.env`. Um diagnóstico de leitura confirmou o motivo pelo log de etiquetas |
| A primeira resposta foi só **"Abraço, P.H. · Assistente virtual da BRAX"** | O modelo escreveu o e-mail inteiro antes de chamar `registrar_qualificacao` e, depois, só a despedida. A decisão 019 descartava todo texto anterior a uma ferramenta | O texto anterior só é descartado quando a ferramenta pode mudar a resposta (decisão 027). Fechos e assinaturas repetidos são removidos do e-mail |

**Aprendizado:** uma regra criada para um canal (019, no WhatsApp) teve efeito colateral no outro. No e-mail o modelo
escreve a mensagem inteira de uma vez, e por isso o texto antes das ferramentas é muito mais comum.

## Teste 2: "Paulo, Nuvia" do zero: reteste da primeira resposta

**Resultado: aprovado.** A primeira resposta veio completa (apresentação curta, explicação, uma pergunta sobre o
gasto mensal), com um único "Abraço," e uma única assinatura (decisão 027 funcionando).

**Detalhe menor:** o P.H. não chamou `registrar_qualificacao` com os dados da primeira mensagem (Nuvia, LTDA,
8 pessoas). A conversa não é afetada, porque ele lê o histórico, mas o registro fica incompleto até o roteamento.
É a mesma tendência anotada na Fase 2, para medir na Fase 6.

## Teste 3: follow-up em modo de teste (1 dia útil = 1 minuto)

**Funcionou:** o 1º lembrete saiu cerca de 1 minuto após a última pergunta do P.H., o 2º cerca de 3 minutos depois,
ambos na mesma thread, e nada mais depois disso (lead marcado como "sem resposta").

| Problema | Causa | Correção |
|---|---|---|
| Ao "Não tenho mais interesse.", o P.H. respondeu só **"Conversa encerrada."** | Não havia caminho para "sem interesse": o modelo usou o encerramento por "fora do assunto" e escreveu uma frase de sistema | Novo motivo `sem_interesse`: o código registra o motivo da perda e envia uma despedida cordial padronizada (decisão 029). "Conversa encerrada" entrou no bloqueio de texto interno |
| `**Conta digital PJ**` com asteriscos no e-mail | O modelo usou markdown apesar da instrução | O código remove `**` do corpo do e-mail |
| Lembretes com "Oi!", sem nome | O nome não foi registrado na qualificação | Saudações usam o primeiro nome do remetente do e-mail quando não há nome registrado |

**Aprendizado:** todo desfecho de conversa precisa de um caminho explícito, inclusive o "não" do lead. "Sem interesse"
é informação valiosa para o time comercial e não pode se perder num encerramento genérico.
