# Diário de validação: Fase 8 (página pública "Converse com o P.H.")

> Mesmo método das fases anteriores: cada teste real é revisado, e as falhas viram testes, regras ou decisões.
> Decisões da fase: 045 (só dados fictícios), 047 (a página não grava direto no banco), 060 (desenho) e 061 (ajustes
> depois do primeiro teste). Desenho: [fase8-desenho.md](fase8-desenho.md).

Página: `https://sdr-brax.lovable.app/simular` · Servidor: `POST https://brax-sdr-agent-production.up.railway.app/simulador/mensagem`

---

## Teste 1: a página chama o servidor (CORS)

**Achado:** a primeira versão da página recebia erro em todas as mensagens, e o diagnóstico do Lovable apontou um
"503" no servidor. Uma chamada direta à rota mostrou que o P.H. respondia normalmente (200). O erro estava no navegador:
antes de mandar a mensagem, ele pergunta ao servidor se aquele site pode chamá-lo, e a variável com os sites
autorizados (`BRAX_SIMULADOR_ORIGENS`) ainda não existia no Railway. Era a trava de segurança funcionando como desenhada.

**Correção:** variável criada no Railway com os dois endereços do Lovable (publicado e pré-visualização).

**Resultado: aprovado.**

| Site que chama o P.H. | Resultado |
|---|---|
| `https://sdr-brax.lovable.app` (publicado) | ✅ autorizado |
| `https://preview--sdr-brax.lovable.app` (pré-visualização) | ✅ autorizado |
| `https://site-qualquer.com` | ✅ recusado (400) |

Também foi corrigido o formato do bloqueio no prompt do Lovable: `bloqueado` é um texto (`"teto_diario"`), não um objeto.

## Teste 2: conversa completa nos dois canais (decisão 061)

Teste de ponta a ponta feito por outra instância do Claude, como visitante: uma founder de SaaS com 12 pessoas no
WhatsApp (self-service) e um CFO de S.A. com 60 pessoas e R$ 120 mil/mês no e-mail (executivo, com aprovação simulada).
Resposta em cerca de 10 segundos.

**Funcionou:** roteamento correto com o motivo nos bastidores, tom certo em cada canal (e-mail com "Re:", parágrafos e
assinatura), e o P.H. não inventou IOF, cashback nem integração com ERP.

**Achados no agente (todos corrigidos, decisão 061):** tipo de empresa "LTDA" registrado sem a lead dizer; CFO grande
"morno"; IOF e cashback transferidos a um vendedor; oferta sem ligação com a dor do dólar; "Vou registrar o que você me
contou"; resumo desatualizado e, na Marina, contradizendo a faixa; ERP no campo errado; encurtador que quase não
encurtava; assunto do e-mail perdido na segunda mensagem.

**Conferência depois das correções:** na mesma conversa da Marina, o P.H. perguntou o tipo de empresa em vez de
deduzir e respondeu IOF e cashback sem transferir. O resumo refeito pelo Haiku passou a citar a faixa self-service e as
respostas sobre IOF e cashback. Bateria de evals com 2 cenários novos (tipo não dito, IOF/cashback): **23/25**, os dois
novos aprovados.

**Achados na página (Prompt 9 do Lovable):** campo de mensagem empurrado para baixo, sugestões que só preenchem,
rótulos técnicos, selo duplicado e porta de entrada pelo login.

## Teste 3: dados pessoais nunca chegam à IA nem ao banco

Mensagem fictícia com os cinco tipos de dado pessoal no servidor real:

> Meu CPF é 123.456.789-09, CNPJ 12.345.678/0001-90, e-mail joana@lumen-ficticia.com.br, celular (11) 98765-4321 e
> cartão 4111 1111 1111 1111. Somos 12 pessoas e gastamos uns R$ 15.000 por mês.

**Resultado: aprovado.** 5 trechos trocados por `[removido]` antes da IA; "12 pessoas" e "R$ 15.000" preservados.
Lido depois direto do Supabase: origem `simulador` e **nenhum** dos cinco dados em mensagens, dados ou eventos. O P.H.
ainda orientou: "dados pessoais e de cartão não devem ser enviados por aqui. Não preciso deles."

**Observação:** nessa resposta, o P.H. não registrou o tamanho nem o gasto (priorizou o alerta). Ele os pega nas
próximas mensagens; fica como observação de comportamento, sem correção.

## Teste 4: limite de mensagens por conversa

**Achado:** o limite de 20 mensagens bloqueou a conversa na **16ª**. No histórico, os resultados das ferramentas também
têm o papel "user" (é o formato da API da Anthropic), e o código os contava como mensagens do visitante.

**Correção:** contar só o que o visitante escreveu, com um teste que reproduz o caso.

**Resultado depois da correção, no servidor real: aprovado.** 20 mensagens respondidas; a 21ª recebeu "Esta conversa
chegou ao limite de mensagens da demonstração. Use "Reiniciar" para começar outra."

## Teste 5: fora do funil comercial

**Resultado: aprovado.** Com 10 conversas do simulador no banco:

| Verificação | Resultado |
|---|---|
| Conversas do simulador com dados de HubSpot | ✅ nenhuma |
| `painel_leads`, lido como a conta demo | ✅ 0 do simulador (12 leads) |
| `painel_mensagens` | ✅ 0 do simulador (84 mensagens) |
| `painel_eventos` | ✅ 0 do simulador (62 eventos) |

## Teste 6: limites que não foram estourados de propósito

- **60 mensagens por endereço de internet por dia** e **teto de US$ 0,30 por dia:** cobertos por testes automáticos
  (`tests/test_simulador_publico.py`), sem estourar no servidor real. Estourar o teto deixaria a página fora do ar para
  todos até o dia seguinte, e estourar o limite por endereço bloquearia o computador do dono do projeto.
- **Leitura do custo do dia no servidor real:** US$ 0,02 de US$ 0,30 durante a validação, somando as conversas do simulador.
- **Guarda de 7 dias:** a limpeza roda junto com o sinal de vida, a cada 6 horas, e tem teste automático.

## Teste 7: celular

**Resultado: aprovado.** Conferido pelo dono do projeto no telefone: conversa e aba de bastidores funcionando.

## Teste 8: Prompt 9 publicado

**Resultado: aprovado.** O site publicado tem as três rotas (`/`, `/login`, `/simular`) e os ajustes da decisão 061:
página de entrada com os dois botões, conta demo com o botão "Entrar com a conta demo", escala de prioridade de 0 a 19,
rótulos legíveis e sugestões que enviam com um clique. A conta demo entra e lê o painel, sem acesso às tabelas
(`verificar_acesso_painel.py`: 17/17).

## Encerramento

**Fase aprovada pelo dono do projeto em 14/10/2026**, junto com a Fase 7, depois do teste final das três páginas
(`/`, `/login`, `/simular`) e dos ajustes dos Prompts 9 e 10.
