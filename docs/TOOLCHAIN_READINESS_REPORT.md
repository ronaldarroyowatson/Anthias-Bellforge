# Anthias-Bellforge Toolchain Readiness Report

> Generated: 2026-05-01
> Auditor: GitHub Copilot (Claude Sonnet 4.6)

---

## Verification Summary

### Config File Paths

| File | Key References | Status |
|---|---|---|
| `.vscode/settings.json` | `ruff.toml`, `pyproject.toml`, `eslint.config.mjs`, `node_modules/typescript/lib` | All resolved to correct repo-root paths |
| `.vscode/launch.json` | `manage.py`, `DJANGO_SETTINGS_MODULE=anthias_django.settings` | Both exist and match repo structure |
| `.vscode/mcp.json` | `${workspaceFolder}` filesystem path, GHCR/Redis/Playwright | Correct; GITHUB_TOKEN, REDIS_URL env var referenced |
| `.vscode/extensions.json` | 28 extension IDs | All valid VS Code marketplace IDs |
| `.devcontainer/devcontainer.json` | `python:3.13-bookworm`, features, port forwards | Ports 8000/6379/5555 match docker-compose.dev.yml |
| `.env.example` | All env vars consumed across all services | Complete, `.env` already git-ignored |
| `docs/TOOLCHAIN_BLUEPRINT.md` | Comprehensive A–K toolchain guide | Created |
| `docs/MANUAL_TOOLCHAIN_ACTIONS.md` | 6 manual auth actions | Created |
| `.gitignore` | Added `static/dist/` and `.venv/` | Fixed — these were missing |

---

### MCP Server Declarations

| Server | Config Location | Auth Required | Ready |
|---|---|---|---|
| `github` | `.vscode/mcp.json` | Yes — `GITHUB_TOKEN` | After Action 1 |
| `filesystem` | `.vscode/mcp.json` | No | Immediately |
| `redis` | `.vscode/mcp.json` | No (local) | After Redis started |
| `playwright` | `.vscode/mcp.json` | No | After `npm install` |

---

### Agent Skills Status

| Skill | Path | Status |
|---|---|---|
| `commit` | `.claude/skills/commit/SKILL.md` | Pre-existing |
| `create-pr` | `.claude/skills/create-pr/SKILL.md` | Pre-existing |
| `docker-rebuild` | `.claude/skills/docker-rebuild/SKILL.md` | **New** |
| `run-python-tests` | `.claude/skills/run-python-tests/SKILL.md` | **New** |
| `run-ts-tests` | `.claude/skills/run-ts-tests/SKILL.md` | **New** |
| `ruff-fix` | `.claude/skills/ruff-fix/SKILL.md` | **New** |
| `openapi-regen` | `.claude/skills/openapi-regen/SKILL.md` | **New** |
| `bun-build` | `.claude/skills/bun-build/SKILL.md` | **New** |

---

### Language Server Coverage

| Language | Files Covered | Server | Status |
|---|---|---|---|
| Python 3.13 | `anthias_app/`, `api/`, `lib/`, `viewer/`, `tests/`, `tools/`, `celery_tasks.py`, `manage.py`, `settings.py` | Pylance + mypy | Extensions configured in `.vscode/settings.json` |
| TypeScript/TSX | `static/src/**/*.{ts,tsx}` | tsserver (bundled) | `tsconfig.json` already present |
| C++ (Qt5/Qt6) | `webview/src/**/*.{cpp,h}` | clangd / ms-vscode.cpptools | Extension in `extensions.json` |
| YAML | `.github/workflows/`, `ansible/`, `docker-compose*.yml`, `balena.yml` | redhat YAML LS | Schema associations in `settings.json` |
| Jinja2 | `docker/*.j2` | wholroyd.jinja | File association in `settings.json` |
| SCSS/Sass | `static/sass/**/*.scss` | Sass extension | File association configured |
| Django HTML | `templates/**/*.html` | batisteo.vscode-django | File association configured |
| TOML | `pyproject.toml`, `ruff.toml`, `bunfig.toml` | even-better-toml | Extension in `extensions.json` |

---

