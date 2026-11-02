# TypeScript rules

Adds to `dev_rules.md` for TypeScript on Node.js 24 LTS or later (and the browser).

## Layout

- One package by default: `package.json`, `tsconfig.json`, `src/`, `test/`. Use workspaces only for a second deployable.
- ES modules only (`"type": "module"`). No barrel `index.ts` files that re-export everything.
- Pin Node in `.nvmrc` or `engines`, and the package manager with the `packageManager` field.

## Tooling

- Package manager: pnpm; commit `pnpm-lock.yaml`; CI runs `pnpm install --frozen-lockfile`. Set `minimumReleaseAge` to delay brand-new releases.
- Type check: `tsc --noEmit` with `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `verbatimModuleSyntax` and `erasableSyntaxOnly`. Adopt the native TypeScript 7 compiler (`tsgo`) when your tools support it.
- Format and lint: either Biome v2 (`biome ci`) alone, or Prettier plus ESLint flat config with `typescript-eslint` `strictTypeChecked`. Pick one set, not both.
- Test: Vitest (`vitest run`); Playwright only for real browser flows.
- Run scripts directly with Node's built-in type stripping (`node src/main.ts`) for tools and servers; bundle only for the browser (Vite).
- Audit: `pnpm audit --prod` in CI; review every new dependency's install scripts (pnpm blocks them by default).

## Code

- No `any`; use `unknown` and narrow. No non-null `!` without a comment saying why it is safe.
- Validate external data (HTTP, files, environment) at the boundary with one schema library (Zod or Valibot) and derive the type from it. Do not hand-write a type and a validator for the same shape.
- No `enum` or `namespace`; use union string literals and modules.
- Await every promise or return it; enable `no-floating-promises`. Wrap top-level work so a rejection sets a non-zero exit code.
- Throw `Error` objects with a `cause`; catch only where you can handle or add context.
- Prefer plain functions and object literals to classes; no dependency-injection framework.

## Data access

- Use the driver directly (`pg` or `postgres` for PostgreSQL, `node:sqlite` or `better-sqlite3` for SQLite, `mssql` for SQL Server) with parameterised queries.
- Add a typed query builder (Kysely) or Drizzle only when hand-written query types repeat. No heavyweight ORM by default.
- Transactions: one helper that takes a callback, runs `BEGIN`, `COMMIT` and `ROLLBACK` on a single checked-out client, and releases it in `finally`.
- Migrations: plain SQL files run by the chosen library's migrator or `node-pg-migrate`.

## Pitfalls

- `number` for money or 64-bit IDs; use integer minor units, `bigint` or a decimal string.
- `Date` parsing of non-ISO strings and local-time arithmetic; store and send ISO 8601 UTC.
- `==`, truthiness checks on `0` and `""`, and `||` where `??` is meant.
- Mixed CommonJS and ESM; `__dirname` in ESM (use `import.meta.dirname`).
- `JSON.parse` results used without validation.
- Hundreds of transitive dependencies for trivial helpers; check the lock file diff in review.
