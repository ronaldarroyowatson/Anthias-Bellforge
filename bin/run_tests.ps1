# PowerShell wrapper for running Anthias tests in Docker
# This script handles Windows-specific Docker setup issues
# Usage: .\bin\run_tests.ps1 [-TestFilter "test_name"] [-Integration]

param(
    [string]$TestFilter = "",
    [switch]$Integration = $false
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

Push-Location $RepoRoot

try {
    Write-Host "Setting up Docker test environment..." -ForegroundColor Cyan

    # Clean up any problematic venv on Windows
    if (Test-Path .\.venv) {
        Write-Host "Cleaning up .venv directory..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .\.venv | Out-Null
    }

    # Build dockerfile generator if needed
    Write-Host "Checking for Dockerfile.test..." -ForegroundColor Cyan
    if (-not (Test-Path docker/Dockerfile.test)) {
        Write-Host "Generating test Dockerfiles..." -ForegroundColor Cyan

        # Build the generator image
        docker build --pull -f docker/Dockerfile.dev -t anthias-dockerfile-image-builder . | Out-Null

        # Run generator in container with separate venv volume
        docker run --rm `
            -v "${PWD}:/app" `
            -v "anthias-builder-venv:/app/.venv" `
            -w /app `
            anthias-dockerfile-image-builder `
            uv run python -m tools.image_builder --environment=development --dockerfiles-only --disable-cache-mounts | Out-Null
    }

    Write-Host "Starting test containers..." -ForegroundColor Cyan
    docker compose -f docker-compose.test.yml down 2>$null
    docker compose -f docker-compose.test.yml up -d --build 2>&1 | Out-Null

    Write-Host "Waiting for containers to be ready..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5

    # Prepare test environment
    Write-Host "Preparing test environment..." -ForegroundColor Cyan
    docker compose -f docker-compose.test.yml exec -T anthias-test bash ./bin/prepare_test_environment.sh -s 2>&1 | Out-Null

    # Run tests
    $TestArgs = @()
    if ($TestFilter) {
        $TestArgs += $TestFilter
    } else {
        $TestArgs += "--exclude-tag=integration"
    }

    if ($Integration) {
        $TestArgs = @("--tag=integration")
    }

    Write-Host "Running tests..." -ForegroundColor Cyan
    docker compose -f docker-compose.test.yml exec -T anthias-test ./manage.py test $TestArgs

    Write-Host "Test execution completed!" -ForegroundColor Green

} finally {
    Pop-Location
}
