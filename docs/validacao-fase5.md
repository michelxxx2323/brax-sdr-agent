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

## Teste 3: "Carla, Artifact": reteste da aprovação pelo Slack

**Resultado: aprovado.** Aprovação clicada 11 segundos após o pedido; o retorno com o link apareceu sozinho no simulador
2 segundos depois; após o "Obrigado", a conversa foi encerrada e a despedida seguinte não chamou a API.

**Detalhe corrigido:** o retorno dizia "Uma pessoa do time vai te ligar na hora marcada", um detalhe inventado. Regra
nova no cérebro e na instrução do retorno: não dizer o formato da reunião (decisão 035).

## Teste 4: "Elisa, Kora": botão "Sugerir outro horário"

**Resultado: aprovado.** No Slack, a janela pediu o horário ("segunda às 14h"); 2 segundos depois a lead recebeu:
"Confirmei com o time: sexta de manhã não conseguem, mas segunda às 14h está livre. Se funcionar melhor para você,
confirma por aqui: [link]". Depois do "Ok obrigada", a conversa foi encerrada.

O resumo do Sonnet não inventou o cargo ("motivo do contato não informado", "solução atual não informada").

| Problema | Causa | Correção |
|---|---|---|
| O resumo dizia "aguardando confirmação de período e dia", mas a lead tinha acabado de dizer "sexta de manhã" | O resumo é pedido durante a resposta, antes de a última mensagem do lead ser salva no histórico | A disponibilidade informada é passada ao Sonnet junto com a conversa |

## Teste 5: "Diego": transferir para humano

**Resultado: o alerta funcionou.** Ao pedido "Quero falar com uma pessoa real", o P.H. chamou `transferir_para_humano`, o
alerta chegou ao Slack e o lead foi avisado de que uma pessoa do time continua em horário comercial.

| Problema | Causa | Correção |
|---|---|---|
| Depois de transferir, o P.H. seguiu respondendo ("Tranquilo! A gente se fala em breve") | Nada pausava o P.H. após a transferência | O P.H. fica pausado para o lead; as mensagens vão para a thread do alerta no Slack; botão "Devolver ao P.H." (decisão 036) |

## Melhorias futuras identificadas

- **Responder ao lead de dentro do Slack** durante o atendimento humano (hoje a pessoa do time usa os próprios canais).
- **Agenda real ligada ao CRM** (reuniões do HubSpot): possível, deixada de fora por privacidade (decisão 035).
- **Busca de empresas com consistência eventual:** com vários processos (hospedagem), a proteção contra duplicadas exigiria
  uma trava ou uma chave única, como o domínio da empresa.

## Teste 6: "Fabio, Linxe": reteste da transferência para humano

**Resultado: a pausa nem foi exercitada, porque a transferência não aconteceu.**

| Problema | Causa | Correção |
|---|---|---|
| O lead pediu "quero falar com uma pessoa" **duas vezes** e o P.H. seguiu qualificando ("antes de eu te conectar, deixa eu entender melhor...") | O modelo priorizou o roteiro de qualificação sobre a regra G4 (no teste do Diego, ele tinha transferido) | O **código reconhece o pedido** antes de chamar a IA e transfere: alerta no Slack, pausa e mensagem padronizada (decisão 036) |
| O retorno da aprovação disse de novo "Um executivo da BRAX vai te ligar" | A regra da decisão 035 estava só na instrução | Trava no código: retorno que menciona ligação, vídeo ou reunião presencial cai na mensagem padronizada |

**Aprendizado:** a mesma regra pode funcionar num teste (Diego) e falhar no seguinte (Fabio). Um teste que passa não prova que
o modelo sempre obedece; regras inegociáveis (como o G4) precisam de garantia em código. Na Fase 6, os evals vão medir com
que frequência isso acontece.
