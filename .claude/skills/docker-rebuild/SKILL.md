# docker-rebuild Skill

Rebuild one or more Bellforge Docker services and tail their logs.

## Usage

Tell the agent: "Rebuild the anthias-server container" or "Restart celery worker".

## Steps

1. Identify the service name(s): `anthias-server`, `anthias-celery`, `anthias-viewer`, `redis`.
2. Run:
   ```bash
   docker compose -f docker-compose.dev.yml up -d --build <service>
   ```
3. Tail logs:
   ```bash
   docker compose -f docker-compose.dev.yml logs -f <service>
   ```
4. If an error is found in logs, surface it and suggest a fix.

## Notes

- `anthias-celery` shares the `anthias-server:dev` image — rebuilding `anthias-server` also updates the celery worker image.
- Always use `docker-compose.dev.yml` in development unless the user specifies a different compose file.
