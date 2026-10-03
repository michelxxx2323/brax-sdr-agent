-- Esquema do banco da BRAX no Supabase (Fase 5b, decisão 043).
-- Como usar: no painel do Supabase, abra "SQL Editor", cole este arquivo inteiro e clique em "Run".
-- Pode rodar mais de uma vez: nada é apagado.

-- Um registro por lead. A coluna "estado" guarda o lead completo (histórico, dados, eventos), igual ao arquivo JSON
-- que o P.H. usava no PC. As outras colunas repetem os campos mais consultados, para o painel comercial (Fase 7)
-- filtrar e contar sem abrir o JSON.
create table if not exists public.leads (
    id                        text primary key,
    canal                     text not null,
    nome_contato              text,
    empresa                   text,
    faixa                     text,          -- self_service | executivo | fora_do_icp | humano
    motivo_faixa              text,
    aprovacao                 text,          -- pendente | aprovada | novo_horario | recusada
    prioridade                integer not null default 0,
    opt_out                   boolean not null default false,
    encerrada                 boolean not null default false,
    transferido_para_vendedor boolean not null default false,
    sem_resposta              boolean not null default false,
    custo_total_usd           numeric(10, 5) not null default 0,
    total_mensagens           integer not null default 0,
    estado                    jsonb not null,
    criado_em                 timestamptz not null default now(),
    atualizado_em             timestamptz not null default now()
);

create index if not exists leads_faixa_idx on public.leads (faixa);
create index if not exists leads_atualizado_em_idx on public.leads (atualizado_em desc);

-- Segurança: a proteção por linha (RLS) fica ligada e SEM nenhuma regra de acesso. Resultado: a chave pública do
-- projeto não lê nem grava nada; só o servidor do P.H., com a chave secreta, acessa a tabela. O painel da Fase 7
-- vai ganhar regras próprias (somente leitura, para usuários do time logados).
alter table public.leads enable row level security;
