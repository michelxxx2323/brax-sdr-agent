# Produto BRAX

> O que o agente pode explicar sobre o produto. Funcionalidades marcadas com `<!-- REVISAR -->` são inventadas
> e precisam de validação. Se o lead perguntar algo que não está aqui, o agente **não inventa**: diz que vai
> confirmar com o time ou oferece falar com uma pessoa.

## Módulos

### 1. Conta digital PJ
- Abertura 100% pelo app oficial, com análise cadastral. **Aprovação não é garantida.**
- Pix (enviar, receber, chaves e QR Code), TED e boletos.
- Múltiplos usuários com permissões diferentes (ex.: sócio aprova, financeiro opera). <!-- REVISAR -->
- Prazo médio de análise de até 2 dias úteis após o envio dos documentos no app. <!-- REVISAR: o agente nunca promete prazo, só informa a média -->

### 2. Cartões corporativos
- Cartões **virtuais** (emitidos na hora, no app) e **físicos** (entregues pelo correio). <!-- REVISAR -->
- Um cartão por pessoa, por fornecedor ou por projeto (ex.: um cartão virtual só para a AWS). <!-- REVISAR -->
- Limites e regras definidos pela empresa: valor por mês, categoria permitida, bloqueio instantâneo.
- Aceitos em compras nacionais e internacionais.
- O **limite total** da empresa depende de análise. O agente **nunca** informa ou promete limite.

### 3. Gestão de despesas
- Foto do comprovante pelo app ou WhatsApp logo após a compra. <!-- REVISAR -->
- Categorização automática e centro de custo.
- Reembolso de despesas pagas fora do cartão, com aprovação no app.
- Políticas de gasto: o que precisa de aprovação, quem aprova, alertas.
- Painel de assinaturas: lista de todos os softwares pagos com os cartões, com valor e responsável. <!-- REVISAR -->

### 4. Integração contábil
- Exportação de extrato e despesas em formatos usados por contadores (OFX, CSV). <!-- REVISAR -->
- Integrações com ERPs usados por startups (ex.: Omie, Conta Azul). <!-- REVISAR: são empresas reais; confirmar se o case pode citar -->
- Acesso de leitura para o contador.

### 5. Saldo remunerado (opcional) <!-- REVISAR: manter ou remover? -->
- O saldo pode render conforme regras do produto.
- **Guardrail:** o agente nunca apresenta rendimento como garantido nem compara com investimentos.

## Como cada dor do ICP é resolvida

| Dor (ver [icp.md](../vendas/icp.md)) | Funcionalidade |
|---|---|
| Cartão compartilhado ou pessoal do sócio | Cartões individuais com limite por pessoa |
| Reembolso manual por planilha | Comprovante no app + reembolso com aprovação |
| Sem controle de assinaturas | Cartão virtual por fornecedor + painel de assinaturas |
| Fechamento contábil lento | Exportação e integração contábil, acesso do contador |
| Custo alto em compras internacionais | Cartão internacional com tarifas menores <!-- REVISAR --> |
| Banco tradicional burocrático | Abertura e emissão de cartões pelo app |

## Como abrir a conta

1. Baixar o app oficial da BRAX (link enviado pelo agente).
2. Cadastrar a empresa e os sócios **dentro do app**.
3. Enviar os documentos **dentro do app**.
4. Aguardar a análise.

O agente **nunca** recebe documentos, senhas ou códigos por WhatsApp ou e-mail. Ver [guardrails](../regras/guardrails.md).
