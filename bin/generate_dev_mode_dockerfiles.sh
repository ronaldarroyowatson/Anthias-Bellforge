#!/bin/bash

set -euo pipefail

BUILDER_DOCKERFILE='docker/Dockerfile.dev'
BUILDER_IMAGE_NAME='anthias-dockerfile-image-builder'
BUILDER_CONTAINER_NAME="${BUILDER_IMAGE_NAME}-instance"
detect_build_target() {
    local machine
    machine="$(uname -m 2>/dev/null || true)"

    # Keep the historical x86 default for developer machines, but
    # auto-select Raspberry Pi targets so viewer artifacts match hardware.
    if [[ "${machine}" == "aarch64" || "${machine}" == "arm64" ]]; then
        local model
        model="$(tr -d '\0' </proc/device-tree/model 2>/dev/null || true)"
        if [[ "${model}" == *"Raspberry Pi 5"* ]]; then
            echo "pi5"
            return
        fi
        echo "pi4-64"
        return
    fi

    echo "x86"
}

BUILD_TARGET="${BUILD_TARGET:-$(detect_build_target)}"
ENVIRONMENT="${ENVIRONMENT:-development}"

docker build \
    --pull \
    -f "$BUILDER_DOCKERFILE" \
    -t "$BUILDER_IMAGE_NAME" .

docker rm -f "$BUILDER_CONTAINER_NAME" || true
docker run \
    --rm \
    --name="$BUILDER_CONTAINER_NAME" \
    -v "$(pwd):/app" \
    -e PYTHONPATH=/app \
    "$BUILDER_IMAGE_NAME" \
    python3 -m tools.image_builder \
        --environment="$ENVIRONMENT" \
        --dockerfiles-only \
        --disable-cache-mounts \
        --build-target="$BUILD_TARGET"
