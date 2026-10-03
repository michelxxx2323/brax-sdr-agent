# Diário de validação: Fase 5 (HubSpot e Slack)

> Mesmo método das fases anteriores: cada teste real é revisado, e as falhas viram testes, regras ou decisões.

---

## Teste 1: configuração do HubSpot e sincronização dos leads de teste (decisão 033)

**Resultado: aprovado, com dois bugs corrigidos.** `configurar_hubspot.py` criou 16 campos da BRAX e o funil
"BRAX Inbound". `sincronizar_crm.py --todos` enviou os 15 leads das fases 2 a 4, com as etapas esperadas:
executivos aprovados em "Reunião aprovada", self-service em "Qualificado – app", MEIs só como contato e empresa (sem negócio).
As 4 conversas da Lumen (inclusive a Ana do WhatsApp) ficaram associadas a **uma única empresa**.

| Problema | Causa | Correção |
|---|---|---|
| Erro 401 "token expirado em 1970" | A chave copiada era a **chave de acesso pessoal** (para a ferramenta de linha de comando do HubSpot), não a chave de serviço | Chave de serviço (começa com `pat-`). A mensagem de erro do script passou a orientar sobre isso |
| Leads do terminal (`lumen`, `lead-teste`) gravados com telefone inválido (`+lumen`) | O código tratava todo id sem `@` como telefone | Telefone só quando o id tem só dígitos; senão, o contato é achado pelo campo "ID do lead na BRAX". Telefones inválidos limpos no HubSpot |
| Duas empresas "Nuvia" | A busca do HubSpot leva alguns segundos para enxergar um registro novo (consistência eventual), e as duas conversas foram sincronizadas em sequência | O cliente lembra as empresas que acabou de criar. As duplicadas foram mescladas com a função de mesclar do HubSpot |

**Aprendizado:** APIs de CRM costumam ter **consistência eventual** na busca: "procurar antes de criar" não basta quando
dois registros chegam juntos. Em produção, com vários processos, a proteção completa exigiria uma trava ou uma chave única
(ex.: domínio da empresa); fica anotado para a hospedagem (5b).

## Teste 2: aprovação pelo Slack de ponta a ponta (WhatsApp simulado + Slack + HubSpot)

Lead "Bruno, Vetra" (40 pessoas, R$ 90 mil/mês), pelo programa único `iniciar_brax.py`.

**O que funcionou:** roteamento para executivo; pedido no Slack com resumo e botões; aprovação clicada 14 segundos depois;
retorno escrito pela IA com o link de agenda, enviado 2 segundos após o clique; HubSpot atualizado.

| Problema | Causa | Correção |
|---|---|---|
| O lead "não recebeu" o retorno da aprovação | O retorno **foi enviado**, mas o simulador só olhava as mensagens logo depois de o lead escrever. Uma mensagem proativa nunca aparecia (e era marcada como vista no "E aí?" seguinte) | O simulador passa a vigiar as mensagens o tempo todo e mostra na hora qualquer mensagem do P.H. |
| Ao "E aí?", o P.H. disse "Deixa eu confirmar com o time... Já retorno por aqui!", com a reunião já aprovada | O modelo não tinha, no contexto do lead, um sinal claro de que a reunião estava aprovada e o link já enviado | O contexto passa a trazer o link já enviado quando a reunião está aprovada, com a regra de reenviá-lo. O alerta de confiabilidade reconhece "deixa eu confirmar" e "já retorno" |

**Aprendizado:** com aprovação assíncrona, o P.H. precisa saber em que pé está cada pendência. Antes, o resultado chegava
na mesma rodada; agora pode chegar entre duas mensagens do lead, e o contexto precisa refletir isso.
