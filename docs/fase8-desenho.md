# Fase 8: página pública para conversar com o P.H. (desenho)

> Decisões 045 (só dados fictícios), 047 (a página não grava direto no banco) e 060 (este desenho).
> Escolhas do dono do projeto em 12/10/2026: página **dentro do painel no Lovable**, **chat + bastidores ao lado**,
> conversas **guardadas por 7 dias**, teto de gasto de **US$ 0,30 por dia**.

## Visão geral

```
Visitante ──▶ Lovable: rota pública /simular (sem login)
                 │  (1) aviso de dados fictícios + confirmação
                 │  (2) POST https://<railway>/simulador/mensagem   { sessao, texto }
                 ▼
            Railway: servidor do P.H.
                 │  valida, limita, mascara dados pessoais
                 │  P.H. de verdade (mesmo agente, mesmo cérebro, mesmas travas)
                 │  grava no Supabase como origem "simulador" (fora do funil e do HubSpot)
                 ▼
            resposta + bastidores  { texto, faixa, etapa, temperatura, dados, eventos }
```

A rota pública **não** fala com o Supabase: a chave pública continua sem ler nada (`verificar_acesso_painel.py`, 17/17).
Tudo o que o visitante vê vem da resposta do servidor.

## Experiência

1. **Abertura:** o que é a BRAX (fictícia) e o P.H., e o aviso: "Use só dados fictícios. Não informe CPF, CNPJ,
   telefone, e-mail ou dados de cartão reais." O botão "Entendi" libera a **escolha do canal**: "Testar pelo WhatsApp"
   (balões de chat, respostas curtas, uma pergunta por vez) ou "Testar por e-mail" (campo de assunto, respostas mais
   completas, com "Re: assunto" e a assinatura da BRAX). O e-mail é simulado na página, sem envio real.
2. **Sugestões para começar** (botões que preenchem a primeira mensagem): "Sou founder de um SaaS com 12 pessoas",
   "Sou CFO de uma empresa de 60 pessoas", "Sou MEI", "Quero falar com uma pessoa". O visitante também pode escrever livre.
3. **Conversa** no estilo do canal escolhido, com o P.H. respondendo como faria a um lead real.
4. **Bastidores ao lado**, ao vivo: dados registrados, faixa, etapa do funil, temperatura (com o medidor de 0 a 16) e os
   eventos de cada resposta ("Faixa definida: Self-service", "Transferido para vendedor", "Bastidor removido"...).
   No celular, os bastidores ficam numa aba.
5. **Reiniciar:** um botão começa outra conversa (nova sessão).

## Regras no servidor (o código garante)

| Regra | Como |
|---|---|
| Só dados fictícios | Dados pessoais (CPF, CNPJ, telefone, e-mail, cartão) são trocados por `[removido]` **antes** de chegar à IA e ao banco |
| Fora do funil comercial | Lead com `origem: simulador`: não vai para o HubSpot nem para o Slack; aprovações de executivo são simuladas e marcadas como tal; o painel comercial não mostra essas conversas |
| Guarda curta | Conversas do simulador apagadas depois de 7 dias (junto do sinal de vida, a cada 6 horas) |
| Custo | Teto global de **US$ 0,30 por dia** (fuso de São Paulo); ao bater, a página avisa que volta amanhã. Também valem os limites por lead que já existem (decisão 021) |
| Abuso | Limite de mensagens por sessão (20) e por endereço de internet por dia (60); mensagens longas recusadas como hoje |
| Origem | O servidor só aceita chamadas do endereço publicado do painel (CORS) |

## O que já existe e é reaproveitado

O agente inteiro (prompt, cérebro, ferramentas, travas, resumo, temperatura), a memória no Supabase e a proteção de custo
por lead. O que é novo: a rota `/simulador/mensagem`, o mascaramento de dados pessoais, o marcador `origem`, o teto
diário, a limpeza de 7 dias, o filtro no painel e a página no Lovable.

## Etapas

1. **Servidor** (Claude Code): rota, mascaramento, limites, teto, origem, limpeza, filtro nas visões, testes e cenários
   de eval com dados pessoais na mensagem.
2. **Página** (Lovable): prompt com a rota pública, o aviso, o chat e os bastidores.
3. **Validação:** testes de abuso (dados pessoais, excesso de mensagens, teto), conferência de que nada aparece no funil
   nem no HubSpot, e uma rodada no celular.

## Fora de escopo por enquanto

CAPTCHA (dá para acrescentar o Cloudflare Turnstile se houver abuso), voz e envio pelo WhatsApp real.
