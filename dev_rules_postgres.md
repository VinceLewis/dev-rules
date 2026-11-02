# PostgreSQL rules

Adds to `dev_rules.md` for PostgreSQL 18.

## Migrations

- Follow `dev_rules.md` section 9. PostgreSQL DDL is transactional, so every file runs in the runner's transaction unless its first line is `-- no-transaction`.
- Put each `CREATE INDEX CONCURRENTLY`, `DROP INDEX CONCURRENTLY` or `REINDEX CONCURRENTLY` alone in its own `-- no-transaction` file: PostgreSQL runs a multi-statement string as one implicit transaction, which these statements reject. If one fails, drop the `INVALID` index it leaves before rerunning. Use `CONCURRENTLY` only on tables that exist in a released database.
- Lint `migrations/*.sql` with `squawk` in the CI lint step to catch locking and rewrite hazards. Keep `.squawk.toml` in the repository root with `pg_version = "18.0"` and `assume_in_transaction = true`; the second line of every `-- no-transaction` file is `-- squawk-disable-assume-in-transaction`.
- Lint and format-check SQL with `sqlfluff lint` in CI, with `dialect = postgres` and `max_line_length = 120` in `.sqlfluff` and the version pinned in the step (`pipx run --spec sqlfluff==4.5.0 sqlfluff lint`). Fix layout locally with `sqlfluff format`.

## Testing

- Start the server with Testcontainers for the host language and the `postgres:18` image, one container per test run.
- Apply migrations once per run with the `migrate` runner into a template database, close its connections, then give each test its own database with `CREATE DATABASE <test_db> TEMPLATE <template_db>`.
- Test functions, triggers and constraints from the host-language tests. Do not use pgTAP.

## Types

- Use `bigint GENERATED ALWAYS AS IDENTITY` for surrogate keys, not `serial`. Use `uuid DEFAULT uuidv7()` instead only when the key is created outside the database or appears in a URL or API.
- Use `timestamptz` for instants, `date` for dates, `numeric(19,4)` for money (never `money`, `real` or `double precision`), and `text` with a `CHECK` for length instead of `varchar(n)`.
- Use `text` with a `CHECK (col IN (...))` for a fixed list of values, never an enum type, whose values cannot be removed. Use `ON DELETE SET NULL` only on nullable columns. Give ordered child rows `UNIQUE (parent_id, position)`, `DEFERRABLE INITIALLY DEFERRED` when reordering swaps positions.
- Declare `NOT NULL`, primary keys, foreign keys and `CHECK` constraints for every rule the database can enforce. Index every foreign key you join or delete on.
- Use `jsonb` only for genuinely schemaless data, never to avoid designing columns.

## Transactions and concurrency

- Upsert with `INSERT … ON CONFLICT (key) DO UPDATE`. Never use `MERGE`: it raises a unique violation when another session inserts the same key concurrently.
- Use `RETURNING` instead of re-selecting changed rows.
- Under `SERIALIZABLE` or `REPEATABLE READ`, retry the whole transaction on SQLSTATE `40001` and `40P01`, with a limit.
- Use `SELECT … FOR UPDATE SKIP LOCKED` for a work queue table before adding a message broker; `pg_advisory_xact_lock` for single-runner jobs.
- The `migrate` runner sets `lock_timeout = '5s'` on its session and no `statement_timeout`, so long backfills and concurrent index builds are not killed. Set `idle_in_transaction_session_timeout` on the server.

## Security

- Applications connect as a role without `SUPERUSER`, `CREATEDB` or ownership of the schema; grant only the privileges they use, normally `SELECT, INSERT, UPDATE, DELETE`, and set the same with `ALTER DEFAULT PRIVILEGES FOR ROLE <owner>` in the first migration so new tables are covered.
- Keep `CREATE` on schema `public` revoked from `PUBLIC` (the default since 15) and set `search_path` explicitly in `SECURITY DEFINER` functions.
- Build dynamic identifiers with `format('%I', name)`, never by concatenation.
- Require TLS (`sslmode=verify-full`) outside local containers.

## Pitfalls

- `ALTER TABLE` that rewrites or takes an `ACCESS EXCLUSIVE` lock on a large table in one step; add nullable columns, backfill in batches, then add the constraint `NOT VALID` and `VALIDATE` it.
- Long-running or idle transactions that block vacuum.
- PgBouncer in transaction mode: set `max_prepared_statements` (1.21+) and never rely on session state (`SET`, session advisory locks, `LISTEN`).
- `NULL` in unique columns: use `UNIQUE NULLS NOT DISTINCT` if `NULL` must be unique.
- `timestamp` without time zone for instants; `now()` is the transaction start time, not the wall clock.
- `OFFSET` pagination on large tables; use keyset pagination.
