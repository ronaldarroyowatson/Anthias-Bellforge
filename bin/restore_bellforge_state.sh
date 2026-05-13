#!/usr/bin/env bash
# Restore BellForge host state from a backup archive created by backup_bellforge_state.sh.

set -euo pipefail

ARCHIVE_PATH=""
SERVICE_NAME="${SERVICE_NAME:-anthias-dev}"
START_SERVICE=1
RESTORE_NETWORK=1
RESTORE_SSH=1
RESTORE_REPO=0

usage() {
    cat <<'USAGE'
Usage: restore_bellforge_state.sh --archive <path> [options]

Options:
  --archive <path>         Backup tar.gz path (required)
  --service <name>         Systemd service name (default: anthias-dev)
  --no-start-service       Do not start service after restore
  --skip-network           Do not restore network files (dhcpcd/wpa/hosts/hostname)
  --skip-ssh               Do not restore authorized_keys
  --restore-repo           Restore /opt/bellforge from backup if present
  -h, --help               Show help
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --archive)
            ARCHIVE_PATH="$2"
            shift 2
            ;;
        --service)
            SERVICE_NAME="$2"
            shift 2
            ;;
        --no-start-service)
            START_SERVICE=0
            shift
            ;;
        --skip-network)
            RESTORE_NETWORK=0
            shift
            ;;
        --skip-ssh)
            RESTORE_SSH=0
            shift
            ;;
        --restore-repo)
            RESTORE_REPO=1
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

if [[ -z "$ARCHIVE_PATH" ]]; then
    echo "--archive is required" >&2
    usage
    exit 1
fi

if [[ ! -f "$ARCHIVE_PATH" ]]; then
    echo "Archive not found: $ARCHIVE_PATH" >&2
    exit 1
fi

echo "Stopping ${SERVICE_NAME} before restore..."
sudo systemctl stop "$SERVICE_NAME" || true

TMP_DIR="$(mktemp -d)"
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "Extracting archive..."
tar -xzf "$ARCHIVE_PATH" -C "$TMP_DIR"
ROOT_DIR="${TMP_DIR}/backup"

if [[ ! -d "$ROOT_DIR" ]]; then
    # Backward compatibility: accept archives with a different single top-level directory
    # or with files extracted directly at the archive root.
    top_level_dirs=()
    while IFS= read -r dir_path; do
        top_level_dirs+=("$dir_path")
    done < <(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d)

    if [[ "${#top_level_dirs[@]}" -eq 1 ]]; then
        ROOT_DIR="${top_level_dirs[0]}"
    else
        ROOT_DIR="$TMP_DIR"
    fi
fi

echo "Using restore root: $ROOT_DIR"

restore_dir() {
    local from_dir="$1"
    local to_dir="$2"

    if [[ -d "$from_dir" ]]; then
        sudo mkdir -p "$(dirname "$to_dir")"
        sudo rm -rf "$to_dir"
        sudo cp -a "$from_dir" "$to_dir"
    fi
}

restore_file() {
    local from_file="$1"
    local to_file="$2"

    if [[ -f "$from_file" ]]; then
        sudo mkdir -p "$(dirname "$to_file")"
        sudo cp -a "$from_file" "$to_file"
    fi
}

echo "Restoring runtime directories..."
restore_dir "${ROOT_DIR}/data/.anthias" /data/.anthias
restore_dir "${ROOT_DIR}/data/anthias_assets" /data/anthias_assets

if [[ ! -f /data/.anthias/anthias.db ]]; then
    # Backward fallback for old archives that only captured the ansible seed DB file.
    restore_file "${ROOT_DIR}/opt/bellforge/ansible/roles/anthias/files/anthias.db" /data/.anthias/anthias.db
fi

if [[ "$RESTORE_REPO" -eq 1 ]]; then
    restore_dir "${ROOT_DIR}/opt/bellforge" /opt/bellforge
fi

echo "Restoring service files..."
restore_file "${ROOT_DIR}/etc/systemd/system/anthias-dev.service" /etc/systemd/system/anthias-dev.service
restore_dir "${ROOT_DIR}/etc/systemd/system/anthias-dev.service.d" /etc/systemd/system/anthias-dev.service.d

if [[ "$RESTORE_NETWORK" -eq 1 ]]; then
    echo "Restoring network files..."
    restore_file "${ROOT_DIR}/etc/dhcpcd.conf" /etc/dhcpcd.conf
    restore_file "${ROOT_DIR}/etc/wpa_supplicant/wpa_supplicant.conf" /etc/wpa_supplicant/wpa_supplicant.conf
    restore_file "${ROOT_DIR}/etc/hostname" /etc/hostname
    restore_file "${ROOT_DIR}/etc/hosts" /etc/hosts
fi

if [[ "$RESTORE_SSH" -eq 1 ]]; then
    echo "Restoring ssh authorized key..."
    restore_file "${ROOT_DIR}/home/pi/.ssh/authorized_keys" /home/pi/.ssh/authorized_keys
    sudo chown -R pi:pi /home/pi/.ssh || true
    sudo chmod 700 /home/pi/.ssh || true
    sudo chmod 600 /home/pi/.ssh/authorized_keys || true
fi

sudo mkdir -p /data/.anthias /data/anthias_assets
sudo chown -R pi:pi /data/.anthias /data/anthias_assets || true

if [[ -f /data/.anthias/anthias.db ]]; then
    stat /data/.anthias/anthias.db
else
    echo "Warning: /data/.anthias/anthias.db is still missing after restore" >&2
fi

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

if [[ "$START_SERVICE" -eq 1 ]]; then
    echo "Starting ${SERVICE_NAME}..."
    sudo systemctl start "$SERVICE_NAME" || true
fi

echo "Restore completed from: $ARCHIVE_PATH"
