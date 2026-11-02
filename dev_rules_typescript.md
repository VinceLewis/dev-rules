# TypeScript rules

Adds to `dev_rules.md` for TypeScript 7 on Node.js 26 LTS or later (and the browser).

## Layout

- One package by default: `package.json`, `tsconfig.json`, `src/`, `test/`. Use pnpm workspaces only for a second deployable.
- ES modules only (`"type": "module"`). No barrel `index.ts` files that re-export everything.
- Pin the exact Node version in `.nvmrc` and the pnpm version in the `packageManager` field. CI reads them with `actions/setup-node` (`node-version-file: .nvmrc`) and `pnpm/action-setup`.

## Tooling

- Package manager: pnpm 11; commit `pnpm-lock.yaml`; CI runs `pnpm install --frozen-lockfile`. Keep the default `minimumReleaseAge` (one day); never lower it.
- Type check: `tsc --noEmit` from the `typescript` package with `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `verbatimModuleSyntax`, `erasableSyntaxOnly` and `allowImportingTsExtensions`.
- Format and lint: Biome v2 alone, configured in `biome.json` with the recommended rules; CI runs `biome ci`. No Prettier or ESLint until `typescript-eslint` supports TypeScript 7; then move linting to ESLint flat config with `typescript-eslint` `strictTypeChecked` and keep Biome as the formatter only.
- Test: Vitest (`vitest run`); `it.each` with literal cases for cases that differ only in data; run one test with `pnpm vitest run test/<file>.test.ts -t "<name>"`. Property tests use `fast-check` (`fc.assert(fc.property(...))`). A web UI gets one Playwright test per user flow, and Playwright is used for nothing else. Database tests start their server with `@testcontainers/postgresql` or `@testcontainers/mssqlserver`.
- Run tools and servers directly with Node's built-in type stripping (`node src/main.ts`); write relative imports with the `.ts` extension. Bundle only browser code, with Vite.
- Audit: `pnpm audit --prod --audit-level high` in CI. Review every new dependency's install scripts; pnpm blocks them unless the package is listed in `allowBuilds` in `pnpm-workspace.yaml`.

## Code

- No `any`; use `unknown` and narrow. No non-null `!` without a comment saying why it is safe.
- Validate external data (HTTP, files, environment) at the boundary with Zod and derive the type with `z.infer`. Do not hand-write a type and a validator for the same shape.
- No `enum` or `namespace`; use union string literals and modules.
- Await every promise or return it; enable Biome's `noFloatingPromises` and `noMisusedPromises`. Use top-level `await` in `src/main.ts` so a rejection exits non-zero; never swallow it.
- Throw `Error` objects with a `cause`; catch only where you can handle or add context.
- Prefer plain functions and object literals to classes; no dependency-injection framework.
- HTTP servers use Hono with `@hono/node-server`, validating requests with Zod through `@hono/zod-validator`. No Express, Fastify or other framework.
- Money is a `bigint` count of ten-thousandths, matching `numeric(19,4)` and `decimal(19,4)`. Convert it to and from a decimal string only at the data-access boundary; round explicitly when dividing.

## Data access

- Use the driver directly with parameterised queries: `pg` for PostgreSQL, `node:sqlite` for SQLite, `mssql` for SQL Server.
- Add Kysely as a typed query builder only when hand-written query result types repeat. No ORM.
- Transactions: one helper that takes a callback, runs `BEGIN`, `COMMIT` and `ROLLBACK` on a single checked-out client, and releases it in `finally`.
- Migrations: the `dev_rules.md` section 9 runner, using only `node:fs` and the driver, run as `node src/main.ts migrate`. No `node-pg-migrate` or library migrator.

## Pitfalls

- `number` for money or 64-bit IDs; keep 64-bit keys as the `string` that `pg` and `mssql` return.
- `mssql` passes `decimal` through a lossy `number` both ways: select money as `CAST(x AS varchar(24))`, and send it as `sql.VarChar` cast to `decimal(19,4)` in the SQL.
- `Date` parsing of non-ISO strings and local-time arithmetic; store and send ISO 8601 UTC.
- `==`, truthiness checks on `0` and `""`, and `||` where `??` is meant.
- Mixed CommonJS and ESM; `__dirname` in ESM (use `import.meta.dirname`).
- `JSON.parse` results used without validation.
- Hundreds of transitive dependencies for trivial helpers; check the lock file diff in review.
