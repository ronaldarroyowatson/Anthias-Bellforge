# run-ts-tests Skill

Run Anthias TypeScript/React unit tests with bun.

## Usage

Tell the agent: "Run the frontend tests" or "Run TypeScript tests for the asset store".

## Steps

### Option A — Local (bun installed on host)

```bash
bun install
bun test
```

### Option B — Inside dev Docker container

```bash
docker compose -f docker-compose.dev.yml exec anthias-server \
  bun install --frozen-lockfile

docker compose -f docker-compose.dev.yml exec anthias-server \
  bun test
```

### Option C — Inside test Docker container (CI path)

```bash
docker compose -f docker-compose.test.yml exec anthias-test \
  bun install --frozen-lockfile

docker compose -f docker-compose.test.yml exec anthias-test \
  bun test
```

## Test Location

Tests live in `static/src/tests/`. The bun test runner is configured in `bunfig.toml`:
- Preload: `static/src/setupTests.ts`
- Root: `static/src`
- DOM: happy-dom via `@happy-dom/global-registrator`
- Mocking: MSW (Mock Service Worker) for API calls

## Notes

- No `jest.config` — bun's built-in test runner is used directly.
- Test files follow the `*.test.ts` / `*.test.tsx` naming convention.
