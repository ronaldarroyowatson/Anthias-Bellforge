# ruff-fix Skill

Run ruff linting and formatting on Bellforge Python source files.

## Usage

Tell the agent: "Fix Python linting errors" or "Format all Python files with ruff".

## Steps

1. Set up the dev-host virtual environment (first time only):
   ```bash
   uv venv
   uv pip install --group dev-host
   ```

2. Check for lint errors:
   ```bash
   uv run ruff check .
   ```

3. Auto-fix lint errors:
   ```bash
   uv run ruff check . --fix
   ```

4. Format all Python files:
   ```bash
   uv run ruff format .
   ```

5. Verify no remaining issues:
   ```bash
   uv run ruff check .
   ```

## Config

`ruff.toml` in the repo root:
- `line-length = 79`
- `quote-style = "single"`
- `target-version = "py313"`
- Excluded: `anthias_app/migrations/*.py`

## Notes

- ruff replaces flake8, isort, and black in this project.
- Never run ruff on auto-generated migration files.
