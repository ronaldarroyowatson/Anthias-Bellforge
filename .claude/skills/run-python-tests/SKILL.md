# run-python-tests Skill

Run Anthias Python unit or integration tests inside Docker.

## Usage

Tell the agent: "Run the Python tests" or "Run integration tests for the API".

## Steps

1. Generate Dockerfiles (if not already done):
   ```bash
   uv run python -m tools.image_builder \
     --dockerfiles-only \
     --disable-cache-mounts \
     --service redis \
     --service test
   ```

2. Start test containers:
   ```bash
   docker compose -f docker-compose.test.yml up -d --build
   ```

3. Prepare the test environment:
   ```bash
   docker compose -f docker-compose.test.yml exec anthias-test \
     bash ./bin/prepare_test_environment.sh -s
   ```

4. Run tests (choose one):
   ```bash
   # Unit tests only (no external services required)
   docker compose -f docker-compose.test.yml exec anthias-test \
     ./manage.py test --exclude-tag=integration -v 2

   # Integration tests only
   docker compose -f docker-compose.test.yml exec anthias-test \
     ./manage.py test --tag=integration -v 2
   ```

5. Stop containers when done:
   ```bash
   docker compose -f docker-compose.test.yml down
   ```

## Notes

- Integration and non-integration tests **must** be run in separate invocations.
- Python version in CI: 3.13.
