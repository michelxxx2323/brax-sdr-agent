-- Resultados dos evals no Supabase, para a aba "Qualidade" do painel (Fase 7, decisão 050).
-- Como usar: no painel do Supabase, abra "SQL Editor", cole este arquivo inteiro e clique em "Run".
-- Pode rodar mais de uma vez: nada é apagado.
--
-- Quem grava: rodar_evals.py (a cada bateria) e enviar_evals_supabase.py (histórico), com a chave secreta.
-- Quem lê: o painel, só pelas duas visões, com as mesmas regras de painel.sql (decisão 047): visões com a permissão
-- do dono, tabela fechada para anon e authenticated, nada para anon.

-- 1. Uma linha por cenário de cada bateria.
create table if not exists public.evals (
    bateria            text not null,          -- nome do arquivo em evals/resultados (data + modelo)
    cenario            text not null,          -- id do cenário em evals/cenarios.json
    data               timestamptz not null,   -- quando a bateria rodou
    modelo_conversa    text not null,          -- modelo do P.H. avaliado
    modelo_juiz        text,
    titulo             text,
    canal              text,
    passou             boolean not null,       -- todas as verificações objetivas passaram
    falhas             jsonb not null default '[]',   -- verificações que falharam (ex.: ["faixa"])
    notas              jsonb not null default '{}',   -- notas do juiz por critério (1 a 5)
    nota_media         numeric(3, 2),
    problemas          jsonb not null default '[]',   -- problemas apontados pelo juiz
    resumo_juiz        text,
    alertas            jsonb not null default '[]',   -- alertas de guardrail e de estilo durante a conversa
    esperado           jsonb not null default '{}',
    obtido             jsonb not null default '{}',
    mensagens_do_lead  integer,
    custo_usd          numeric(10, 5),
    custo_ph_usd       numeric(10, 5),
    conversa           jsonb not null default '[]',   -- [["lead", "texto"], ["ph", "texto"], ...] (dados fictícios)
    primary key (bateria, cenario)
);

alter table public.evals enable row level security;
revoke all on public.evals from anon, authenticated;

-- 2. Um cenário por linha, com cada critério do juiz numa coluna.
create or replace view public.painel_evals as
select
    e.bateria,
    e.data,
    e.modelo_conversa,
    e.cenario,
    e.titulo,
    e.canal,
    e.passou,
    e.falhas,
    e.nota_media,
    (e.notas ->> 'tom_e_clareza')::integer        as nota_tom_e_clareza,
    (e.notas ->> 'uma_pergunta_por_vez')::integer as nota_uma_pergunta_por_vez,
    (e.notas ->> 'nao_repete_perguntas')::integer as nota_nao_repete_perguntas,
    (e.notas ->> 'honestidade')::integer          as nota_honestidade,
    (e.notas ->> 'guardrails')::integer           as nota_guardrails,
    (e.notas ->> 'conducao')::integer             as nota_conducao,
    e.problemas,
    e.resumo_juiz,
    e.alertas,
    e.esperado,
    e.obtido,
    e.mensagens_do_lead,
    e.custo_usd,
    e.custo_ph_usd,
    e.conversa
from public.evals e;

-- 3. Uma bateria por linha: a evolução da qualidade ao longo do tempo.
create or replace view public.painel_evals_baterias as
select
    e.bateria,
    min(e.data)                                              as data,
    min(e.modelo_conversa)                                   as modelo_conversa,
    count(*)::integer                                        as cenarios,
    count(*) filter (where e.passou)::integer                as aprovados,
    round(avg(case when e.passou then 1.0 else 0.0 end), 3)  as taxa_aprovacao,
    round(avg(e.nota_media), 2)                              as nota_media,
    count(*) filter (where e.alertas::text ~ '"G[1-4]:')::integer as cenarios_com_alerta_de_guardrail,
    round(sum(e.custo_usd), 2)                               as custo_total_usd,
    round(avg(e.custo_ph_usd), 4)                            as custo_medio_ph_usd
from public.evals e
group by e.bateria;

-- 4. Permissões (iguais às do painel.sql).
alter view public.painel_evals reset (security_invoker);
alter view public.painel_evals_baterias reset (security_invoker);
revoke all on public.painel_evals, public.painel_evals_baterias from anon, authenticated;
grant select on public.painel_evals, public.painel_evals_baterias to authenticated;
