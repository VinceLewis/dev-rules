# .NET and C# rules

Adds to `dev_rules.md` for C# on .NET. Current baseline: .NET 10 LTS, C# 14.

## Layout

- Start with one product project and one test project: `src/<App>/`, `tests/<App>.Tests/`, one `<App>.slnx`.
- Pin the SDK in `global.json` with `rollForward: latestFeature` and `"test": { "runner": "Microsoft.Testing.Platform" }`. CI installs it with `actions/setup-dotnet` and `global-json-file: global.json`.
- Put shared settings in one `Directory.Build.props`: `Nullable` enable, `ImplicitUsings` enable, `TreatWarningsAsErrors` true, `AnalysisLevel` `latest-recommended`, `InvariantGlobalization` true; set it false only when the product formats text in the user's culture.
- Use top-level statements in `Program.cs` for a console app. No `Startup` class, generic host or dependency-injection container unless you need hosted services or ASP.NET Core.
- Use `internal` by default; expose internals to the test project with an `<InternalsVisibleTo Include="<App>.Tests" />` item instead of making types public.

## Tooling

- Format: `dotnet format --verify-no-changes` in CI, driven by `.editorconfig` with `max_line_length = 120`. `dotnet format` does not wrap long lines; wrap them by hand, and the size gate enforces the width.
- Lint: the built-in Roslyn analysers at `latest-recommended`, run by `dotnet build`. No third-party analyser packages.
- Test: xUnit v3 (`xunit.v3`) on Microsoft.Testing.Platform, run with `dotnet test`. Assert with xUnit's `Assert`; no assertion library.
- Dependencies: Central Package Management (`Directory.Packages.props`), `RestorePackagesWithLockFile` true, and `dotnet restore --locked-mode` in CI.
- Audit: `NuGetAudit` enabled with `NuGetAuditMode` `all` and `NuGetAuditLevel` `high`; treat `NU1903`/`NU1904` as errors.
- Build: `dotnet build -warnaserror` in CI.

## Code

- Use records for data, `static` methods for pure logic and plain classes otherwise.
- Throw for failures. Use the `bool TryX(..., out T value)` pattern only where callers routinely expect failure, such as parsing input; no result types. Throw specific exceptions only at the boundary where they are handled; catch `Exception` only at the top level to log and set the exit code.
- Use `async`/`await` all the way down when you do I/O; pass `CancellationToken`. Never `.Result`, `.Wait()` or `async void` (except event handlers).
- Dispose with `using` declarations. Never hold a connection open across user interaction.
- Parse and format with `CultureInfo.InvariantCulture`; use `decimal` for money. Read the time from `DateTimeOffset.UtcNow`; take a `TimeProvider` only where a test must control the clock.
- Read settings (`dev_rules.md` section 3) from the `--config` file with `System.Text.Json` into one `sealed record` whose properties are all `required`, with `UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow`, and validate it at start-up. Read secrets with `Environment.GetEnvironmentVariable`. Parse `args` by hand in `Program.cs`; no `System.CommandLine`. No `appsettings*.json` files and no added `Microsoft.Extensions.Configuration` sources.
- Use `System.Text.Json` with source generation for fixed shapes. Do not add a JSON Schema library to validate a file you can check in 30 lines.

## Data access

- Use plain ADO.NET with the engine's driver: `Microsoft.Data.SqlClient` for SQL Server, `Npgsql` for PostgreSQL, `Microsoft.Data.Sqlite` for SQLite. No Dapper and no EF Core; map each reader row to a record by hand.
- Always use typed parameters: set the provider type (`SqlDbType`, `NpgsqlDbType`, `SqliteType`), size, precision and scale; money is `Decimal` with precision 19 and scale 4 on SQL Server and PostgreSQL. Never `AddWithValue`; it infers `nvarchar` and causes implicit conversions.
- Transactions: open the connection, `BeginTransaction`, pass the transaction to every command, `Commit`, and let `Dispose` roll back on failure. Never use `TransactionScope`.
- Migrations follow `dev_rules.md` section 9: `Program.cs` dispatches `<App> migrate` from `args` to a runner that applies `migrations/*.sql`, embedded with `<EmbeddedResource Include="../../migrations/*.sql" />`, in ordinal file-name order with ADO.NET. No EF Core migrations, DbUp or FluentMigrator.

## Testing

- Use Testcontainers for .NET (`Testcontainers.MsSql`, `Testcontainers.PostgreSql`) for real database tests, one container per test assembly through an xUnit v3 `AssemblyFixture`; create a fresh database per test and build its schema with the product's migration runner.
- Use `[Theory]` with `[InlineData]` literals for cases that differ only in data; one assertion idea per test. Run one test with `dotnet test --filter-method "*TestName"`.
- Property tests use `CsCheck` inside an xUnit `[Fact]`: `Gen.<type>.Sample(value => ...)`. No FsCheck.
- No mocking framework. Hand-write a fake only when the real dependency is unusable in tests.

## Pitfalls

- `DateTime.Now`, `double` for money, and culture-sensitive `ToString()`/`Parse()`.
- `HttpClient` created per request; create one per app with `new SocketsHttpHandler { PooledConnectionLifetime = TimeSpan.FromMinutes(2) }` and reuse it. No `IHttpClientFactory`.
- `string.Equals` without `StringComparison`; use `Ordinal` for identifiers.
- Suppressing nullable warnings with `!`; fix the flow instead.
- Reflection, `dynamic` and source-less code generation in a small app.
- Extra projects created per layer (`.Core`, `.Domain`, `.Contracts`, `.Infrastructure`) before any second consumer.
