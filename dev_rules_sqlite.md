# SQLite rules

Adds to `dev_rules.md` for embedded SQLite 3.45 or later.

## When to use it

- Use SQLite for single-host applications, tools, local state and tests of SQLite-backed code. Choose a server database when several hosts write, or you need roles and network access.
- Never use SQLite as a stand-in for another engine in tests; its types, locking and SQL dialect differ.
- Do not put a database file on a network file system.

## Connection settings

Set these on every connection, in one place, straight after opening:

- `PRAGMA foreign_keys = ON;` (off by default, per connection).
- `PRAGMA journal_mode = WAL;` for concurrent readers with one writer.
- `PRAGMA busy_timeout = 5000;` so writers wait instead of failing with `SQLITE_BUSY`.
- `PRAGMA synchronous = NORMAL;` with WAL, or `FULL` when every commit must survive power loss.

## Schema and migrations

- Declare tables `STRICT` so column types are enforced; add `NOT NULL`, primary keys, foreign keys and `CHECK` constraints.
- Use `INTEGER PRIMARY KEY` for row IDs; add `AUTOINCREMENT` only if IDs must never be reused.
- Store money as integer minor units, instants as ISO 8601 UTC text or Unix integers, and booleans as `0`/`1` with a `CHECK`.
- Track the schema version in `PRAGMA user_version`; apply numbered SQL migrations in a transaction and bump the version in the same transaction.
- For changes `ALTER TABLE` cannot make, follow the documented rebuild: create the new table, copy, drop, rename, then run `PRAGMA foreign_key_check`.

## Transactions

- Wrap every multi-statement write in a transaction; start writers with `BEGIN IMMEDIATE` so lock conflicts surface at the start, not at commit.
- Keep write transactions short; there is one writer at a time.
- Upsert with `INSERT … ON CONFLICT (key) DO UPDATE`; use `RETURNING` to read changed rows.
- Know your driver's transaction mode: Python's `sqlite3` needs `autocommit=False` (3.12+) or explicit `BEGIN`; others autocommit each statement.

## Testing

- Give each test its own file under a temporary directory (or `:memory:` when you do not test locking or WAL), created from the real migrations.
- Run `PRAGMA integrity_check` and `PRAGMA foreign_key_check` in the migration test.

## Pitfalls

- Type affinity in non-`STRICT` tables silently stores text in integer columns.
- `LIKE` is case-insensitive for ASCII only; `=` uses binary collation unless declared `COLLATE NOCASE`.
- Copying the file while it is open; back up with `VACUUM INTO` or the online backup API.
- Leaving `-wal` and `-shm` files behind when moving a WAL database; checkpoint first.
- Sharing one connection across threads without the driver's thread-safety guarantees.
- Unbounded growth after deletes; schedule `VACUUM` or set `auto_vacuum` before creating tables.
