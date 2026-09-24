# ICP: Perfil de Cliente Ideal

> Este arquivo diz ao agente **para quem** a BRAX existe e para quem não existe.
> Ele é a base da qualificação, das objeções e do tom de voz. Os números marcados como
> *hipótese* devem ser revisados conforme o agente conversar com leads reais.

## Resumo em uma frase

Startups brasileiras em crescimento, com CNPJ ativo e time em expansão, que perderam o controle
dos gastos da empresa e querem cartões corporativos, conta PJ e gestão de despesas em um só lugar.

## Perfil da empresa

| Critério | Ideal | Aceitável |
|---|---|---|
| Tipo | Startup com CNPJ ativo (LTDA ou S.A.) | Empresa de tecnologia tradicional em crescimento |
| Estágio | Pós-seed até Série B | Bootstrapped com receita recorrente |
| Funcionários | 10 a 200 | 5 a 10 (com plano de contratar) |
| Setores | SaaS, marketplaces, e-commerce, fintechs, healthtechs | Agências digitais, consultorias de tecnologia |
| Modelo de trabalho | Remoto ou híbrido, time distribuído | Presencial |
| Gastos recorrentes | Assinaturas de software, mídia paga, viagens, compras internacionais | Apenas despesas locais |

## Sinais de que é um bom momento (sinais de compra)

O agente deve dar mais prioridade quando perceber um destes sinais:

- **Captou uma rodada recentemente** — dinheiro novo, time crescendo, investidor cobrando controle.
- **Está contratando rápido** — muitas vagas abertas, mais gente precisando de cartão.
- **Contratou a primeira pessoa de financeiro** — alguém agora é dono do problema.
- **Abriu escritório ou nova cidade** — novas despesas e novas pessoas gastando.
- **Paga muito software em dólar** — dor com IOF, câmbio e cartão pessoal de sócio.
- **Reclamou do banco atual** — burocracia, tarifas, demora para liberar cartões.

## Dores que resolvemos

1. **Cartão compartilhado ou cartão pessoal do sócio** pagando despesas da empresa.
2. **Reembolso manual** por planilha, com nota fiscal perdida e atraso no pagamento.
3. **Sem controle de assinaturas** — ninguém sabe quantas ferramentas a empresa paga.
4. **Fechamento contábil lento** — o contador cobra comprovantes todo mês.
5. **Custo alto em compras internacionais** — IOF e spread em ferramentas pagas em dólar.
6. **Banco tradicional burocrático** — demora para abrir conta e emitir cartões.

## Personas (quem conversa com o agente)

### Founder / CEO
- **Contexto:** em startups menores, é quem decide tudo, inclusive o banco.
- **O que importa:** tempo. Quer resolver rápido e sem burocracia.
- **Como falar:** direto, poucas perguntas, mostrar economia de tempo.

### Head de Finanças / CFO
- **Contexto:** em startups maiores, é o decisor principal.
- **O que importa:** controle, relatórios, integração com o contador e com o ERP, políticas de gasto.
- **Como falar:** mais detalhado, com funcionalidades de controle e segurança.

### Operações / People / Office Manager
- **Contexto:** sofre a dor no dia a dia (reembolsos, cartões de funcionários).
- **O que importa:** menos trabalho manual.
- **Como falar:** focar na rotina. Geralmente **não é o decisor**: o agente deve descobrir quem decide.

## Quem NÃO é cliente

O agente deve identificar esses casos com educação e encerrar ou redirecionar:

- **Pessoa física** ou quem ainda não tem CNPJ.
- **MEI e autônomos** — o produto não foi desenhado para eles (indicar outra solução, sem prometer nada).
- **Empresas em setores que exigem análise especial** — o agente não decide: registra e passa para um humano.
- **Quem só quer crédito ou empréstimo** — não é o produto principal; não prometer limite.

## Roteamento por faixa (*hipótese*)

| Faixa | Critério | Próximo passo |
|---|---|---|
| Self-service | Até 20 funcionários **e** gasto mensal até R$ 50 mil | Agente envia o link para abrir a conta no app |
| Executivo | Mais de 20 funcionários **ou** gasto mensal acima de R$ 50 mil | Agente agenda conversa com um executivo humano |
| Fora do ICP | Qualquer critério da seção acima | Agente agradece, registra o motivo no CRM e encerra |

## Como este arquivo é usado

- `vendas/qualificacao.md` transforma estes critérios em perguntas.
- `vendas/objecoes.md` responde às dúvidas de cada persona.
- `vendas/handoff.md` usa a tabela de roteamento.
- O agente registra no CRM a faixa e o motivo, para medir depois se as faixas estão certas.
