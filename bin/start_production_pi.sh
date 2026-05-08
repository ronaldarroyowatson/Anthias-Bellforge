#!/bin/bash
set -e

cd ~/Anthias-Bellforge

export DOCKER_TAG="latest"
export DEVICE_TYPE="pi5"
export MY_IP="192.168.2.180"
export MAC_ADDRESS=""
export USER="pi"
TOTAL_KB=3887864
export VIEWER_MEMORY_LIMIT_KB=$(( TOTAL_KB * 8 / 10 ))
export SHM_SIZE_KB=$(( TOTAL_KB * 3 / 10 ))

echo "==> Substituting template..."
envsubst < docker-compose.yml.tmpl > /tmp/docker-compose.prod.yml

echo "==> Removing /dev/vchiq entries (Pi5 does not need them)..."
sed -i '/- "\/dev\/vchiq:\/dev\/vchiq"/d' /tmp/docker-compose.prod.yml
sed -i '/- \/dev\/vchiq:\/dev\/vchiq/d' /tmp/docker-compose.prod.yml

echo "==> Fixing staticfiles path..."
sed -i 's|/home/pi/anthias/staticfiles|/home/pi/Anthias-Bellforge/staticfiles|g' /tmp/docker-compose.prod.yml

echo "==> Creating required host directories..."
mkdir -p ~/.anthias ~/anthias_assets ~/Anthias-Bellforge/staticfiles

echo "==> Generated compose file:"
cat /tmp/docker-compose.prod.yml

echo "==> Stopping dev stack if running..."
docker compose -f ~/Anthias-Bellforge/docker-compose.dev.yml down 2>/dev/null || true

echo "==> Building production stack (this will take a while)..."
docker compose -f /tmp/docker-compose.prod.yml build

echo "==> Starting production stack..."
docker compose -f /tmp/docker-compose.prod.yml up -d

echo "==> Done!"
docker compose -f /tmp/docker-compose.prod.yml ps
