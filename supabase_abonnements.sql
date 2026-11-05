-- Table des abonnements (à exécuter une seule fois dans Supabase : SQL Editor -> New query -> Run)
create table if not exists public.abonnements (
    deposit_id  uuid primary key,          -- identifiant du paiement pawaPay
    telephone   text not null,             -- numéro international, ex. 242061234567
    operateur   text,                      -- ex. MTN_MOMO_COG, ORANGE_CIV, MPESA_KEN
    pays        text,                      -- code pays, ex. COG, CIV, KEN
    montant     numeric,                   -- montant payé dans la monnaie locale
    devise      text,                      -- ex. XAF, XOF, KES
    statut      text not null default 'EN_ATTENTE',   -- EN_ATTENTE, PAYE, ECHEC
    cree_le     timestamptz default now(),
    paye_le     timestamptz,
    expire_le   timestamptz,
    code_acces  text,                      -- code à 6 chiffres donné à l'abonné
    motif       text                       -- raison d'un échec
);

-- Mise à jour d'une table déjà créée avec l'ancienne version (sans danger si déjà fait)
alter table public.abonnements add column if not exists pays text;
alter table public.abonnements alter column montant type numeric;
alter table public.abonnements alter column devise drop default;

create index if not exists abonnements_telephone_idx on public.abonnements (telephone, statut);

-- Sécurité : la table n'est lisible que par la clé secrète (utilisée par l'application).
alter table public.abonnements enable row level security;
