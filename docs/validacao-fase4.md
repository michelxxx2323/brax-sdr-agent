# Diário de validação: Fase 4 (canal de WhatsApp)

> Mesmo método das fases anteriores: cada conversa real é revisada, e as falhas viram testes, regras ou decisões.

Modelo de conversa: `claude-haiku-4-5`. Canal: WhatsApp em **modo simulado** (decisão 030): o simulador faz o papel
da Meta, com avisos no formato da WhatsApp Cloud API e assinatura HMAC, e o servidor do webhook roda no computador.

---

## Teste 1: "Ana, Lumen" (28 pessoas, R$ 70 mil/mês): esperado executivo com aprovação, pelo webhook

**Resultado: aprovado.** O fluxo inteiro passou pelo servidor do webhook:
- Dados registrados já na primeira mensagem (nome, empresa, tipo, tamanho), sem perguntas repetidas.
- Roteamento para executivo com o motivo registrado; aprovação pedida na resposta certa, aprovada no terminal do
  servidor; link de agenda enviado junto com o dia combinado.
- Áudio: o P.H. pediu, com educação, que a mensagem fosse escrita (o áudio não foi aberto).
- Depois do "valeu", a conversa foi encerrada pelo código; as mensagens seguintes ficaram em silêncio, sem chamar a API.
- Todas as mensagens abaixo do limite do WhatsApp. Custo da conversa: cerca de US$ 0,06.

**Detalhes menores, para medir na Fase 6:**
- O resumo para aprovação dizia "Ana, parece ser founder/CEO", mas o cargo não foi informado: o resumo para o time
  comercial não deve conter palpites.
- "Boa sorte na segunda!" (quem conversa na reunião é o executivo), já anotado na Fase 2.

## Teste 2: integração real com a Meta, só recebimento (decisão 032)

Configuração: app na Meta com o número de teste da WhatsApp Cloud API, servidor no computador exposto por um túnel
ngrok, `WHATSAPP_MODO=meta` e envio desligado (nenhuma mensagem sai para ninguém).

**Resultado: aprovado.**
- `diagnosticar_whatsapp.py` confirmou token e número de teste na Meta (só leitura).
- A Meta verificou o endereço do webhook com o token de verificação.
- O botão "Testar" do campo `messages` enviou uma mensagem de exemplo **real e assinada pela Meta**, de um número fictício:
  o servidor conferiu a assinatura (HTTP 200), criou o lead e o P.H. respondeu ("Oi! Aqui é o P.H., assistente virtual da
  BRAX 👋 ... Qual é o nome da sua empresa?"). A resposta apareceu só no terminal, como previsto.

| Problema | Causa | Correção |
|---|---|---|
| A Meta não conseguia validar o webhook | A URL foi cadastrada sem `https://`; além disso, o exemplo do guia citava `.ngrok-free.app`, mas os domínios gratuitos novos terminam em `.ngrok-free.dev` | URL completa (`https://<domínio>/webhook`). O diagnóstico pelo painel local do ngrok (porta 4040) mostrou que a chamada da Meta nem chegava ao túnel, o que isolou o problema no cadastro da URL |

**Pendente (por escolha):** o envio real ao WhatsApp, que exige cadastrar um número na lista do número de teste.
