# Docker Test Environment Setup and Troubleshooting

This document explains how the Docker test environment works and how to troubleshoot issues.

## Quick Start

On Windows with PowerShell:
```powershell
.\bin\run_tests.ps1
```

For a specific test:
```powershell
.\bin\run_tests.ps1 -TestFilter "anthias_app.tests.SplashPageViewTest.test_splash_page_uses_host_local_domain_when_no_ip_found"
```

For integration tests only:
```powershell
.\bin\run_tests.ps1 -Integration
```

## Architecture

The test environment uses Docker Compose with these services:

1. **redis** - Message broker and channel layer for Django Channels
2. **anthias-test** - Test runner container with Django and test dependencies

## Initial Setup (One-Time)

The first test run performs these steps automatically:

1. Builds `anthias-dockerfile-image-builder` Docker image with Python and `uv` package manager
2. Generates `docker/Dockerfile.test` and `docker/Dockerfile.redis` from Jinja2 templates
3. Builds the `anthias-test:dev` image for running tests
4. Creates Redis container for test database and message bus
5. Initializes test database and runs migrations

## Windows-Specific Issues and Solutions

### Problem: `.venv` permission errors during Docker build

**Symptom**: `error: failed to remove directory '/app/.venv': Input/output error (os error 5)`

**Cause**: Windows file system permissions conflict when Docker container tries to manage a Windows-local Python venv.

**Solution**: The `run_tests.ps1` script automatically removes `.venv` before building. This is correct - the venv should be inside Docker, not on Windows.

### Problem: Docker engine not running

**Symptom**: `Cannot connect to Docker daemon`

**Solution**:
1. Open Docker Desktop application
2. Wait for it to finish initializing (about 30 seconds)
3. Verify Docker is ready: `docker ps`
4. Retry the test command

### Problem: Build hangs or times out

**Symptom**: Test containers stuck at "Building" for > 10 minutes

**Solution**:
1. Kill hanging docker processes: `docker compose -f docker-compose.test.yml down`
2. Remove stale volumes: `docker volume prune -f`
3. Retry with: `.\bin\run_tests.ps1`

### Problem: Tests fail with database locked errors

**Symptom**: `sqlite3.OperationalError: database is locked`

**Solution**:
1. The test database is in `/tmp/anthias-test.db` inside the container
2. If a previous test crashed, the lock file persists
3. Solution: `docker compose -f docker-compose.test.yml down` then retry

## Manual Test Execution

If you need to run tests manually:

```powershell
# Start containers
docker compose -f docker-compose.test.yml up -d --build

# Wait for containers to be ready (5-10 seconds)
Start-Sleep -Seconds 5

# Prepare environment
docker compose -f docker-compose.test.yml exec -T anthias-test bash ./bin/prepare_test_environment.sh -s

# Run specific test
docker compose -f docker-compose.test.yml exec -T anthias-test ./manage.py test anthias_app.tests.SplashPageViewTest.test_splash_page_uses_host_local_domain_when_no_ip_found

# Or run all non-integration tests
docker compose -f docker-compose.test.yml exec -T anthias-test ./manage.py test --exclude-tag=integration

# Clean up
docker compose -f docker-compose.test.yml down
```

## Debugging Tests

### View test container logs

```powershell
docker compose -f docker-compose.test.yml logs anthias-test --tail 50
```

### Run with verbose output

```powershell
docker compose -f docker-compose.test.yml exec -T anthias-test ./manage.py test -v 2 --exclude-tag=integration
```

### Enter test container shell

```powershell
docker compose -f docker-compose.test.yml exec anthias-test bash
```

Then you can run `./manage.py test` directly with any options.

## Environment Variables

The test environment uses these key settings:

- `ENVIRONMENT=development` - Dev mode configuration
- `DEBUG=True` - Django debug mode
- `DATABASE_URL=sqlite:////tmp/anthias-test.db` - Test database location
- `REDIS_URL=redis://anthias-redis:6379/0` - Redis broker

## Performance Tips

1. **First build is slow** (~5-10 minutes): Docker downloads all Python packages and builds the image
2. **Subsequent builds are fast**: Docker caches layers, so rebuilds take <1 minute
3. **Test execution**: First test run initializes database (~10-20 seconds), subsequent runs are <5 seconds
4. **Reuse containers**: Don't `docker compose down` between test runs unless you need a clean database

## CI/CD Integration

The GitHub Actions workflow uses the same test environment. See `.github/workflows/test.yml` for details.
