#!/usr/bin/env python3
# Remote display doctor: automate Pi startup checks, tests, and debug bundle pull.

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def _now_utc() -> str:
    return datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')


def _run_local(
    command: list[str], check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f'Local command failed ({result.returncode}): {command}\n'
            f'stdout:\n{result.stdout}\n'
            f'stderr:\n{result.stderr}'
        )
    return result


def _build_ssh_base(
    *,
    user: str,
    host: str,
    port: int,
    key_path: str | None,
    timeout_seconds: int,
) -> list[str]:
    base = [
        'ssh',
        '-o',
        'BatchMode=yes',
        '-o',
        f'ConnectTimeout={timeout_seconds}',
        '-p',
        str(port),
    ]
    if key_path:
        base.extend(['-i', key_path])
    base.append(f'{user}@{host}')
    return base


def _run_remote(
    ssh_base: list[str],
    script: str,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    remote_command = f'set -euo pipefail; {script}'
    return _run_local([*ssh_base, remote_command], check=check)


def _pull_remote_file(
    *,
    user: str,
    host: str,
    port: int,
    key_path: str | None,
    remote_path: str,
    local_path: Path,
) -> None:
    scp_base = ['scp', '-P', str(port)]
    if key_path:
        scp_base.extend(['-i', key_path])
    scp_base.extend([f'{user}@{host}:{remote_path}', str(local_path)])
    _run_local(scp_base, check=True)


def _push_local_file(
    *,
    user: str,
    host: str,
    port: int,
    key_path: str | None,
    local_path: Path,
    remote_path: str,
) -> None:
    scp_base = ['scp', '-P', str(port)]
    if key_path:
        scp_base.extend(['-i', key_path])
    scp_base.extend([str(local_path), f'{user}@{host}:{remote_path}'])
    _run_local(scp_base, check=True)


def _check_required_tools() -> None:
    for tool_name in ('ssh', 'scp'):
        if shutil.which(tool_name) is None:
            raise RuntimeError(
                f'Missing required CLI tool: {tool_name}. Install OpenSSH client.'
            )


def _sync_local_display_files(
    *,
    ssh_base: list[str],
    user: str,
    host: str,
    port: int,
    key_path: str | None,
    remote_repo_dir: str,
) -> list[str]:
    repo_root = Path(__file__).resolve().parents[1]
    files_to_sync = [
        'anthias_app/views.py',
        'anthias_app/tests.py',
        'viewer/__init__.py',
        'viewer/utils.py',
        'viewer/render_probe.py',
        'tests/test_viewer.py',
        'tests/test_viewer_utils.py',
        'tests/test_render_probe.py',
        'bin/start_viewer.sh',
        'bin/collect_display_debug_bundle.sh',
        'bin/run_display_pipeline_tests.sh',
        'docker-compose.viewer.yml',
    ]
    synced: list[str] = []

    for relative_path in files_to_sync:
        local_path = repo_root / relative_path
        if not local_path.exists():
            continue

        remote_path = f'{remote_repo_dir}/{relative_path}'
        remote_dir = str(Path(remote_path).parent).replace('\\', '/')
        _run_remote(
            ssh_base, f'mkdir -p {shlex.quote(remote_dir)}', check=True
        )
        _push_local_file(
            user=user,
            host=host,
            port=port,
            key_path=key_path,
            local_path=local_path,
            remote_path=remote_path,
        )
        synced.append(relative_path)

    return synced


def _remote_compose_up_script(repo_dir: str, rebuild: bool) -> str:
    compose_files = '-f docker-compose.dev.yml -f docker-compose.viewer.yml'
    build_arg = '--build' if rebuild else ''
    return (
        f'cd {shlex.quote(repo_dir)}; '
        f'docker compose {compose_files} up -d {build_arg}; '
        f'docker compose {compose_files} ps'
    )


def _remote_sync_script(repo_dir: str, branch: str, remote_name: str) -> str:
    return (
        f'cd {shlex.quote(repo_dir)}; '
        f'git fetch {shlex.quote(remote_name)} --prune; '
        f'git checkout {shlex.quote(branch)}; '
        f'git pull --ff-only {shlex.quote(remote_name)} {shlex.quote(branch)}'
    )


def _remote_release_drm_owners_script() -> str:
    return (
        'if sudo -n true >/dev/null 2>&1; then '
        'for svc in lightdm gdm3 sddm xdm; do '
        'if systemctl is-active --quiet "$svc"; then '
        'echo "Stopping display manager: $svc"; '
        'sudo -n systemctl stop "$svc" || true; '
        'fi; '
        'done; '
        'else '
        'echo "Skipping display-manager stop: sudo -n unavailable"; '
        'fi; '
        'echo "DRM holders after release attempt:"; '
        'if sudo -n true >/dev/null 2>&1; then '
        'sudo -n fuser -v /dev/dri/card* /dev/dri/renderD* 2>/dev/null || true; '
        'else '
        'fuser -v /dev/dri/card* /dev/dri/renderD* 2>/dev/null || true; '
        'fi'
    )


def _normalize_remote_repo_dir(repo_dir: str) -> str:
    if repo_dir == '~':
        return '$HOME'
    if repo_dir.startswith('~/'):
        return '$HOME/' + repo_dir[2:]
    return repo_dir


def _resolve_remote_repo_dir(
    ssh_base: list[str],
    preferred_repo_dir: str,
    ssh_user: str,
) -> str:
    user_home = f'/home/{ssh_user}'
    candidates = [
        preferred_repo_dir,
        f'{user_home}/Anthias-Bellforge',
        f'{user_home}/anthias',
        f'{user_home}/screenly',
        '$HOME/Anthias-Bellforge',
        '$HOME/anthias',
        '$HOME/screenly',
    ]
    unique_candidates = list(dict.fromkeys(candidates))

    rendered_candidates: list[str] = []
    for candidate in unique_candidates:
        if candidate == '$HOME':
            rendered_candidates.append('"$HOME"')
            continue

        if candidate.startswith('$HOME/'):
            rendered_candidates.append(f'"$HOME/{candidate[6:]}"')
            continue

        rendered_candidates.append(shlex.quote(candidate))

    candidate_list = ' '.join(rendered_candidates)
    script = (
        f'for candidate in {candidate_list}; do '
        'if [ -d "$candidate/.git" ]; then '
        'printf "%s" "$candidate"; '
        'exit 0; '
        'fi; '
        'done; '
        'exit 1'
    )
    result = _run_remote(ssh_base, script, check=False)
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(
            'Could not locate a git repo on Pi. Checked: '
            + ', '.join(unique_candidates)
        )

    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            'Automate Pi display debugging: remote sync, restart stack, '
            'run display tests, collect and download debug bundle.'
        )
    )
    parser.add_argument('--host', required=True, help='Pi hostname or IP')
    parser.add_argument('--user', default='pi', help='SSH username')
    parser.add_argument('--port', type=int, default=22, help='SSH port')
    parser.add_argument(
        '--key', default=None, help='Optional SSH private key path'
    )
    parser.add_argument(
        '--repo-dir',
        default='~/Anthias-Bellforge',
        help='Repo path on Pi (default: ~/Anthias-Bellforge)',
    )
    parser.add_argument(
        '--output-dir',
        default='artifacts/pi-display-doctor',
        help='Local output directory for logs and bundles',
    )
    parser.add_argument(
        '--connect-timeout',
        type=int,
        default=15,
        help='SSH connect timeout in seconds',
    )
    parser.add_argument(
        '--no-sync',
        action='store_true',
        help='Skip remote git fetch/checkout/pull',
    )
    parser.add_argument(
        '--sync-branch',
        default='main',
        help='Branch to pull on the Pi when sync is enabled',
    )
    parser.add_argument(
        '--sync-remote',
        default='origin',
        help='Git remote name to sync from',
    )
    parser.add_argument(
        '--no-rebuild',
        action='store_true',
        help='Start compose services without --build',
    )
    parser.add_argument(
        '--keep-display-manager',
        action='store_true',
        help=(
            'Do not stop host display-manager services before compose startup'
        ),
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip running bin/run_display_pipeline_tests.sh on Pi',
    )
    parser.add_argument(
        '--no-local-file-sync',
        action='store_true',
        help=(
            'Skip syncing local display-pipeline files to the Pi before '
            'compose/test steps'
        ),
    )
    parser.add_argument(
        '--skip-bundle',
        action='store_true',
        help='Skip running/downloading collect_display_debug_bundle output',
    )

    args = parser.parse_args()

    _check_required_tools()
    preferred_remote_repo_dir = _normalize_remote_repo_dir(args.repo_dir)

    run_id = _now_utc()
    local_output_dir = Path(args.output_dir) / run_id
    local_output_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, object] = {
        'run_id': run_id,
        'host': args.host,
        'user': args.user,
        'repo_dir': args.repo_dir,
        'steps': [],
    }

    ssh_base = _build_ssh_base(
        user=args.user,
        host=args.host,
        port=args.port,
        key_path=args.key,
        timeout_seconds=args.connect_timeout,
    )

    def run_step(
        name: str, script: str, *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        result = _run_remote(ssh_base, script, check=check)
        summary['steps'].append(
            {
                'step': name,
                'exit_code': result.returncode,
                'stdout_path': f'{name}.stdout.log',
                'stderr_path': f'{name}.stderr.log',
            }
        )
        (local_output_dir / f'{name}.stdout.log').write_text(
            result.stdout, encoding='utf-8'
        )
        (local_output_dir / f'{name}.stderr.log').write_text(
            result.stderr, encoding='utf-8'
        )
        return result

    try:
        run_step('connectivity', 'echo CONNECTED; uname -a; whoami; pwd')

        remote_repo_dir = _resolve_remote_repo_dir(
            ssh_base,
            preferred_repo_dir=preferred_remote_repo_dir,
            ssh_user=args.user,
        )
        summary['resolved_repo_dir'] = remote_repo_dir
        run_step(
            'repo_check',
            f'cd {shlex.quote(remote_repo_dir)}; git rev-parse --abbrev-ref HEAD',
        )

        if not args.no_local_file_sync:
            synced_files = _sync_local_display_files(
                ssh_base=ssh_base,
                user=args.user,
                host=args.host,
                port=args.port,
                key_path=args.key,
                remote_repo_dir=remote_repo_dir,
            )
            summary['local_file_sync'] = {
                'enabled': True,
                'synced_count': len(synced_files),
                'files': synced_files,
            }
        else:
            summary['local_file_sync'] = {'enabled': False}

        if not args.no_sync:
            run_step(
                'sync_repo',
                _remote_sync_script(
                    repo_dir=remote_repo_dir,
                    branch=args.sync_branch,
                    remote_name=args.sync_remote,
                ),
            )

        if not args.keep_display_manager:
            run_step(
                'release_drm_owners',
                _remote_release_drm_owners_script(),
                check=False,
            )

        run_step(
            'compose_up',
            _remote_compose_up_script(
                repo_dir=remote_repo_dir,
                rebuild=not args.no_rebuild,
            ),
        )

        if not args.skip_tests:
            run_step(
                'display_tests',
                (
                    f'cd {shlex.quote(remote_repo_dir)}; '
                    'if docker compose -f docker-compose.dev.yml '
                    '-f docker-compose.viewer.yml ps anthias-server >/dev/null 2>&1; then '
                    'if ! docker compose -f docker-compose.dev.yml '
                    '-f docker-compose.viewer.yml exec -T anthias-server '
                    'bash ./bin/run_display_pipeline_tests.sh; then '
                    'echo "anthias-server display tests failed; retrying in anthias-viewer"; '
                    'docker compose -f docker-compose.dev.yml '
                    '-f docker-compose.viewer.yml exec -T anthias-viewer '
                    'python -m unittest tests.test_viewer tests.test_viewer_utils '
                    'tests.test_render_probe -v; '
                    'fi; '
                    'else '
                    'echo "anthias-server container unavailable for test run"; '
                    'exit 1; '
                    'fi'
                ),
                check=False,
            )

        run_step(
            'render_probe_snapshot',
            (
                f'cd {shlex.quote(remote_repo_dir)}; '
                'docker compose -f docker-compose.dev.yml -f docker-compose.viewer.yml '
                'exec -T redis sh -c "redis-cli GET viewer.render.last_command; '
                'echo ---; redis-cli GET viewer.render.last_result; '
                'echo ---; redis-cli LRANGE viewer.render.history 0 30"'
            ),
            check=False,
        )

        if not args.skip_bundle:
            remote_bundle_dir = f'/tmp/anthias-display-debug-{run_id}'
            run_step(
                'collect_bundle',
                f'cd {shlex.quote(remote_repo_dir)}; '
                f'./bin/collect_display_debug_bundle.sh {shlex.quote(remote_bundle_dir)}',
                check=False,
            )
            remote_bundle_tar = f'{remote_bundle_dir}.tar.gz'
            local_bundle_tar = (
                local_output_dir / f'anthias-display-debug-{run_id}.tar.gz'
            )
            try:
                _pull_remote_file(
                    user=args.user,
                    host=args.host,
                    port=args.port,
                    key_path=args.key,
                    remote_path=remote_bundle_tar,
                    local_path=local_bundle_tar,
                )
                summary['bundle_downloaded'] = str(local_bundle_tar)
            except Exception as exc:
                summary['bundle_download_error'] = str(exc)

        summary_path = local_output_dir / 'summary.json'
        summary_path.write_text(
            json.dumps(summary, indent=2),
            encoding='utf-8',
        )

        print(f'Run complete. Summary: {summary_path}')
        return 0

    except Exception as exc:
        summary['fatal_error'] = str(exc)
        summary_path = local_output_dir / 'summary.json'
        summary_path.write_text(
            json.dumps(summary, indent=2),
            encoding='utf-8',
        )
        print(f'Run failed. Summary: {summary_path}', file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
