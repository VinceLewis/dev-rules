# Go rules

Adds to `dev_rules.md` for Go 1.25 or later.

## Layout

- Start flat: `go.mod`, `main.go` and a few files in package `main`. Add `internal/<pkg>` only when a second binary or a clear boundary needs it.
- No `pkg/`, `util/`, `common/` or `models/` packages. Name packages after what they provide.
- Pin the toolchain with the `go` and `toolchain` lines in `go.mod`; declare developer tools with `tool` directives and run them with `go tool`.

## Tooling

- Format: `gofmt -l .` must print nothing (or `golangci-lint fmt` with `gofumpt` and `goimports`).
- Lint: `go vet ./...` and `golangci-lint run` (v2 config) with `errcheck`, `staticcheck`, `govet`, `ineffassign`, `unused`, `bodyclose`, `sqlclosecheck` and `rowserrcheck` enabled.
- Test: `go test -race -count=1 ./...`; table-driven tests with literal cases; `t.TempDir()` and `t.Context()` for isolation.
- Dependencies: commit `go.sum`; CI fails if `go mod tidy` changes anything. Run `govulncheck ./...`.

## Code

- Handle every error where it occurs; wrap with `fmt.Errorf("doing x: %w", err)` and test with `errors.Is` or `errors.As`. Never `_ =` an error without a comment.
- Panic only for programmer errors at start-up, never for input.
- Accept interfaces only where you have two implementations; return concrete types. Define an interface in the consuming package, with the fewest methods.
- Pass `context.Context` as the first parameter of anything that does I/O; never store it in a struct.
- Use the standard library first: `net/http` routing, `log/slog`, `encoding/json`, `flag`. Add a framework only with a named need.
- Every goroutine has an owner that waits for it (`sync.WaitGroup.Go` or `errgroup`) and a way to stop.

## Data access

- Use `database/sql` with `pgx/v5/stdlib`, or `pgx` directly for PostgreSQL; `modernc.org/sqlite` or `mattn/go-sqlite3` for SQLite; `go-mssqldb` for SQL Server.
- Write SQL by hand or generate typed code with `sqlc`. No ORM by default.
- Always `defer rows.Close()` and check `rows.Err()` after the loop.
- Transactions: `tx, err := db.BeginTx(ctx, nil)`, then `defer tx.Rollback()`, and `return tx.Commit()`; the deferred rollback is a no-op after commit.
- Migrations: plain SQL files applied by `goose` or `golang-migrate`, or embedded with `embed.FS` and a 30-line runner.

## Pitfalls

- Nil interface holding a nil pointer is not `nil`.
- `defer` inside a loop holds resources until the function returns.
- Unbuffered channel sends with no receiver leak goroutines.
- Unclosed `http.Response.Body`; default `http.Client` with no timeout.
- `float64` for money; use integer minor units or a decimal type.
- `time.Now()` compared across machines; store UTC.
- `init()` functions with side effects and package-level mutable state.
