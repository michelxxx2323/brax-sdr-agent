# Diário de validação: Fase 7 (painel do time comercial no Lovable)

> Mesmo método das fases anteriores: cada teste real é revisado, e as falhas viram testes, regras ou decisões.
> Decisões da fase: 045 (só dados fictícios) e 046 (painel lê visões somente leitura).

---

## Teste 1: ambiente do Supabase para o painel

**Resultado: aprovado.** `supabase/painel.sql` rodado no SQL Editor, cadastro público desligado, usuário do painel criado
pelo administrador. O projeto do Lovable foi conectado ao Supabase antes do primeiro prompt.

**As visões:** `painel_leads` trouxe os 24 leads (fictícios), com a etapa do funil calculada (7 reuniões aprovadas,
7 qualificados pelo app, 6 em qualificação, 2 fora do perfil, 1 com vendedor, 1 perdido). `painel_mensagens` mostra só o
texto trocado, na ordem, sem os blocos internos das ferramentas. `painel_eventos` traz a linha do tempo.

**Depois de conectar o Lovable:** o banco continuou com os mesmos objetos (a tabela `leads` e as três visões): nada foi
criado ou alterado.

**Acesso, testado de fora:**

| Quem | Tentativa | Esperado | Resultado |
|---|---|---|---|
| Sem chave nenhuma | ler `painel_leads` | recusar | ✅ 401 |
| Qualquer pessoa | criar conta pelo cadastro público | recusar | ✅ "Signups not allowed" |
| Visitante com a chave pública, sem login | ler as três visões | recusar | ✅ "permission denied" |
| Visitante com a chave pública, sem login | ler a tabela `leads` | nada | ✅ 0 linhas (RLS) |
| Visitante com a chave pública, sem login | gravar um lead falso | recusar | ✅ bloqueado pelo RLS |

A chave pública fica no código do site, e qualquer pessoa pode copiá-la; por isso o teste que importa é o dela sem login.
**Melhoria:** a leitura da tabela `leads` devolvia uma lista vazia em vez de "permissão negada". Não vazava nada, mas
o visitante anônimo também perdeu a permissão na tabela (segunda camada além do RLS).

## Teste 2: revisão do acesso (decisão 047)

Uma revisão do desenho levantou que o usuário logado conseguia ler a tabela `leads` inteira, inclusive o `estado` com os
detalhes internos das ferramentas, porque as visões usavam `security_invoker`. O novo `verificar_acesso_painel.py`
confirmou o problema (10/11, com ❌ em "logado NÃO lê a tabela leads").

**Correção:** visões com a permissão do dono do banco e a tabela fechada para `anon` e `authenticated`.

**Resultado: aprovado, 11/11.** Visitante sem login: nenhuma visão, tabela recusada, gravação recusada, cadastro
desligado. Conta demo logada: lê as três visões (24 leads, 296 mensagens, 124 eventos), não lê a tabela (403) e não grava
(403). O servidor do P.H. (chave secreta) continua lendo e gravando, e o Railway segue no ar.
