# SQL Server rules

Adds to `dev_rules.md` for T-SQL on SQL Server 2022 or 2025 and Azure SQL.

## Layout

- Keep the schema in as few files as possible: one install script per database (`database/<db>.sql`), idempotent and re-runnable. Split only at the file-size limit.
- Change objects in place with `CREATE OR ALTER`. Never add `proc-v2.sql` that alters `proc-v1.sql`.
- Use numbered forward-only migration scripts (`0001_create_x.sql`) only once a released database must be upgraded in place; until then, edit the install script.
- Run scripts with `go-sqlcmd` (`sqlcmd -b -V 11`) so any error stops the run with a non-zero exit code.
- Consider an SDK-style SQL project (`Microsoft.Build.Sql`) and `SqlPackage` only when you deploy DACPACs to several environments.

## Tooling

- Lint: SQLFluff with the `tsql` dialect in CI; format with `sqlfluff fix` or keep a consistent hand style.
- Test: drive tests from the host language against a real SQL Server container (`mcr.microsoft.com/mssql/server:2025-latest`). Use tSQLt only when logic lives mainly in procedures.
- Every test creates a uniquely named database and drops it afterwards; check for leftovers at the end of the run.

## Transactions and errors

- Start every procedure that writes with `SET NOCOUNT, XACT_ABORT ON;`.
- Use `BEGIN TRY … BEGIN TRAN … COMMIT … END TRY BEGIN CATCH IF @@TRANCOUNT > 0 ROLLBACK; THROW; END CATCH`. Never swallow an error or use `RAISERROR` for new code.
- Write the data change and its audit or receipt row in the same transaction.
- For upserts, use `UPDATE … WITH (UPDLOCK, SERIALIZABLE)` then `INSERT` if `@@ROWCOUNT = 0`. Avoid `MERGE`: it has a long history of concurrency and correctness bugs.
- Use `OUTPUT` to capture changed rows and keys, not `SCOPE_IDENTITY()` loops or `@@IDENTITY`.
- Never use `NOLOCK` or `READ UNCOMMITTED`. Enable `READ_COMMITTED_SNAPSHOT` if readers block writers.
- Use `sp_getapplock` for an application-level single-runner lock instead of a status table.

## Types and data

- Use `datetime2(3)` or `datetimeoffset` for time, `decimal(p,s)` for money, `date` for dates. Never `float` or `money` for amounts.
- Use `nvarchar` for human text and `varchar` for ASCII codes; match parameter types exactly to column types to avoid implicit conversions and scans.
- Declare `NOT NULL` by default, primary keys on every table, and foreign keys and check constraints for every rule the database can enforce.
- Compare identifiers with an explicit binary or known collation when case matters.

## Security

- Applications connect as a least-privilege login mapped to a user granted `EXECUTE` on a schema or specific objects. Never `sa` or `db_owner` in application code.
- Separate logins or roles for read, write, approval and administration when the workflow has those roles; derive "who approved" from `ORIGINAL_LOGIN()` or `SUSER_SNAME()`, not from a parameter.
- Dynamic SQL only through `sp_executesql` with parameters; quote identifiers with `QUOTENAME`, and check them against `sys.objects` or `sys.columns` first.
- Use `Encrypt=True` (the default in `Microsoft.Data.SqlClient`) and a trusted certificate; allow `TrustServerCertificate=True` only for local containers.

## Pitfalls

- Missing `XACT_ABORT`, leaving open transactions after a client timeout.
- `GO` inside a script run by ADO.NET: it is a `sqlcmd` separator, not T-SQL.
- Scalar user-defined functions and cursors over large sets; prefer set-based statements.
- `SELECT *` in views and procedures; list columns.
- Parameter sniffing on skewed data; fix with the right index first, `OPTION (RECOMPILE)` second.
- Relying on `IDENTITY` values being gap-free or ordered by commit time.
- Service Broker, CLR, linked servers or SQL Agent jobs for work a single transaction can do.
