# Diário de validação: Fase 5b (Supabase e hospedagem no Railway)

> Mesmo método das fases anteriores: cada teste real é revisado, e as falhas viram testes, regras ou decisões.
> Decisões da fase: 043 (Railway + Supabase) e 044 (programa pronto para a nuvem).

---

## Teste 1: Supabase e migração dos leads de teste

**Resultado: aprovado.** Projeto `brax-sdr` (região São Paulo, plano gratuito, RLS automática), tabela criada com
`supabase/esquema.sql`. A conexão foi conferida pelo formato da chave (`sb_secret_`, sem mostrar o valor) e por uma consulta.

| Problema | Causa | Correção |
|---|---|---|
| Chave "vazia" | O `.env` ainda tinha o nome antigo `SUPABASE_SERVICE_ROLE_KEY`, de um modelo da Fase 1 | Variável renomeada para `SUPABASE_SECRET_KEY` (o nome documentado no `.env.example`) |
| `migrar_para_supabase.py` não achava o código | Faltava o ajuste de caminho que os outros scripts da raiz têm | Corrigido |

A migração rodou primeiro em **modo simulação** (lista o que seria copiado) e só depois com `--gravar`: 22 leads.
Antes de gravar, o lead de teste com o **e-mail real** do dono do projeto foi apagado do PC e do HubSpot (contato
encontrado pela busca por e-mail e pelo campo "ID do lead na BRAX"; a exclusão foi confirmada por consulta direta).

Um lead novo ("teste-supabase") conversou com o P.H. e foi gravado e relido do banco. **Observação:** nessa conversa o
P.H. não registrou os dados que a lead deu na primeira mensagem. Não se repetiu no teste seguinte; fica em observação.

## Teste 2: o P.H. no Railway, de ponta a ponta

Endereço: `https://brax-sdr-agent-production.up.railway.app` (modo `meta`, envio real desligado, decisão 032).

**Travas de segurança, testadas de fora:**

| Teste | Esperado | Resultado |
|---|---|---|
| `GET /saude` | 200 | ✅ `{"ok":true,"modo":"meta"}` |
| Verificação da Meta com token errado | 403 | ✅ |
| Mensagem sem assinatura | 403 | ✅ |
| Programa no modo simulado com `PORT` definida | não liga | ✅ (testado no PC) |

**Conversa real:** mensagens no formato da Meta, **assinadas com o segredo do app** (como a Meta faz), de um lead fictício
(Rafael, Nuvem Azul, 12 pessoas, R$ 15 mil/mês). Resultado: identificação como assistente virtual, dados registrados,
roteamento **self-service**, link do app com o aviso de segurança, lead no Supabase e contato, empresa e negócio
("Qualificado – app") no HubSpot.

**Falha encontrada: o Supabase estava pausado.** A primeira mensagem chegou ao Railway (200), mas o P.H. não conseguiu
gravá-la: o endereço do banco nem existia mais no DNS. O plano gratuito pausa projetos sem uso, e o projeto ficou parado
entre a migração e o deploy. Depois do *Resume*, os 23 leads estavam intactos; a mensagem enviada durante a pausa se perdeu
(o webhook responde "ok" à Meta antes de processar, então a Meta não reenvia).

**Correção:** um **sinal de vida** a cada 6 horas (uma consulta leve ao banco) dentro do próprio P.H. Sem ele, se o token
do Gmail vencer e ninguém mandar mensagem, nada mais tocaria no banco e ele pausaria de novo, derrubando tudo em silêncio.

**Aprendizado:** em planos gratuitos, "ficar parado" é um modo de falha. O monitoramento precisa cobrir as dependências,
não só o servidor: o `/saude` do Railway dizia "ok" enquanto o banco estava fora do ar.

## Pendências da fase

- Apontar o webhook da Meta para o endereço do Railway (no lugar do ngrok) e testar com o botão "Testar" da Meta.
- Publicar o app OAuth do Gmail (hoje em modo de teste, o token vence em 7 dias). Adiado: o Google pede dados de branding.
- Confirmar o plano Hobby do Railway ao fim do teste gratuito.
