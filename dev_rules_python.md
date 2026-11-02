# Python rules

Adds to `dev_rules.md` for Python 3.14.

## Layout

- A project uses `pyproject.toml`, `src/<package>/` and `tests/`. One package until a second deployable exists.
- Pin the interpreter: `3.14` in `.python-version` and `requires-python = ">=3.14"` in `pyproject.toml`.
- A single script with third-party dependencies stays one file with PEP 723 inline metadata (`# /// script`, including `requires-python`) and runs with `uv run script.py`.
- A standard-library-only script, such as `scripts/size_gate.py`, has no PEP 723 block and no dependencies, and runs with the system `python3` (3.14 on `ubuntu-latest`), not `uv`.

## Tooling

- Environments and dependencies: `uv`. Dev tools (ruff, the type checker, pytest, hypothesis, testcontainers, pip-audit) go in `[dependency-groups] dev`; run them with `uv run`. Commit `uv.lock`; CI runs `uv sync --locked`. No `requirements.txt`.
- Format: `ruff format --check`, with `line-length = 120` under `[tool.ruff]` in `pyproject.toml` to match the size gate.
- Lint: `ruff check` with `[tool.ruff.lint] select = ["E", "F", "B", "I", "UP", "SIM", "S", "PTH"]` and `per-file-ignores = { "tests/**" = ["S101"] }`.
- Types: `mypy --strict` on `src/` (not pyright, basedpyright or ty); type hints on every public function.
- Test: `pytest` with `tmp_path` and fixtures for isolation; `pytest.mark.parametrize` with literal cases. Run one test with `uv run pytest tests/test_<module>.py::test_<name>`.
- Property tests use Hypothesis `@given` with its default settings.
- Database tests: `testcontainers`, one container per test session from a fixture in `tests/conftest.py`; PostgreSQL via `PostgresContainer("postgres:18", driver=None)`, whose URL `psycopg` accepts. Build the schema by calling the `migrate` code, never a separate schema file.
- Audit in CI: `uv export --frozen --no-emit-project --format requirements-txt | uv run pip-audit --disable-pip -r /dev/stdin`.

## Code

- Use the standard library first: `pathlib`, `argparse`, `json`, `csv`, `dataclasses`, `logging`, `subprocess`, `sqlite3`, `decimal`, `zoneinfo`.
- Validate all external input (HTTP, files, environment) at the boundary with Pydantic v2 models and use the model as the type; never hand-write a parser and a type for the same shape. Use `dataclasses` (`frozen=True, slots=True`) for internal data.
- No classes for code that is just functions. `abc.ABC` subclasses and `typing.Protocol` classes count as interfaces (`dev_rules.md` section 2).
- Catch specific exceptions; never bare `except:` or `except Exception: pass`. Re-raise with `raise … from err`.
- Read settings (`dev_rules.md` section 3) from the `--config` file into one Pydantic model with `model_config = ConfigDict(extra="forbid", frozen=True)` and no field defaults, and secrets from `os.environ`, at the entry point; pass them down. No global settings objects. Each command, including `migrate`, is an `argparse` subcommand.
- Call `subprocess.run([...], check=True)` with a list, never `shell=True` with interpolated strings.
- Open files with an explicit `encoding="utf-8"` and `newline=""` for CSV.

## Data access

- Use the driver directly: `psycopg[binary]` (psycopg 3) for PostgreSQL, `sqlite3` for SQLite, `mssql-python` for SQL Server. No SQLAlchemy, no ORM, no query builder. Always use parameter placeholders; compose PostgreSQL identifiers only with `psycopg.sql`.
- Transactions, one block per unit of work: psycopg connects with `autocommit=True` and uses `with conn.transaction():`; sqlite3 connects with `autocommit=True` and executes `BEGIN IMMEDIATE` … `COMMIT` itself, rolling back on error (`dev_rules_sqlite.md`); mssql-python uses `with mssql_python.connect(...) as conn:` (commits on success, rolls back on error, closes).
- Migrations: exactly `dev_rules.md` section 9, no Alembic or other tool. The runner sends each file's whole text in one call: `conn.execute(text)` (psycopg), `conn.executescript(text)` (sqlite3), `cursor.execute(text)` (mssql-python).

## Pitfalls

- Mutable default arguments (`def f(x=[])`).
- `float` for money; use `decimal.Decimal` built from strings, stored as `numeric(19,4)` (PostgreSQL) or `decimal(19,4)` (SQL Server).
- Naive `datetime`; always `datetime.now(UTC)` and `zoneinfo`.
- `import *`, circular imports and module-level side effects.
- Installing into the system interpreter; always use the project environment.
- Running untrusted downloaded scripts without `-I` (isolated mode).
- `pickle` or `eval` on any external data.
