# Personal Finance Workbench

A private, single-owner finance workbench built with Next.js, TypeScript, Supabase Auth, and PostgreSQL. It is not a SaaS or multi-tenant commercial product.

## Current foundation

- Separate `personal` and `office` finance spaces.
- PostgreSQL uses `numeric(20,2)` for money, not binary floating point.
- Row Level Security (RLS) checks ownership in PostgreSQL.
- Server-side domain operations call `requireUser()`; middleware is not the authorization boundary.
- Domain logic lives in `src/modules/`; reusable infrastructure primitives live in `src/lib/`.
- ESLint architecture rules allow modules to import lib, but forbid lib from importing modules.
- Transactions must reference an account/category from the same finance space (database composite foreign keys).

## Prerequisites

- Node.js 20 or later
- A Supabase project

## Configure

1. Copy `.env.example` to `.env.local`.
2. Fill in the Supabase project URL and publishable/anon key.
3. In Supabase SQL Editor, run `supabase/migrations/0001_workbench_foundation.sql`.
4. In Supabase Authentication, create the one owner account manually. Disable public sign-ups for this private app.
5. Create one `finance_spaces` row for each kind (`personal` and `office`) using the authenticated owner's UUID. The unique constraint prevents duplicate spaces of the same kind.
6. Install dependencies and start the app:

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Quality gates

```bash
npm run typecheck
npm run lint
npm test
npm run build
``

These commands must be run in this directory. They have **not** been claimed as passing by repository setup alone.

## Architecture rules

- `src/lib/**`: clients and low-level primitives only. No domain decisions.
- `src/modules/**`: domain schemas and use cases; may import `src/lib/**`.
- `src/lib/**` must never import `src/modules/**`; ESLint enforces the boundary.
- Pages/actions are composition roots and must invoke server-side domain functions/guards.
- Never expose a Supabase service-role key to browser code. User operations use the session-bound client and RLS.

## Important limitations of this initial scaffold

This is a foundation, not a production-ready accounting system. There is no transaction UI yet, no transfer double-entry flow, no bank reconciliation, and no financial reports. The SQL migration and app still need to be applied/run against a real Supabase project and verified with tests. Do not enter sensitive financial records until those checks pass.
