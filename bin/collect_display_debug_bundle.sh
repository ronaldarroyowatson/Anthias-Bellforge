#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_ARGS=(-f docker-compose.dev.yml -f docker-compose.viewer.yml)
VIEWER_CONTAINER="anthias-bellforge-anthias-viewer-1"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_ROOT="${1:-/tmp/anthias-display-debug-${TIMESTAMP}}"
OUT_DIR="${OUT_ROOT%/}"

mkdir -p "$OUT_DIR"

echo "Collecting Anthias display diagnostics into: $OUT_DIR"

run_capture() {
    local name="$1"
    shift

    if "$@" >"$OUT_DIR/${name}.txt" 2>&1; then
        return 0
    fi

    local rc=$?

    {
        echo "Command failed: $*"
        echo "Exit code: $rc"
    } >>"$OUT_DIR/${name}.txt"
}

run_capture host_uname uname -a
run_capture host_uptime uptime
run_capture host_cpuinfo_head sh -c "grep -E 'Model|Hardware|Revision|Serial' /proc/cpuinfo | head -20"
run_capture host_boot_config cat /boot/firmware/config.txt
run_capture host_cmdline cat /boot/firmware/cmdline.txt
run_capture host_drm_tree sh -c "ls -la /sys/class/drm && for p in /sys/class/drm/card*-*/status; do echo \"\$p: \$(cat \$p 2>/dev/null)\"; done"
run_capture host_dri_nodes sh -c "ls -la /dev/dri && stat /dev/dri/*"
run_capture host_dri_holders sh -c "if sudo -n true >/dev/null 2>&1; then sudo -n fuser -v /dev/dri/card* /dev/dri/renderD* 2>/dev/null || true; else fuser -v /dev/dri/card* /dev/dri/renderD* 2>/dev/null || true; fi"
run_capture host_display_manager_state sh -c "for svc in lightdm gdm3 sddm xdm; do printf '%s: ' \"\$svc\"; systemctl is-active \"\$svc\" 2>/dev/null || true; done"
run_capture host_journal_anthias_dev sh -c "journalctl -u anthias-dev --no-pager -n 300"

run_capture compose_ps docker compose "${COMPOSE_ARGS[@]}" ps
run_capture compose_server_logs docker compose "${COMPOSE_ARGS[@]}" logs --tail 200 anthias-server
run_capture compose_viewer_logs docker compose "${COMPOSE_ARGS[@]}" logs --tail 400 anthias-viewer
run_capture redis_render_probe_state docker compose "${COMPOSE_ARGS[@]}" exec -T redis sh -c "redis-cli GET viewer.render.last_command; echo ---; redis-cli GET viewer.render.last_result; echo ---; redis-cli LRANGE viewer.render.history 0 20"

run_capture viewer_id docker exec "$VIEWER_CONTAINER" id
run_capture viewer_processes docker exec "$VIEWER_CONTAINER" ps aux
run_capture viewer_env docker exec "$VIEWER_CONTAINER" env
run_capture viewer_drm sh -c "docker exec $VIEWER_CONTAINER sh -c 'ls -la /dev/dri; ls -la /sys/class/drm; for p in /sys/class/drm/card*-*/status; do echo \"\$p: \$(cat \$p 2>/dev/null)\"; done'"
run_capture viewer_dri_holders sh -c "docker exec $VIEWER_CONTAINER sh -c 'fuser -v /dev/dri/card* /dev/dri/renderD* 2>/dev/null || true'"
run_capture viewer_web_ping docker exec "$VIEWER_CONTAINER" curl -sS -o /dev/null -w "%{http_code}\n" http://anthias-server:8080/splash-page
run_capture viewer_display_html sh -c "docker exec $VIEWER_CONTAINER sh -c 'cat /tmp/display.html 2>/dev/null || echo display-html-missing'"
run_capture viewer_display_url_line sh -c "docker exec $VIEWER_CONTAINER sh -c 'grep -n \"class=\\\"url\\\"\" /tmp/display.html 2>/dev/null || echo display-url-line-missing'"
run_capture viewer_webview_proc_environ sh -c "docker exec $VIEWER_CONTAINER sh -c 'set -- \$(pidof AnthiasWebview 2>/dev/null || true); pid=\${1:-}; if [ -n \"\$pid\" ]; then cat /proc/\$pid/environ | tr \"\\0\" \"\\n\"; else echo \"AnthiasWebview not running\"; fi'"

# Run a short-lived foreground webview process strictly for diagnostics.
run_capture viewer_webview_eglfs_probe sh -c "docker exec -e QT_QPA_PLATFORM=eglfs -e QT_QPA_DEBUG=1 -e QT_LOGGING_RULES='qt.qpa.*=true' $VIEWER_CONTAINER timeout 8 AnthiasWebview"

if command -v tar >/dev/null 2>&1; then
    TAR_PATH="${OUT_DIR}.tar.gz"
    tar -C "$(dirname "$OUT_DIR")" -czf "$TAR_PATH" "$(basename "$OUT_DIR")"
    echo "Bundle created: $TAR_PATH"
else
    echo "tar not available; bundle directory left at: $OUT_DIR"
fi
