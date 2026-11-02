# SQLite rules

Adds to `dev_rules.md` for embedded SQLite 3.51.3 or later.

## When to use it

- Use SQLite for single-host applications, tools, local state and tests of SQLite-backed code. Choose PostgreSQL when several hosts write, or you need roles and network access.
- Never use SQLite as a stand-in for another engine in tests; its types, locking and SQL dialect differ.
- Do not put a database file on a network file system.

## Connection settings

Set these on every connection, in one place, straight after opening and before any transaction:

- `PRAGMA foreign_keys = ON;` (off by default, per connection; the `migrate` runner is the one exception, below).
- `PRAGMA journal_mode = WAL;` for concurrent readers with one writer.
- `PRAGMA busy_timeout = 5000;` so writers wait instead of failing with `SQLITE_BUSY`.
- `PRAGMA synchronous = FULL;` so every commit survives power loss.

At start-up, fail if `select sqlite_version()` is below 3.51.3: earlier versions have the WAL-reset bug, which can lose data.

## Schema and migrations

- Declare tables `STRICT` so column types are enforced; add `NOT NULL`, primary keys, foreign keys and `CHECK` constraints.
- Use `INTEGER PRIMARY KEY` for row IDs. Add `AUTOINCREMENT` only to a table whose rows are deleted while their IDs are held outside the database (URLs, files, other systems), so a deleted ID is never handed out again.
- Store instants as `TEXT` in UTC with a fixed format, `YYYY-MM-DDTHH:MM:SS.SSSZ`, so text order is time order; in SQL, `strftime('%Y-%m-%dT%H:%M:%fZ', 'now')`. Store booleans as `INTEGER` `0`/`1` with a `CHECK`.
- Money: SQLite has no exact decimal type, so store amounts as `INTEGER` ten-thousandths (scale 4, matching the language's decimal at scale 4 and `numeric(19,4)`): `12.3400` is stored as `123400`. Never `REAL` and never decimal text, which `sum()` turns into `REAL` and which sorts as text. Read and write money columns only through one pair of data-access functions that multiply or divide by 10000 exactly and reject values with more than 4 decimal places or outside the 64-bit range. In SQL, only add, subtract, compare and `sum()` amounts (integer `sum()` stays exact and fails on overflow); never `avg()` or `total()`, which return `REAL`.
- Create `schema_migrations` as a `STRICT` table with `version INTEGER PRIMARY KEY` and `applied_at TEXT NOT NULL` (the instant format above). Never use `PRAGMA user_version`; it holds no `applied_at` and differs from the other engines' runners.
- The `migrate` runner opens its connection with `PRAGMA foreign_keys = OFF`, runs each file and its version row inside `BEGIN IMMEDIATE`, and runs `PRAGMA foreign_key_check` before `COMMIT`, rolling back if it returns any row. SQLite DDL is transactional; only `VACUUM` needs `-- no-transaction`.
- For changes `ALTER TABLE` cannot make, follow the documented rebuild in one migration: create the new table, copy, drop the old one, rename the new one, recreate its indexes, triggers and views.

## Transactions

- Wrap every multi-statement write in a transaction; start writers with `BEGIN IMMEDIATE` so lock conflicts surface at the start, not at commit.
- Keep write transactions short; there is one writer at a time.
- Upsert with `INSERT … ON CONFLICT (key) DO UPDATE`; use `RETURNING` to read changed rows.
- Make the driver issue `BEGIN IMMEDIATE`, never an implicit `BEGIN`. Python's `sqlite3`: connect with `autocommit=True` and execute `BEGIN IMMEDIATE` and `COMMIT` yourself; with `autocommit=False` a transaction is always open, so the connection pragmas above do nothing.

## Testing

- Each test creates its database file in its own temporary directory with the same runner as `migrate`, from the real migrations.
- In the migration test, assert that `PRAGMA integrity_check` returns `ok` and `PRAGMA foreign_key_check` returns no rows.

## Pitfalls

- Type affinity in non-`STRICT` tables silently stores text in integer columns.
- `LIKE` is case-insensitive for ASCII only; `=` uses binary collation unless declared `COLLATE NOCASE`.
- Copying the file while it is open; back up with `VACUUM INTO 'path'`.
- Leaving `-wal` and `-shm` files behind when moving a WAL database; checkpoint first.
- Sharing one connection across threads without the driver's thread-safety guarantees.
- Expecting the file to shrink after deletes; freed pages are reused. Run `VACUUM` (a `-- no-transaction` migration) only when `PRAGMA freelist_count` shows a measured need; never set `auto_vacuum` and never schedule `VACUUM`.
