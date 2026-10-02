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
