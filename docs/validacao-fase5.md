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
