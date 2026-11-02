# PostgreSQL rules

Adds to `dev_rules.md` for PostgreSQL 17 or 18.

## Layout and migrations

- Before the first release, keep one idempotent schema file and edit it in place. After release, use numbered forward-only migrations (`0001_…sql`); never edit an applied one.
- Run each migration in a transaction (PostgreSQL DDL is transactional), except `CREATE INDEX CONCURRENTLY`, which must run alone outside a transaction.
- Use one tool: the host language's (`goose`, `Alembic`, `node-pg-migrate`, EF Core) or plain `psql -v ON_ERROR_STOP=1 -1 -f`.
- Lint migrations with `squawk` in CI to catch locking and rewrite hazards; lint style with SQLFluff (`postgres` dialect) if you want one.

## Testing

- Test against a real server in a container (`postgres:18`), one fresh database per test run, created from `template0` or a migrated template database.
- Use pgTAP only when logic lives mainly in functions; otherwise test from the host language.

## Types

- Use `bigint GENERATED ALWAYS AS IDENTITY` for surrogate keys, not `serial`. Use `uuidv7()` (18+) where you need globally unique keys.
- Use `timestamptz` for instants, `date` for dates, `numeric(p,s)` for money, `text` with a `CHECK` for length instead of `varchar(n)`.
- Declare `NOT NULL`, primary keys, foreign keys and `CHECK` constraints for every rule the database can enforce. Index every foreign key you join or delete on.
- Use `jsonb` only for genuinely schemaless data, never to avoid designing columns.

## Transactions and concurrency

- Keep the data change and its audit row in one transaction.
- Upsert with `INSERT … ON CONFLICT (key) DO UPDATE`; use `MERGE … RETURNING` (17+) when you need per-row actions.
- Use `RETURNING` instead of re-selecting changed rows.
- Under `SERIALIZABLE` or `REPEATABLE READ`, retry the whole transaction on SQLSTATE `40001` and `40P01`, with a limit.
- Use `SELECT … FOR UPDATE SKIP LOCKED` for a work queue table before adding a message broker; `pg_advisory_xact_lock` for single-runner jobs.
- Set `lock_timeout` and `statement_timeout` in migrations and `idle_in_transaction_session_timeout` on the server.

## Security

- Applications connect as a role without `SUPERUSER`, `CREATEDB` or ownership of the schema; grant only the needed privileges. The owner role runs migrations.
- Keep `CREATE` on schema `public` revoked from `PUBLIC` (the default since 15) and set `search_path` explicitly in `SECURITY DEFINER` functions.
- Parameterise every query; build dynamic identifiers with `format('%I', name)`.
- Require TLS (`sslmode=verify-full`) outside local containers.

## Pitfalls

- `ALTER TABLE` that rewrites or takes an `ACCESS EXCLUSIVE` lock on a large table in one step; add nullable columns, backfill in batches, then add the constraint `NOT VALID` and `VALIDATE` it.
- Long-running or idle transactions that block vacuum.
- Prepared statements through a transaction-mode pooler; check your driver and PgBouncer settings.
- `NULL` in unique columns: use `UNIQUE NULLS NOT DISTINCT` if `NULL` must be unique.
- `timestamp` without time zone for instants; `now()` is the transaction start time, not the wall clock.
- `OFFSET` pagination on large tables; use keyset pagination.
