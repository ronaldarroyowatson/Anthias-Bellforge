#!/bin/bash

# Defensively expose legacy /data/.screenly and /data/screenly_assets
# paths as symlinks if a running setup still has them in DB rows or in
# an older docker-compose file. No-op on clean installs.
/usr/src/app/bin/migrate_in_container_paths.sh

# Fixes permission on /dev/vchiq
chgrp -f video /dev/vchiq
chmod -f g+rwX /dev/vchiq

# Set permission for sha file
chown -f viewer /dev/snd/*
chown -f viewer /data/.anthias/latest_anthias_sha

# Fixes caching in QTWebEngine
mkdir -p /data/.local/share/AnthiasWebview/QtWebEngine \
    /data/.cache/AnthiasWebview \
    /data/.cache/fontconfig \
    /data/.pki

chown -Rf viewer /data/.local/share/AnthiasWebview
chown -Rf viewer /data/.cache/AnthiasWebview/
chown -Rf viewer /data/.cache/fontconfig
chown -Rf viewer /data/.pki

# Qt + dbus + various Linux apps look up XDG_RUNTIME_DIR; without it they
# log warnings and fall back to ad-hoc paths. Provide a per-uid runtime
# dir owned by the viewer user.
VIEWER_UID=$(id -u viewer)
export XDG_RUNTIME_DIR="/run/user/${VIEWER_UID}"
mkdir -p "${XDG_RUNTIME_DIR}"
chown viewer:video "${XDG_RUNTIME_DIR}"
chmod 700 "${XDG_RUNTIME_DIR}"

# Temporary workaround for watchdog
touch /tmp/anthias.watchdog
chown viewer /tmp/anthias.watchdog

# For whatever reason Raspbian messes up the sudo permissions
chown -f root:root /usr/bin/sudo
chown -Rf root:root /etc/sudoers.d
chown -Rf root:root /etc/sudo.conf
chown -Rf root:root /usr/lib/sudo
chown -f root:root /etc/sudoers
chmod -f 4755 /usr/bin/sudo

# SIGUSR1 from the viewer is also sent to the container
# Prevent it so that the container does not fail
trap '' 16

# Disable swapping. Path is cgroup v1 only; cgroup v2 hosts (modern
# Debian / Ubuntu / Raspberry Pi OS Bookworm) don't expose it, so guard
# the write to avoid a noisy "No such file or directory" on every boot.
if [ -w /sys/fs/cgroup/memory/memory.swappiness ]; then
    echo 0 > /sys/fs/cgroup/memory/memory.swappiness
fi

# Race guard for cold boots/hotplug: wait briefly for DRM to expose
# connectors and report at least one HDMI output as connected.
HDMI_DETECT_TIMEOUT_SECONDS="${HDMI_DETECT_TIMEOUT_SECONDS:-30}"
connected_hdmi_connectors() {
    for connector in /sys/class/drm/card*-HDMI-A-*; do
        [ -d "$connector" ] || continue
        [ "$(cat "$connector/status" 2>/dev/null)" = 'connected' ] || continue
        basename "$connector"
    done
}

dump_drm_connectors() {
    for connector in /sys/class/drm/card*-*; do
        [ -d "$connector" ] || continue
        state=$(cat "$connector/status" 2>/dev/null || true)
        echo "start_viewer: drm $(basename "$connector") status=${state:-unknown}"
    done
}

waited=0
while [ "$waited" -lt "$HDMI_DETECT_TIMEOUT_SECONDS" ]; do
    CONNECTED_HDMI=$(connected_hdmi_connectors)
    [ -n "$CONNECTED_HDMI" ] && break
    sleep 1
    waited=$((waited + 1))
done

if [ -n "$CONNECTED_HDMI" ]; then
    echo "start_viewer: connected HDMI connector(s):"
    echo "$CONNECTED_HDMI" | sed 's/^/  - /'
else
    echo "start_viewer: no HDMI connector reported connected after ${HDMI_DETECT_TIMEOUT_SECONDS}s"
    dump_drm_connectors
fi

if [ "${VIEWER_DISPLAY_DEBUG:-0}" = "1" ]; then
    echo "start_viewer: VIEWER_DISPLAY_DEBUG=1"
    echo "start_viewer: kernel $(uname -a)"
    echo "start_viewer: /dev/dri devices: $(ls /dev/dri 2>/dev/null | tr '\n' ' ')"
    if [ -r /boot/firmware/config.txt ]; then
        overlay=$(grep -E '^dtoverlay=' /boot/firmware/config.txt | tail -n1)
        [ -n "$overlay" ] && echo "start_viewer: $overlay"
    fi

    # Keep default log volume reasonable unless explicitly overridden.
    export QT_QPA_DEBUG="${QT_QPA_DEBUG:-1}"
    export QT_LOGGING_RULES="${QT_LOGGING_RULES:-qt.qpa.*=true}"
fi

# If the user didn't pin a KMS connector index, infer one from the first
# connected HDMI port so either physical port can work without manual edits.
if [ -z "${QT_QPA_EGLFS_KMS_CONNECTOR_INDEX:-}" ] && [ -n "$CONNECTED_HDMI" ]; then
    SELECTED_CONNECTOR=$(echo "$CONNECTED_HDMI" | head -n1)
    PORT_NUMBER=$(echo "$SELECTED_CONNECTOR" | awk -F'HDMI-A-' '{print $2}')
    CARD_NAME=$(echo "$SELECTED_CONNECTOR" | awk -F'-' '{print $1}')
    case "$PORT_NUMBER" in
        ''|*[!0-9]*)
            ;;
        *)
            if [ "$PORT_NUMBER" -gt 0 ]; then
                QT_QPA_EGLFS_KMS_CONNECTOR_INDEX=$((PORT_NUMBER - 1))
                export QT_QPA_EGLFS_KMS_CONNECTOR_INDEX
                # Also pin the DRM device so Qt EGLFS opens the display
                # controller (card1 on Pi 5) rather than defaulting to card0
                # (the V3D GPU, which has no display connectors).
                if [ -n "$CARD_NAME" ] && [ -c "/dev/dri/$CARD_NAME" ]; then
                    export QT_QPA_EGLFS_KMS_DEVICE="/dev/dri/$CARD_NAME"
                fi
                echo "start_viewer: using $SELECTED_CONNECTOR (QT_QPA_EGLFS_KMS_CONNECTOR_INDEX=${QT_QPA_EGLFS_KMS_CONNECTOR_INDEX}, QT_QPA_EGLFS_KMS_DEVICE=${QT_QPA_EGLFS_KMS_DEVICE:-default})"
            fi
            ;;
    esac
fi

# QtWebEngine renders web content at 1 CSS px = 1 physical px by default,
# which makes pages look ~half-size on a 4K TV (forum 6538). Pick a Qt
# scale factor based on the active framebuffer width so the page is laid
# out as if the screen were 1920px wide and then upscaled. Pi/x86 viewer
# images both expose connector state under /sys/class/drm — the first
# line of `modes` is the active/preferred mode. Skip if the user already
# set QT_SCALE_FACTOR explicitly, so a manual override always wins.
if [ -z "${QT_SCALE_FACTOR:-}" ]; then
    SCREEN_WIDTH=""
    for connector in /sys/class/drm/card*-*; do
        [ -d "$connector" ] || continue
        [ "$(cat "$connector/status" 2>/dev/null)" = "connected" ] || continue
        first_mode=$(head -n1 "$connector/modes" 2>/dev/null)
        case "$first_mode" in
            *x*)
                SCREEN_WIDTH="${first_mode%%x*}"
                break
                ;;
        esac
    done
    if [ -n "$SCREEN_WIDTH" ]; then
        # Round to the nearest integer ratio of 1920 (1, 2, 3...) and
        # cap at 4 so a freak EDID can't request 8x.
        SCALE=$(awk -v w="$SCREEN_WIDTH" 'BEGIN {
            s = w / 1920
            if (s < 1.5) print 1
            else if (s < 2.5) print 2
            else if (s < 3.5) print 3
            else print 4
        }')
        if [ "${SCALE:-1}" -gt 1 ]; then
            export QT_SCALE_FACTOR="$SCALE"
            echo "start_viewer: detected ${SCREEN_WIDTH}px screen, QT_SCALE_FACTOR=${SCALE}"
        fi
    fi
fi

# Start viewer.
# Some copied source dirs can end up mode 700 in certain host setups,
# which blocks the unprivileged viewer user from importing modules.
chmod -R a+rX /usr/src/app 2>/dev/null || true

# sudo resets PATH to its secure_path, so resolve python via the
# absolute venv path instead — `python` on PATH would otherwise hit
# the system interpreter, which has no Anthias deps installed.
# --preserve-env=XDG_RUNTIME_DIR forces sudo to forward the runtime dir
# we just set; -E alone is subject to env_check / env_delete and is not
# guaranteed for XDG_* on Debian's default sudoers.
PRESERVE_ENV_KEYS="XDG_RUNTIME_DIR,QT_SCALE_FACTOR,QT_QPA_EGLFS_KMS_CONNECTOR_INDEX,QT_QPA_EGLFS_KMS_DEVICE,QT_QPA_DEBUG,QT_LOGGING_RULES,QTWEBENGINE_CHROMIUM_FLAGS,VIEWER_DISPLAY_DEBUG"
if [ "${VIEWER_RUN_AS_ROOT:-0}" = "1" ]; then
    # QtWebEngine refuses to start as root unless Chromium sandboxing is disabled.
    case " ${QTWEBENGINE_CHROMIUM_FLAGS:-} " in
        *" --no-sandbox "*)
            ;;
        *)
            export QTWEBENGINE_CHROMIUM_FLAGS="${QTWEBENGINE_CHROMIUM_FLAGS:-} --no-sandbox"
            ;;
    esac

    echo "start_viewer: launching viewer runtime as root (VIEWER_RUN_AS_ROOT=1)"
    echo "start_viewer: QTWEBENGINE_CHROMIUM_FLAGS=${QTWEBENGINE_CHROMIUM_FLAGS}"
    dbus-run-session env PYTHONPATH=/usr/src/app /venv/bin/python -m viewer.__main__ &
else
    sudo --preserve-env="$PRESERVE_ENV_KEYS" -E -u viewer \
        dbus-run-session env PYTHONPATH=/usr/src/app /venv/bin/python -m viewer.__main__ &
fi

# Wait for the viewer
while true; do
  PID=$(pidof python)
  if [ "$?" == '0' ]; then
    break
  fi
  sleep 0.5
done

# If the viewer runs OOM, force the OOM killer to kill this script so the container restarts
echo 1000 > /proc/$$/oom_score_adj

# Exit when the viewer stops
while kill -0 "$PID"; do
  sleep 1
done