### Linter / Formatter Consistency Check

| Tool | Target | Config | Command | Consistent |
|---|---|---|---|---|
| ruff (lint) | Python | `ruff.toml` → line=79, py313, single-quotes | `uv run ruff check .` | Yes |
| ruff (format) | Python | `ruff.toml` | `uv run ruff format .` | Yes |
| mypy | Python | `pyproject.toml` [tool.mypy] | `uv run mypy .` | Yes |
| ansible-lint | Ansible | Default rules | `uv run ansible-lint ansible/` | Yes |
| ESLint 10 | TypeScript/TSX | `eslint.config.mjs` | `bun run lint:check` | Yes |
| Prettier 3.8 | TypeScript/TSX/SCSS | default | `bun run format:check` | Yes |
| bun test | `static/src/tests/**` | `bunfig.toml` | `bun test` | Yes |
| Django test | `tests/`, `anthias_app/tests.py` | `manage.py` | `./manage.py test` | Yes |

---

### Dev Container Coherence

- Base image: `mcr.microsoft.com/devcontainers/python:3.13-bookworm` — matches `requires-python = ">=3.13"` in `pyproject.toml`
- Docker-in-Docker feature: enables running compose test stacks from inside the container
- Ports 8000, 6379, 5555 forwarded — match `docker-compose.dev.yml` (8000→8080), Redis (6379), Flower (5555)
- `postCreateCommand` installs `dev-host` uv group (ruff, mypy, ansible-lint, type stubs) and bun packages
- Extensions list in devcontainer mirrors `.vscode/extensions.json` for consistency

---

## New Files Created

```
.vscode/
├── extensions.json       — 28 recommended extensions
├── settings.json         — Python/TS/YAML/Django formatters, mypy, ruff, test config
├── launch.json           — Django server, Celery worker, test, viewer debug configs
└── mcp.json              — GitHub, Filesystem, Redis, Playwright MCP servers

.devcontainer/
└── devcontainer.json     — Python 3.13, Docker-in-Docker, Node, Bun, uv 0.9.17

.claude/skills/
├── docker-rebuild/SKILL.md
├── run-python-tests/SKILL.md
├── run-ts-tests/SKILL.md
├── ruff-fix/SKILL.md
├── openapi-regen/SKILL.md
└── bun-build/SKILL.md

docs/
├── TOOLCHAIN_BLUEPRINT.md       — Full A–K toolchain reference
├── MANUAL_TOOLCHAIN_ACTIONS.md  — 6 manual auth actions with steps
└── http/api-v2.http             — REST Client examples for v2 API

.env.example                     — All environment variables with instructions
.gitignore (updated)             — Added static/dist/ and .venv/
```

---

## Items Completed Without User Intervention

- All VS Code configuration files created and wired
- Dev container scaffolded
- MCP server config created (auth-free servers ready immediately)
- 6 new agent skills created
- REST API `.http` example file created
- `.env.example` template with all variables documented
- `.gitignore` patched with missing entries
- Full toolchain blueprint written to `docs/TOOLCHAIN_BLUEPRINT.md`

---

## Manual Actions Required (Work Through One at a Time)

See [docs/MANUAL_TOOLCHAIN_ACTIONS.md](MANUAL_TOOLCHAIN_ACTIONS.md) for full instructions on each item below.

| Priority | Action | Blocks |
|---|---|---|
| 1 | **GitHub PAT** — create token at github.com/settings/tokens, set `GITHUB_TOKEN` in `.env` | GitHub MCP server, update detection, CI image push |
| 2 | **GitHub Copilot subscription** — activate at github.com/features/copilot | All agent capabilities |
| 3 | **GA4 telemetry decision** — disable upstream Screenly telemetry or replace with your own GA4 property | Data privacy / COPPA compliance for school use |
| 4 | **Docker Hub login** — run `docker login` to avoid pull rate limits | Docker builds |
| 5 | **Balena login** — run `balena login` for fleet OTA deployment | Fleet deployment |
| 6 | **Start Redis locally** — `docker compose -f docker-compose.dev.yml up -d redis` | Redis MCP, local dev |
