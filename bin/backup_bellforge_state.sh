#!/usr/bin/env bash
# Create a complete, restorable BellForge host backup archive.

set -euo pipefail

BACKUP_ROOT="${BACKUP_ROOT:-/home/pi/backups}"
REPO_DIR="${REPO_DIR:-/opt/bellforge}"
SERVICE_NAME="${SERVICE_NAME:-anthias-dev}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
ARCHIVE_PATH="${BACKUP_ROOT}/bellforge_backup_${TIMESTAMP}.tar.gz"
MANIFEST_PATH="${BACKUP_ROOT}/bellforge_backup_${TIMESTAMP}.manifest.txt"
STOP_SERVICE=1
START_SERVICE=1
INCLUDE_REPO=1

usage() {
    cat <<'USAGE'
Usage: backup_bellforge_state.sh [options]

Options:
  --backup-root <path>     Backup output directory (default: /home/pi/backups)
  --repo-dir <path>        BellForge repo path (default: /opt/bellforge)
  --service <name>         Systemd service name (default: anthias-dev)
  --no-stop-service        Do not stop service before snapshotting
  --no-restart-service     Do not restart service after backup
  --exclude-repo           Do not include repo working tree in backup
  -h, --help               Show help
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backup-root)
            BACKUP_ROOT="$2"
            shift 2
            ;;
        --repo-dir)
            REPO_DIR="$2"
            shift 2
            ;;
        --service)
            SERVICE_NAME="$2"
            shift 2
            ;;
        --no-stop-service)
            STOP_SERVICE=0
            shift
            ;;
        --no-restart-service)
            START_SERVICE=0
            shift
            ;;
        --exclude-repo)
            INCLUDE_REPO=0
            shift
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

mkdir -p "$BACKUP_ROOT"

TMP_DIR="$(mktemp -d)"
STAGING_DIR="${TMP_DIR}/backup"
mkdir -p "$STAGING_DIR"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

copy_if_exists() {
    local source_path="$1"
    local target_path="$2"

    if [[ -e "$source_path" ]]; then
        mkdir -p "$(dirname "$target_path")"
        cp -a "$source_path" "$target_path"
    fi
}

if [[ "$STOP_SERVICE" -eq 1 ]]; then
    echo "Stopping ${SERVICE_NAME} before backup..."
    sudo systemctl stop "$SERVICE_NAME" || true
fi

echo "Collecting runtime data..."
copy_if_exists /data/.anthias "${STAGING_DIR}/data/.anthias"
copy_if_exists /data/anthias_assets "${STAGING_DIR}/data/anthias_assets"

echo "Collecting service and host config..."
copy_if_exists /etc/systemd/system/anthias-dev.service "${STAGING_DIR}/etc/systemd/system/anthias-dev.service"
copy_if_exists /etc/systemd/system/anthias-dev.service.d "${STAGING_DIR}/etc/systemd/system/anthias-dev.service.d"
copy_if_exists /etc/dhcpcd.conf "${STAGING_DIR}/etc/dhcpcd.conf"
copy_if_exists /etc/wpa_supplicant/wpa_supplicant.conf "${STAGING_DIR}/etc/wpa_supplicant/wpa_supplicant.conf"
copy_if_exists /etc/hostname "${STAGING_DIR}/etc/hostname"
copy_if_exists /etc/hosts "${STAGING_DIR}/etc/hosts"
copy_if_exists /home/pi/.ssh/authorized_keys "${STAGING_DIR}/home/pi/.ssh/authorized_keys"

if [[ "$INCLUDE_REPO" -eq 1 && -d "$REPO_DIR" ]]; then
    echo "Collecting repo snapshot from ${REPO_DIR}..."
    mkdir -p "${STAGING_DIR}/opt"
    cp -a "$REPO_DIR" "${STAGING_DIR}/opt/bellforge"
fi

echo "Collecting metadata..."
{
    echo "backup_created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "hostname=$(hostname)"
    echo "kernel=$(uname -a)"
    echo "service_name=${SERVICE_NAME}"
    echo "repo_dir=${REPO_DIR}"
    echo "include_repo=${INCLUDE_REPO}"
    echo "stop_service=${STOP_SERVICE}"
    echo "restart_service=${START_SERVICE}"
} > "${STAGING_DIR}/metadata.txt"

(
    cd "$TMP_DIR"
    tar -czf "$ARCHIVE_PATH" backup
)

sha256sum "$ARCHIVE_PATH" > "$MANIFEST_PATH"

echo "Backup archive created: $ARCHIVE_PATH"
echo "Backup manifest created: $MANIFEST_PATH"

if [[ "$START_SERVICE" -eq 1 ]]; then
    echo "Restarting ${SERVICE_NAME} after backup..."
    sudo systemctl start "$SERVICE_NAME" || true
fi
