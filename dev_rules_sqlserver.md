# SQL Server rules

Adds to `dev_rules.md` for T-SQL on SQL Server 2022 or 2025 and Azure SQL.

## Layout and migrations

- Every database object is created by a numbered migration (`dev_rules.md` section 9). There is no separate install script.
- Write procedures, views, functions and triggers with `CREATE OR ALTER`. After release, change one by adding a migration with its full new definition. Never add `proc-v2.sql` that alters `proc-v1.sql`.
- Separate batches with a line holding only `GO`. The runner splits each file on those lines and runs all its batches in the file's transaction. Use no other `sqlcmd` syntax (`:r`, `:setvar`, `$(var)`).
- No `sqlcmd`, SQL project (`Microsoft.Build.Sql`), DACPAC or `SqlPackage` in build or deployment; the `migrate` runner is the only path to a database.

## Tooling

- Lint and format check: `sqlfluff lint` in CI, with `dialect = tsql` and `max_line_length = 120` in `.sqlfluff` and the version pinned in the step (`pipx run --spec sqlfluff==4.5.0 sqlfluff lint`). Fix layout locally with `sqlfluff format`.
- Test from the host language with the Testcontainers SQL Server module, setting the image explicitly to `mcr.microsoft.com/mssql/server:2025-latest`; use `2022-latest` only when production runs SQL Server 2022.
- Test procedures by calling them from those tests. No tSQLt.
- Every test creates a uniquely named database and applies the migrations to it with the `migrate` runner.

## Transactions and errors

- Start every procedure that writes with `SET NOCOUNT, XACT_ABORT ON;`.
- Use `BEGIN TRY … BEGIN TRAN … COMMIT … END TRY BEGIN CATCH IF @@TRANCOUNT > 0 ROLLBACK; THROW; END CATCH`. Never swallow an error or use `RAISERROR` for new code.
- For upserts, use `UPDATE … WITH (UPDLOCK, SERIALIZABLE)` then `INSERT` if `@@ROWCOUNT = 0`. Never use `MERGE`: it has a long history of concurrency and correctness bugs.
- Use `OUTPUT` to capture changed rows and keys, not `SCOPE_IDENTITY()` loops or `@@IDENTITY`.
- Never use `NOLOCK` or `READ UNCOMMITTED`. The first migration, marked `-- no-transaction`, runs `ALTER DATABASE CURRENT SET READ_COMMITTED_SNAPSHOT ON;` (already on in Azure SQL).
- Use `sp_getapplock` for an application-level single-runner lock instead of a status table.

## Types and data

- Use `datetimeoffset(3)` in UTC for instants (default `SYSUTCDATETIME()`), `decimal(19,4)` for money and `date` for dates. Never `float` or `money` for amounts.
- Use `nvarchar` for human text and `varchar` for ASCII codes; match parameter types exactly to column types to avoid implicit conversions and scans.
- Declare `NOT NULL` by default, primary keys on every table, and foreign keys and check constraints for every rule the database can enforce.
- Declare identifier columns whose case matters with `COLLATE Latin1_General_100_BIN2`.

## Security

- Applications connect as a least-privilege login mapped to a database user. Never `sa` or `db_owner` in application code.
- Grant permissions only to database roles, one per duty the workflow has (read, write, approval), as `EXECUTE` on each object, granted in the migration that creates it; add each user to its role. Derive "who approved" from `ORIGINAL_LOGIN()`, never from a parameter.
- Dynamic SQL only through `sp_executesql` with parameters; quote identifiers with `QUOTENAME`, and check them against `sys.objects` or `sys.columns` first.
- Use `Encrypt=True` (the default in `Microsoft.Data.SqlClient`) and a trusted certificate; allow `TrustServerCertificate=True` only for Testcontainers databases.

## Pitfalls

- Missing `XACT_ABORT`, leaving open transactions after a client timeout.
- `GO` sent to the server: it is a client batch separator, not T-SQL; the runner must split on it.
- Scalar user-defined functions and cursors over large sets; prefer set-based statements.
- `SELECT *` in views and procedures; list columns.
- Parameter sniffing on skewed data; fix with the right index first, `OPTION (RECOMPILE)` second.
- Relying on `IDENTITY` values being gap-free or ordered by commit time.
- Service Broker, CLR, linked servers or SQL Agent jobs for work a single transaction can do.
