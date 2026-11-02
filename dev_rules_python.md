# Python rules

Adds to `dev_rules.md` for Python 3.13 or later.

## Layout

- A single script stays a single file with PEP 723 inline metadata (`# /// script`) and runs with `uv run script.py`.
- A project uses `pyproject.toml`, `src/<package>/` and `tests/`. One package until a second deployable exists.
- Pin the interpreter in `.python-version` and `requires-python`.

## Tooling

- Environments and dependencies: `uv`; commit `uv.lock`; CI runs `uv sync --locked`. No `requirements.txt` alongside it.
- Format: `ruff format --check`.
- Lint: `ruff check` with at least rule sets `E`, `F`, `B`, `I`, `UP`, `SIM`, `S` and `PTH`.
- Types: `mypy --strict` or `pyright` in strict mode on `src/`; type hints on every public function.
- Test: `pytest` with `tmp_path` and fixtures for isolation; `pytest.mark.parametrize` with literal cases.
- Audit: `pip-audit` (run with `uvx pip-audit`) in CI.
- A standard-library-only tool (like the size gate) has no dependencies at all.

## Code

- Use the standard library first: `pathlib`, `argparse`, `json`, `csv`, `dataclasses`, `logging`, `subprocess`, `sqlite3`, `decimal`, `zoneinfo`.
- Use `dataclasses` (with `frozen=True, slots=True`) for data; reach for Pydantic only to validate untrusted structured input.
- No classes for code that is just functions; no abstract base classes with one subclass; `typing.Protocol` only for two real implementations.
- Catch specific exceptions; never bare `except:` or `except Exception: pass`. Re-raise with `raise … from err`.
- Read configuration from `argparse` and `os.environ` at the entry point and pass it down; no global settings objects.
- Call `subprocess.run([...], check=True)` with a list, never `shell=True` with interpolated strings.
- Open files with an explicit `encoding="utf-8"` and `newline=""` for CSV.

## Data access

- Use the driver directly: `psycopg` 3 for PostgreSQL, `sqlite3` for SQLite, `pyodbc` or `mssql-python` for SQL Server. Always use parameter placeholders.
- Add SQLAlchemy Core when you need to compose queries; the ORM only for a large, entity-shaped domain.
- Transactions: `with conn.transaction():` (psycopg) or `with conn:` (sqlite3) around the unit of work.
- Migrations: plain SQL files with a small runner, or Alembic if you use SQLAlchemy.

## Pitfalls

- Mutable default arguments (`def f(x=[])`).
- `float` for money; use `Decimal` built from strings.
- Naive `datetime`; always `datetime.now(UTC)` and `zoneinfo`.
- `import *`, circular imports and module-level side effects.
- Installing into the system interpreter; always use the project environment.
- Running untrusted downloaded scripts without `-I` (isolated mode).
- `pickle` or `eval` on any external data.
