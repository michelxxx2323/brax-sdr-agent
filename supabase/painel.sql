-- Ambiente do painel comercial no Supabase (Fase 7, decisão 046).
-- Como usar: no painel do Supabase, abra "SQL Editor", cole este arquivo inteiro e clique em "Run".
-- Pode rodar mais de uma vez. Não altera nem apaga nenhum lead.
--
-- Ideia: o painel (Lovable) NUNCA lê a tabela leads direto nem grava nada. Ele lê três visões (views) prontas:
--   painel_leads      um lead por linha, com os dados de qualificação e a etapa do funil já calculada
--   painel_mensagens  a conversa de cada lead, só o texto (sem os detalhes internos das ferramentas)
--   painel_eventos    a linha do tempo de cada lead (roteamento, aprovação, transferência...)
-- As visões usam "security_invoker": respeitam as regras de acesso (RLS) de quem está consultando.

-- 1. Regra de acesso: usuário LOGADO (o time) pode LER os leads. Não existe regra para gravar, então o painel
--    não consegue criar, alterar ou apagar nada. Visitante não logado continua sem ver nada.
drop policy if exists "time comercial le leads" on public.leads;
create policy "time comercial le leads" on public.leads
    for select to authenticated using (true);

-- 2. Um lead por linha, pronto para tabelas, filtros e gráficos.
create or replace view public.painel_leads with (security_invoker = true) as
select
    l.id,
    l.canal,
    l.nome_contato,
    l.empresa,
    l.estado -> 'dados' ->> 'cargo'                          as cargo,
    l.estado -> 'dados' ->> 'setor'                          as setor,
    l.estado -> 'dados' ->> 'tipo_empresa'                   as tipo_empresa,
    nullif(l.estado -> 'dados' ->> 'funcionarios', '')::numeric::integer as funcionarios,
    nullif(l.estado -> 'dados' ->> 'gasto_mensal', '')::numeric as gasto_mensal,
    l.estado -> 'dados' ->> 'dor'                            as dor,
    l.estado -> 'dados' ->> 'solucao_atual'                  as solucao_atual,
    l.estado -> 'dados' -> 'sinais_de_compra'                as sinais_de_compra,
    l.estado -> 'dados' ->> 'motivo_encerramento'            as motivo_encerramento,
    l.faixa,
    l.motivo_faixa,
    l.aprovacao,
    l.prioridade,
    l.opt_out,
    l.encerrada,
    l.transferido_para_vendedor,
    l.sem_resposta,
    l.custo_total_usd,
    l.total_mensagens,
    -- Etapa do funil (mesma lógica do HubSpot, src/brax_sdr/crm.py, com duas etapas a mais para o painel).
    case
        when l.faixa = 'fora_do_icp'                                          then 'fora_do_perfil'
        when l.opt_out or l.sem_resposta
             or l.estado -> 'dados' ->> 'motivo_encerramento' is not null     then 'perdido'
        when l.faixa = 'executivo' and l.aprovacao in ('aprovada', 'novo_horario') then 'reuniao_aprovada'
        when l.faixa = 'executivo' and l.aprovacao is distinct from 'recusada'     then 'reuniao_solicitada'
        when l.faixa in ('self_service', 'executivo')                         then 'qualificado_app'
        when l.faixa = 'humano' or l.transferido_para_vendedor                then 'com_vendedor'
        else 'em_qualificacao'
    end as etapa,
    l.criado_em,
    l.atualizado_em
from public.leads l;

-- 3. A conversa de cada lead, uma mensagem por linha, só com o texto que o lead e o P.H. trocaram.
create or replace view public.painel_mensagens with (security_invoker = true) as
select
    l.id            as lead_id,
    m.ordem::integer as ordem,
    case when m.mensagem ->> 'role' = 'user' then 'lead' else 'ph' end as autor,
    m.texto
from public.leads l
cross join lateral (
    select
        e.mensagem,
        e.ordem,
        case
            when jsonb_typeof(e.mensagem -> 'content') = 'string' then e.mensagem ->> 'content'
            else (
                select string_agg(b.bloco ->> 'text', E'\n\n' order by b.posicao)
                from jsonb_array_elements(e.mensagem -> 'content') with ordinality as b(bloco, posicao)
                where b.bloco ->> 'type' = 'text'
            )
        end as texto
    from jsonb_array_elements(l.estado -> 'mensagens') with ordinality as e(mensagem, ordem)
) m
where m.texto is not null and btrim(m.texto) <> '';

-- 4. Linha do tempo de cada lead.
create or replace view public.painel_eventos with (security_invoker = true) as
select
    l.id                           as lead_id,
    (ev.evento ->> 'quando')::timestamptz as quando,
    ev.evento ->> 'tipo'           as tipo,
    ev.evento ->> 'detalhe'        as detalhe
from public.leads l
cross join lateral jsonb_array_elements(l.estado -> 'eventos') as ev(evento);

-- 5. Permissões: só usuários logados consultam as visões. Visitantes anônimos, nada.
revoke all on public.painel_leads, public.painel_mensagens, public.painel_eventos from anon;
grant select on public.painel_leads, public.painel_mensagens, public.painel_eventos to authenticated;
