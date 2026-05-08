# Makefile for common Docker operations on Windows
# Run these commands from the project root directory
# Example: `make docker-test` or `make docker-clean`

.PHONY: docker-test docker-build docker-down docker-clean docker-rebuild help

help:
	@echo "Anthias Docker Commands:"
	@echo "  make docker-test         - Run tests in Docker (recommended)"
	@echo "  make docker-build        - Build test images"
	@echo "  make docker-down         - Stop and remove containers"
	@echo "  make docker-clean        - Remove containers, volumes, and images"
	@echo "  make docker-rebuild      - Clean and rebuild everything"
	@echo "  make docker-logs         - View test container logs"
	@echo "  make docker-shell        - Enter test container shell"

docker-test: docker-build
	@echo "Running tests..."
	docker compose -f docker-compose.test.yml exec -T anthias-test ./manage.py test --exclude-tag=integration
	@echo "Tests complete!"

docker-build:
	@echo "Building test environment..."
	@if not exist docker\Dockerfile.test (
		@echo "Generating Dockerfiles..."
		docker build --pull -f docker/Dockerfile.dev -t anthias-dockerfile-image-builder . > nul 2>&1
		docker run --rm -v "${PWD}:/app" -v "anthias-builder-venv:/app/.venv" -w /app anthias-dockerfile-image-builder uv run python -m tools.image_builder --environment=development --dockerfiles-only --disable-cache-mounts > nul 2>&1
	)
	docker compose -f docker-compose.test.yml up -d --build

docker-down:
	docker compose -f docker-compose.test.yml down

docker-clean: docker-down
	@echo "Removing Docker images and volumes..."
	docker compose -f docker-compose.test.yml rm -f
	docker volume rm anthias-builder-venv 2>/dev/null || true
	docker images | findstr anthias | awk '{print $$3}' | xargs docker rmi -f 2>/dev/null || true

docker-rebuild: docker-clean docker-build

docker-logs:
	docker compose -f docker-compose.test.yml logs -f anthias-test

docker-shell: docker-build
	docker compose -f docker-compose.test.yml exec anthias-test bash

# Advanced targets

docker-test-verbose: docker-build
	docker compose -f docker-compose.test.yml exec -T anthias-test ./manage.py test -v 2 --exclude-tag=integration

docker-test-single:
	@echo "Usage: make docker-test-single TEST=anthias_app.tests.SplashPageViewTest.test_splash_page_uses_host_local_domain_when_no_ip_found"
	docker compose -f docker-compose.test.yml exec -T anthias-test ./manage.py test $(TEST)

docker-coverage: docker-build
	docker compose -f docker-compose.test.yml exec -T anthias-test coverage run --source='.' manage.py test --exclude-tag=integration
	docker compose -f docker-compose.test.yml exec -T anthias-test coverage report
