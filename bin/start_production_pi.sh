#!/bin/bash
set -e

cd ~/Anthias-Bellforge

export DOCKER_TAG="latest"
export DEVICE_TYPE="pi5"
# Resolve the current LAN IP on every boot so splash/setup URLs stay valid.
MY_IP_DETECTED="$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')"
if [ -z "$MY_IP_DETECTED" ]; then
	MY_IP_DETECTED="$(hostname -I | awk '{print $1}')"
fi
if [ -z "$MY_IP_DETECTED" ]; then
	echo "ERROR: Unable to determine host IP for MY_IP" >&2
	exit 1
fi
export MY_IP="$MY_IP_DETECTED"
export MAC_ADDRESS=""
export USER="pi"
TOTAL_KB=3887864
export VIEWER_MEMORY_LIMIT_KB=$(( TOTAL_KB * 8 / 10 ))
export SHM_SIZE_KB=$(( TOTAL_KB * 3 / 10 ))

# Keep generated compose file in project dir so Docker resolves build contexts correctly
COMPOSE_FILE="$HOME/Anthias-Bellforge/docker-compose.prod.yml"

echo "==> Substituting template..."
echo "==> Using MY_IP=$MY_IP"
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
docker compose -f "$COMPOSE_FILE" ps
