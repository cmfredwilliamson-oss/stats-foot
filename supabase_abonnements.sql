-- Table des abonnements (à exécuter une seule fois dans Supabase : SQL Editor -> New query -> Run)
create table if not exists public.abonnements (
    deposit_id  uuid primary key,          -- identifiant du paiement pawaPay
    telephone   text not null,             -- numéro au format 242XXXXXXXXX
    operateur   text,                      -- MTN_MOMO_COG ou AIRTEL_COG
    montant     integer,                   -- en XAF
    devise      text default 'XAF',
    statut      text not null default 'EN_ATTENTE',   -- EN_ATTENTE, PAYE, ECHEC
    cree_le     timestamptz default now(),
    paye_le     timestamptz,
    expire_le   timestamptz,
    code_acces  text,                      -- code à 6 chiffres donné à l'abonné
    motif       text                       -- raison d'un échec
);

create index if not exists abonnements_telephone_idx on public.abonnements (telephone, statut);

-- Sécurité : la table n'est lisible que par la clé "service_role" (utilisée par l'application).
alter table public.abonnements enable row level security;
