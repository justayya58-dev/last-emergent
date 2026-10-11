-- Personal Finance Workbench foundation.
-- Apply to a fresh Supabase project. RLS is the authoritative data boundary.
begin;

create extension if not exists pgcrypto;

create table public.finance_spaces (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  kind text not null check (kind in ('personal', 'office')),
  name text not null check (length(trim(name)) between 1 and 80),
  currency char(3) not null default 'IDR' check (currency ~ '^[A-Z]{3}$'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_id, kind),
  unique (owner_id, id)
);

create table public.accounts (
  id uuid primary key default gen_random_uuid(),
  space_id uuid not null references public.finance_spaces(id) on delete cascade,
  name text not null check (length(trim(name)) between 1 and 100),
  account_type text not null check (account_type in ('cash', 'bank', 'credit_card', 'e_wallet', 'investment', 'other')),
  opening_balance numeric(20,2) not null default 0,
  currency char(3) not null default 'IDR' check (currency ~ '^[A-Z]{3}$'),
  is_archived boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (space_id, id)
);

create table public.categories (
  id uuid primary key default gen_random_uuid(),
  space_id uuid not null references public.finance_spaces(id) on delete cascade,
  name text not null check (length(trim(name)) between 1 and 80),
  direction text not null check (direction in ('income', 'expense', 'both')),
  created_at timestamptz not null default now(),
  unique (space_id, name),
  unique (space_id, id)
);

create table public.transactions (
  id uuid primary key default gen_random_uuid(),
  space_id uuid not null references public.finance_spaces(id) on delete cascade,
  account_id uuid not null,
  category_id uuid,
  kind text not null check (kind in ('income', 'expense', 'transfer')),
  amount numeric(20,2) not null check (amount > 0),
  currency char(3) not null default 'IDR' check (currency ~ '^[A-Z]{3}$'),
  occurred_on date not null,
  description text not null default '' check (length(description) <= 500),
  reference text check (reference is null or length(reference) <= 120),
  status text not null default 'posted' check (status in ('draft', 'posted', 'void')),
  created_by uuid not null default auth.uid() references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (space_id, account_id) references public.accounts(space_id, id),
  foreign key (space_id, category_id) references public.categories(space_id, id)
);

create index transactions_space_date_idx on public.transactions(space_id, occurred_on desc);
create index transactions_account_date_idx on public.transactions(account_id, occurred_on desc);
create index accounts_space_idx on public.accounts(space_id);
create index categories_space_idx on public.categories(space_id);

create or replace function public.set_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger finance_spaces_set_updated_at before update on public.finance_spaces
for each row execute function public.set_updated_at();
create trigger accounts_set_updated_at before update on public.accounts
for each row execute function public.set_updated_at();
create trigger transactions_set_updated_at before update on public.transactions
for each row execute function public.set_updated_at();

alter table public.finance_spaces enable row level security;
alter table public.accounts enable row level security;
alter table public.categories enable row level security;
alter table public.transactions enable row level security;

create policy "owners manage their finance spaces"
on public.finance_spaces for all to authenticated
using (owner_id = (select auth.uid()))
with check (owner_id = (select auth.uid()));

create policy "owners manage accounts in their spaces"
on public.accounts for all to authenticated
using (exists (
  select 1 from public.finance_spaces s
  where s.id = accounts.space_id and s.owner_id = (select auth.uid())
))
with check (exists (
  select 1 from public.finance_spaces s
  where s.id = accounts.space_id and s.owner_id = (select auth.uid())
));

create policy "owners manage categories in their spaces"
on public.categories for all to authenticated
using (exists (
  select 1 from public.finance_spaces s
  where s.id = categories.space_id and s.owner_id = (select auth.uid())
))
with check (exists (
  select 1 from public.finance_spaces s
  where s.id = categories.space_id and s.owner_id = (select auth.uid())
));

create policy "owners manage transactions in their spaces"
on public.transactions for all to authenticated
using (exists (
  select 1 from public.finance_spaces s
  where s.id = transactions.space_id and s.owner_id = (select auth.uid())
))
with check (
  created_by = (select auth.uid())
  and exists (
    select 1 from public.finance_spaces s
    where s.id = transactions.space_id and s.owner_id = (select auth.uid())
  )
);

grant select, insert, update, delete on public.finance_spaces to authenticated;
grant select, insert, update, delete on public.accounts to authenticated;
grant select, insert, update, delete on public.categories to authenticated;
grant select, insert, update, delete on public.transactions to authenticated;

commit;
