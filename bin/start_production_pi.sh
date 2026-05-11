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

# Keep generated compose file in project dir so Docker resolves build contexts correctly
COMPOSE_FILE="$HOME/Anthias-Bellforge/docker-compose.prod.yml"

echo "==> Substituting template..."
envsubst < docker-compose.yml.tmpl > "$COMPOSE_FILE"

echo "==> Removing /dev/vchiq entries (Pi5 does not need them)..."
sed -i '/- "\/dev\/vchiq:\/dev\/vchiq"/d' "$COMPOSE_FILE"
sed -i '/- \/dev\/vchiq:\/dev\/vchiq/d' "$COMPOSE_FILE"
# Remove bare 'devices:' keys left after all entries are stripped (invalid compose syntax)
python3 - <<'PYEOF'
import re, pathlib, os
p = pathlib.Path(os.path.expanduser('~/Anthias-Bellforge/docker-compose.prod.yml'))
text = p.read_text()
# Remove a 'devices:' line that is immediately followed by another key or end-of-block
text = re.sub(r'    devices:\n(?=    [a-z]|\n)', '', text)
p.write_text(text)
PYEOF

echo "==> Fixing staticfiles path..."
sed -i 's|/home/pi/anthias/staticfiles|/home/pi/Anthias-Bellforge/staticfiles|g' "$COMPOSE_FILE"

echo "==> Creating required host directories..."
mkdir -p ~/.anthias ~/anthias_assets ~/Anthias-Bellforge/staticfiles

echo "==> Generated compose file:"
cat "$COMPOSE_FILE"

echo "==> Stopping dev stack if running..."
docker compose -f ~/Anthias-Bellforge/docker-compose.dev.yml down 2>/dev/null || true

echo "==> Building production stack (this will take a while)..."
docker compose -f "$COMPOSE_FILE" build

echo "==> Starting production stack..."
docker compose -f "$COMPOSE_FILE" up -d

echo "==> Done!"
docker compose -f /tmp/docker-compose.prod.yml ps
