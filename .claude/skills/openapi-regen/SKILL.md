# openapi-regen Skill

Regenerate the OpenAPI schema from the DRF Spectacular configuration.

## Usage

Tell the agent: "Regenerate the OpenAPI schema" or "Update the API docs schema".

## Steps

1. Start the dev stack if not already running:
   ```bash
   docker compose -f docker-compose.dev.yml up -d
   ```

2. Generate the schema:
   ```bash
   docker compose -f docker-compose.dev.yml exec anthias-server \
     python manage.py spectacular --color --file schema.yml
   ```

3. The schema is output to `schema.yml` in the repo root.

4. Commit the updated schema if it changed:
   ```bash
   git add schema.yml
   git commit -m "chore: regenerate OpenAPI schema"
   ```

## API Versions

The REST API has four versions:
- `GET /api/v1/`
- `GET /api/v1.1/`
- `GET /api/v1.2/`
- `GET /api/v2/` ← primary, uses DRF + drf-spectacular

The OpenAPI schema covers v2. For testing all endpoints, use `humao.rest-client` with `.http` files in `docs/http/`.

## Notes

- The schema is also regenerated automatically by the GitHub Actions workflow `.github/workflows/generate-openapi-schema.yml` on every push to `master`.
