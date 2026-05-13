#!/usr/bin/env bash
# Run a reproducible fresh-install simulation workflow on a remotely managed Pi.

set -euo pipefail

PI_HOST="${PI_HOST:-192.168.2.180}"
PI_USER="${PI_USER:-pi}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/exportedRaspberryPiKey}"
REPO_URL="${REPO_URL:-https://github.com/ronaldarroyowatson/Anthias-Bellforge.git}"
REPO_DIR="${REPO_DIR:-/opt/bellforge}"
BACKUP_ROOT="${BACKUP_ROOT:-/home/pi/backups}"
TARGET_BACKUP=""

usage() {
    cat <<'USAGE'
Usage: run_pi_fresh_install_simulation.sh [options]

Options:
  --host <ip-or-hostname>      Pi host (default: 192.168.2.180)
  --user <username>            SSH user (default: pi)
  --key <path>                 SSH key path
  --repo-url <url>             BellForge git repo URL
  --repo-dir <path>            Target repo dir on Pi (default: /opt/bellforge)
  --backup-root <path>         Backup directory on Pi (default: /home/pi/backups)
  --backup <path>              Explicit backup archive to restore
  -h, --help                   Show help
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)
            PI_HOST="$2"
            shift 2
            ;;
        --user)
            PI_USER="$2"
            shift 2
            ;;
        --key)
            SSH_KEY="$2"
            shift 2
            ;;
        --repo-url)
            REPO_URL="$2"
            shift 2
            ;;
        --repo-dir)
            REPO_DIR="$2"
            shift 2
            ;;
        --backup-root)
            BACKUP_ROOT="$2"
            shift 2
            ;;
        --backup)
            TARGET_BACKUP="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

SSH_BASE=(ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${PI_USER}@${PI_HOST}")

run_remote() {
    local script_content="$1"
    printf '%s\n' "$script_content" | "${SSH_BASE[@]}" bash
}

echo "== Phase 1: Full OS upgrade and app-level reset =="
run_remote "
set -euo pipefail
sudo DEBIAN_FRONTEND=noninteractive apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y
sudo DEBIAN_FRONTEND=noninteractive apt-get autoremove -y
sudo systemctl stop anthias-dev || true
if [ -d '${REPO_DIR}' ]; then
  cd '${REPO_DIR}'
  COMPOSE_PROJECT_NAME=anthias-bellforge docker compose -f docker-compose.dev.yml -f docker-compose.viewer.yml down --remove-orphans || true
fi
sudo rm -rf '${REPO_DIR}' /data/.anthias /data/anthias_assets
sudo mkdir -p /data/.anthias /data/anthias_assets
sudo chown -R pi:pi /data/.anthias /data/anthias_assets
"

echo "== Phase 2: Fresh clone and build-ready install =="
run_remote "
set -euo pipefail
sudo git clone '${REPO_URL}' '${REPO_DIR}'
sudo chown -R pi:pi '${REPO_DIR}'
cd '${REPO_DIR}'
/bin/bash ./bin/generate_dev_mode_dockerfiles.sh
sudo cp -f ./bin/anthias-dev.service /etc/systemd/system/anthias-dev.service
sudo mkdir -p /etc/systemd/system/anthias-dev.service.d
cat <<'EOF' | sudo tee /etc/systemd/system/anthias-dev.service.d/override.conf >/dev/null
[Service]
WorkingDirectory=${REPO_DIR}
Environment=COMPOSE_PROJECT_NAME=anthias-bellforge
ExecStart=
ExecStart=/bin/bash -lc 'MY_IP=\$(hostname -I | awk '\''{print \$1}'\''); export MY_IP; exec /usr/bin/docker compose -f ${REPO_DIR}/docker-compose.dev.yml -f ${REPO_DIR}/docker-compose.viewer.yml up -d'
ExecStop=
ExecStop=/usr/bin/docker compose -f ${REPO_DIR}/docker-compose.dev.yml -f ${REPO_DIR}/docker-compose.viewer.yml down --remove-orphans
EOF
sudo systemctl daemon-reload
sudo systemctl reset-failed anthias-dev || true
sudo systemctl start anthias-dev
"

echo "== Phase 3: Wait for healthy startup =="
run_remote "
set -euo pipefail
for i in \$(seq 1 80); do
  state=\$(systemctl is-active anthias-dev || true)
  if [ \"\$state\" = 'active' ]; then
    break
  fi
  if [ \"\$state\" = 'failed' ]; then
    sudo systemctl status anthias-dev --no-pager -n 120
    sudo journalctl -u anthias-dev --no-pager -n 200
    exit 1
  fi
  sleep 15
done
systemctl is-active anthias-dev
curl -sS -o /dev/null -w 'splash_http=%{http_code}\\n' http://127.0.0.1:8000/splash-page || true
docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}' | grep -Ei 'anthias-bellforge|viewer|server|redis|celery' || true
"

if [[ -z "$TARGET_BACKUP" ]]; then
    TARGET_BACKUP="$("${SSH_BASE[@]}" "ls -1t '${BACKUP_ROOT}'/bellforge_backup_*.tar.gz 2>/dev/null | head -n 1 || true")"
fi

if [[ -z "$TARGET_BACKUP" ]]; then
    echo "No backup archive found in ${BACKUP_ROOT}; stopping before restore validation."
    exit 0
fi

echo "== Phase 4: Restore validation from ${TARGET_BACKUP} =="
run_remote "
set -euo pipefail
cd '${REPO_DIR}'
/bin/bash ./bin/restore_bellforge_state.sh --archive '${TARGET_BACKUP}'
for i in \$(seq 1 40); do
  state=\$(systemctl is-active anthias-dev || true)
  if [ \"\$state\" = 'active' ]; then
    break
  fi
  sleep 10
done
systemctl is-active anthias-dev || true
curl -sS -o /dev/null -w 'splash_http=%{http_code}\\n' http://127.0.0.1:8000/splash-page || true
stat -c 'db_stat=%n %s %y' /data/.anthias/anthias.db 2>/dev/null || echo 'db_stat=missing'
"

echo "Fresh-install simulation workflow complete."
