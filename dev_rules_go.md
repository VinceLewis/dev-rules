# Go rules

Adds to `dev_rules.md` for Go 1.27.

## Layout

- Start flat: `go.mod`, `main.go` and a few files in package `main`. Add `internal/<pkg>` only when a second binary needs the code or a package would exceed its size budget.
- No `pkg/`, `util/`, `common/` or `models/` packages. Name packages after what they provide.
- Pin the toolchain with the `go` and `toolchain` lines in `go.mod`. Declare `govulncheck` with a `tool` directive and run it with `go tool govulncheck`. Pin `golangci-lint` with `version:` in `golangci/golangci-lint-action`; never as a `tool` directive, which its maintainers do not support.

## Tooling

- Format: `gofmt`. CI fails unless `test -z "$(gofmt -l .)"`. `gofmt` does not wrap long lines; wrap them by hand, and the size gate enforces the width.
- Lint: `golangci-lint run` with a v2 `.golangci.yml` enabling `errcheck`, `staticcheck`, `govet`, `ineffassign`, `unused`, `bodyclose`, `sqlclosecheck` and `rowserrcheck`.
- Test against real dependencies; no SQL mocking library such as `go-sqlmock`, and no package-level function variables swapped by tests.
- Test: `go test -race -count=1 ./...`; table-driven tests with literal cases and named `t.Run` subtests; `t.TempDir()` and `t.Context()` for isolation. Assert with the standard `testing` package only; no `testify` or other assertion library. Run one case with `go test -run '^TestName$/^case$' ./<pkg>`.
- Parsers of untrusted input get a native `FuzzName` test with literal seeds from `f.Add`, which `go test` runs as ordinary cases. After writing or changing one, run `go test -run '^$' -fuzz '^FuzzName$' -fuzztime 30s ./<pkg>`; commit any failing input it writes under `testdata/fuzz/` as a regression case.
- Database tests start PostgreSQL and SQL Server with `testcontainers-go` (`modules/postgres`, `modules/mssql`): one container per test package, started in `TestMain`, which terminates it after `m.Run()`; each test gets its own database. SQLite tests open a file under `t.TempDir()`. Build the schema with the `migrate` runner.
- Dependencies: commit `go.sum`; CI runs `go mod tidy -diff` and `go tool govulncheck ./...`.

## Code

- Handle every error where it occurs; wrap with `fmt.Errorf("doing x: %w", err)`; match sentinel errors with `errors.Is` and error types with `errors.AsType`. Never `_ =` an error without a comment.
- Panic only for programmer errors at start-up, never for input.
- Accept interfaces only where you have two implementations; return concrete types. Define an interface in the consuming package, with the fewest methods.
- Pass `context.Context` as the first parameter of anything that does I/O; never store it in a struct.
- Use the standard library for logging (`log/slog`), JSON (`encoding/json`) and flags (`flag`). Log with `slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: level}))`, set once in `main`.
- Settings (`dev_rules.md` section 3): `main` reads the `--config` file into one `Config` struct with a `json.Decoder` using `DisallowUnknownFields`, rejects trailing data, and runs `Config.validate()`, which fails on every zero-valued field. Convert `_seconds` fields to `time.Duration` there. Never read settings or the environment in `init()` or below `main`. Route HTTP with `github.com/go-chi/chi/v5` and its `middleware` package over plain `net/http` handlers; no other web framework.
- HTTP servers: build `http.Server` with `ReadHeaderTimeout`, `ReadTimeout`, `WriteTimeout` and `IdleTimeout` from settings (start at 5s, 30s, 30s and 120s). Wrap every request body in `http.MaxBytesReader` (start at 1 MiB). Run until `signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)` fires, then `srv.Shutdown`.
- Use chi's `middleware.RequestID`, `middleware.RealIP` (behind the proxy only) and `middleware.Recoverer`; one logging middleware that logs method, route pattern (`chi.RouteContext(r.Context()).RoutePattern()`), status, duration and request ID.
- Decode every JSON body with one helper: the body limit, `DisallowUnknownFields`, rejection of trailing data, then validation of every enum and range before any query.
- Verify bearer JWTs locally with `github.com/golang-jwt/jwt/v5` (`dev_rules_web.md`), using `jwt.WithValidMethods`, `jwt.WithIssuer`, `jwt.WithAudience` and `jwt.WithExpirationRequired`.
- Make outbound requests with `http.NewRequestWithContext`, passing the request's context.
- Every goroutine has an owner that waits for it and a way to stop: `errgroup.WithContext` (`golang.org/x/sync/errgroup`) when any goroutine can return an error, `sync.WaitGroup.Go` otherwise.

## Data access

- Use `database/sql` with `github.com/jackc/pgx/v5/stdlib` for PostgreSQL (never the native `pgx` API); `modernc.org/sqlite` for SQLite; `github.com/microsoft/go-mssqldb` for SQL Server.
- Write SQL by hand and scan rows into structs. No ORM, no query builder and no code generator such as `sqlc`.
- Always `defer rows.Close()` and check `rows.Err()` after the loop.
- Transactions: `tx, err := db.BeginTx(ctx, nil)`, then `defer tx.Rollback()`, and `return tx.Commit()`; the deferred rollback is a no-op after commit.
- Migrations: embed `migrations/*.sql` with `//go:embed` into an `embed.FS` in package `main` at the repository root. The runner reads them with `fs.ReadDir` (sorted by name) and runs each file in one `ExecContext` call with no arguments. Dispatch `migrate` and other subcommands on `os.Args[1]`, each with its own `flag.NewFlagSet`.
- Money: `decimal.Decimal` from `github.com/shopspring/decimal` (`decimal.NullDecimal` for nullable columns), stored in PostgreSQL `numeric(19,4)` or SQL Server `decimal(19,4)`. Parse input with `decimal.NewFromString`.

## Pitfalls

- Nil interface holding a nil pointer is not `nil`.
- `defer` inside a loop holds resources until the function returns.
- Unbuffered channel sends with no receiver leak goroutines.
- Unclosed `http.Response.Body`; default `http.Client` with no timeout.
- `float64` or `decimal.NewFromFloat` for money.
- `time.Now()` compared across machines; store UTC.
- `init()` functions with side effects and package-level mutable state.
