# .NET and C# rules

Adds to `dev_rules.md` for C# on .NET. Current baseline: .NET 10 LTS, C# 14.

## Layout

- Start with one product project and one test project: `src/<App>/`, `tests/<App>.Tests/`, one `<App>.slnx`.
- Pin the SDK in `global.json` with `rollForward: latestFeature`.
- Put shared settings in one `Directory.Build.props`: `Nullable` enable, `ImplicitUsings` enable, `TreatWarningsAsErrors` true, `AnalysisLevel` `latest-recommended`, `InvariantGlobalization` true unless you need cultures.
- Use top-level statements in `Program.cs` for a console app. No `Startup` class, generic host or dependency-injection container unless you need hosted services or ASP.NET Core.
- Use `internal` by default; expose `InternalsVisibleTo` to the test project instead of making types public.

## Tooling

- Format: `dotnet format --verify-no-changes` in CI, driven by `.editorconfig`.
- Lint: built-in Roslyn analysers at `latest-recommended`; add a third-party analyser only for a named rule you need.
- Test: xUnit v3 (or MSTest) on Microsoft.Testing.Platform, run with `dotnet test`.
- Dependencies: Central Package Management (`Directory.Packages.props`), `RestorePackagesWithLockFile` true, and `dotnet restore --locked-mode` in CI.
- Audit: `NuGetAudit` enabled with `NuGetAuditMode` `all`; treat `NU1903`/`NU1904` as errors.
- Build: `dotnet build -warnaserror` in CI.

## Code

- Use records for data, `static` methods for pure logic and plain classes otherwise. No interface for a single implementation; mock at the process boundary or use the real thing.
- Return results or throw; do not do both for the same failure. Throw specific exceptions only at the boundary where they are handled; catch `Exception` only at the top level to log and set the exit code.
- Use `async`/`await` all the way down when you do I/O; pass `CancellationToken`. Never `.Result`, `.Wait()` or `async void` (except event handlers).
- Dispose with `using` declarations. Never hold a connection open across user interaction.
- Parse and format with `CultureInfo.InvariantCulture`; use `decimal` for money and `DateTimeOffset.UtcNow` or `TimeProvider` for time.
- Read configuration from the command line and environment directly; add `Microsoft.Extensions.Configuration` only when there are several sources to merge.
- Use `System.Text.Json` with source generation for fixed shapes. Do not add a JSON Schema library to validate a file you can check in 30 lines.

## Data access

- Default to plain ADO.NET with `Microsoft.Data.SqlClient` (or `Npgsql`, `Microsoft.Data.Sqlite`). Add Dapper when mapping code repeats; add EF Core only for a large, entity-shaped domain.
- Always use typed parameters: set `SqlDbType`, size, precision and scale. Never `AddWithValue`; it infers `nvarchar` and causes implicit conversions.
- Transactions: open the connection, `BeginTransaction`, pass the transaction to every command, `Commit`, and let `Dispose` roll back on failure. Avoid `TransactionScope` unless you truly span resources.
- Migrations: idempotent SQL scripts run in order by a small runner, or EF Core migration bundles if you use EF Core. Never both.

## Testing

- Use Testcontainers for .NET, or a CI service container, for real database tests; create a fresh database per test class or test.
- Use `[Theory]` with inline literal data for boundaries; one assertion idea per test.
- No mocking framework by default. Hand-write a fake only when the real dependency is unavailable in tests.

## Pitfalls

- `DateTime.Now`, `double` for money, and culture-sensitive `ToString()`/`Parse()`.
- `HttpClient` created per request; create one and reuse it, or use `IHttpClientFactory` inside ASP.NET Core.
- `string.Equals` without `StringComparison`; use `Ordinal` for identifiers.
- Suppressing nullable warnings with `!`; fix the flow instead.
- Reflection, `dynamic` and source-less code generation in a small app.
- Extra projects created per layer (`.Core`, `.Domain`, `.Contracts`, `.Infrastructure`) before any second consumer.
