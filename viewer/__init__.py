# -*- coding: utf-8 -*-
# Viewer runtime: startup splash, display transport, and playback loop.

import logging
import ipaddress
import sys
from glob import glob
from os import getenv, path
from signal import SIGALRM, signal
from time import monotonic, sleep
from typing import Any
from urllib.parse import quote, urlsplit

import django
import pydbus
import sh as sh
from tenacity import Retrying, stop_after_attempt, wait_fixed

from settings import ReplySender, settings
from viewer.constants import BALENA_IP_RETRY_DELAY as BALENA_IP_RETRY_DELAY
from viewer.constants import EMPTY_PL_DELAY as EMPTY_PL_DELAY
from viewer.constants import MAX_BALENA_IP_RETRIES as MAX_BALENA_IP_RETRIES
from viewer.constants import SERVER_WAIT_TIMEOUT as SERVER_WAIT_TIMEOUT
from viewer.constants import SPLASH_DELAY as SPLASH_DELAY
from viewer.constants import SPLASH_PAGE_URL as SPLASH_PAGE_URL
from viewer.constants import STANDBY_SCREEN as STANDBY_SCREEN
from viewer.media_player import MediaPlayerProxy
from viewer.playback import navigate_to_asset, play_loop, skip_asset, stop_loop
from viewer.utils import (
    command_not_found,
    get_skip_event,
    sigalrm,
    wait_for_server,
    watchdog,
)

django.setup()

# Place imports that uses Django in this block.

from lib.utils import (  # noqa: E402
    connect_to_redis,
    get_balena_device_info,
    get_node_ip,
    is_balena_app,
    string_to_bool,
    url_fails,
)
from viewer.messaging import ViewerSubscriber  # noqa: E402
from viewer.render_probe import (
    record_render_command,  # noqa: E402
    record_render_result,  # noqa: E402
)
from viewer.scheduling import Scheduler  # noqa: E402

__author__ = 'Screenly, Inc'
__copyright__ = 'Copyright 2012-2026, Screenly, Inc'
__license__ = 'Dual License: GPLv2 and Commercial License'


current_browser_url: str | None = None
browser: Any = None
loop_is_stopped: bool = False
browser_bus: Any = None
browser_stdout_cursor: int = 0
r = connect_to_redis()
reply_sender = ReplySender(r)

HOME: str | None = None

scheduler: Any = None


def send_current_asset_id_to_server(correlation_id: str | None) -> None:
    if not correlation_id:
        logging.warning(
            'current_asset_id command received without a correlation ID; '
            'dropping reply.'
        )
        return

    # `subscriber.start()` runs before `scheduler = Scheduler()` in
    # main(), so a `current_asset_id` command arriving during the
    # `wait_for_server` window would `AttributeError` on
    # `scheduler.current_asset_id`. Reply with `None` instead — the v1
    # endpoint already treats a falsy id as "no current asset" and
    # returns `[]`, which is the correct answer pre-scheduler-init.
    if scheduler is None:
        logging.info(
            'current_asset_id requested before scheduler was ready; '
            'replying with no current asset.'
        )
        reply_sender.send(correlation_id, {'current_asset_id': None})
        return

    reply_sender.send(
        correlation_id, {'current_asset_id': scheduler.current_asset_id}
    )


commands = {
    'next': lambda _: skip_asset(scheduler),
    'previous': lambda _: skip_asset(scheduler, back=True),
    'asset': lambda asset_id: navigate_to_asset(scheduler, asset_id),
    'reload': lambda _: load_settings(),
    'stop': lambda _: setattr(
        __import__('__main__'), 'loop_is_stopped', stop_loop(scheduler)
    ),
    'play': lambda _: setattr(
        __import__('__main__'), 'loop_is_stopped', play_loop()
    ),
    'unknown': lambda _: command_not_found(),
    'current_asset_id': lambda corr: send_current_asset_id_to_server(corr),
}


BROWSER_STARTUP_TIMEOUT_SECONDS = 30
BROWSER_HANDSHAKE_LINE = 'Anthias service start'
SUBSCRIBER_READY_WAIT_TIMEOUT_SECONDS = 5
SUBSCRIBER_READY_POLL_INTERVAL_SECONDS = 0.2
SETUP_RETRY_ATTEMPTS = 5
SETUP_RETRY_DELAY_SECONDS = 2


def _display_debug_enabled() -> bool:
    return string_to_bool(getenv('VIEWER_DISPLAY_DEBUG', '0'))


def _drm_connector_snapshot() -> list[str]:
    snapshot: list[str] = []

    for connector in sorted(glob('/sys/class/drm/card*-*')):
        status_file = path.join(connector, 'status')
        status = 'unknown'

        if path.isfile(status_file):
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    status = f.read().strip()
            except OSError:
                status = 'error'

        modes_file = path.join(connector, 'modes')
        mode = 'n/a'
        if path.isfile(modes_file):
            try:
                with open(modes_file, 'r', encoding='utf-8') as f:
                    mode = (f.readline() or '').strip() or 'n/a'
            except OSError:
                mode = 'error'

        snapshot.append(
            f'{path.basename(connector)} status={status} mode={mode}'
        )

    return snapshot


def _log_display_runtime_diagnostics() -> None:
    if not _display_debug_enabled():
        return

    logging.info('viewer-display-debug: enabled')

    qt_env_keys = [
        'QT_QPA_PLATFORM',
        'QT_QPA_EGLFS_KMS_CONNECTOR_INDEX',
        'QT_SCALE_FACTOR',
        'QT_QPA_DEBUG',
        'QT_LOGGING_RULES',
        'QTWEBENGINE_CHROMIUM_FLAGS',
        'XDG_RUNTIME_DIR',
    ]
    for key in qt_env_keys:
        value = getenv(key)
        if value:
            logging.info('viewer-display-debug: env %s=%s', key, value)

    for connector_state in _drm_connector_snapshot():
        logging.info('viewer-display-debug: drm %s', connector_state)


def _drain_browser_stdout() -> None:
    global browser_stdout_cursor

    if browser is None:
        return

    try:
        raw_output = browser.process.stdout
        if isinstance(raw_output, bytes):
            output = raw_output.decode('utf-8', errors='replace')
        else:
            output = str(raw_output)
    except Exception as exc:
        logging.debug('viewer-display-debug: stdout decode failed: %s', exc)
        return

    if browser_stdout_cursor >= len(output):
        return

    new_output = output[browser_stdout_cursor:]
    browser_stdout_cursor = len(output)

    for line in new_output.splitlines():
        line = line.strip()
        if line:
            logging.info('AnthiasWebview: %s', line)


def _normalize_startup_host(raw_host: str) -> str:
    host = raw_host.strip()
    if not host:
        return 'anthias.local'

    if host.startswith('http://') or host.startswith('https://'):
        return host

    try:
        parsed_ip = ipaddress.ip_address(host.strip('[]'))
        if isinstance(parsed_ip, ipaddress.IPv6Address):
            host = f'[{parsed_ip}]'
        else:
            host = str(parsed_ip)
    except ValueError:
        pass

    return f'http://{host}'


def _is_local_startup_host(raw_host: str) -> bool:
    value = raw_host.strip()
    if not value:
        return False

    parse_target = value if '://' in value else f'//{value}'
    parsed = urlsplit(parse_target)
    host = (parsed.hostname or value).strip().strip('[]').lower()
    if host in {'localhost', '0.0.0.0', '::1'}:
        return True
    return host.startswith('127.')


def _first_non_local_candidate(raw_candidates: str) -> str:
    for token in raw_candidates.replace(',', ' ').split():
        candidate = token.strip()
        if not candidate:
            continue

        try:
            parsed_ip = ipaddress.ip_address(candidate.strip('[]'))
        except ValueError:
            continue

        if parsed_ip.is_loopback or parsed_ip.is_unspecified:
            continue

        return candidate
    return ''


def _resolve_startup_connect_url() -> str:
    configured_host = getenv('MY_IP', '').strip()
    if configured_host and not _is_local_startup_host(configured_host):
        return _normalize_startup_host(configured_host)

    node_ip_candidates = _first_non_local_candidate(get_node_ip())
    if node_ip_candidates:
        return _normalize_startup_host(node_ip_candidates)

    if configured_host:
        return _normalize_startup_host(configured_host)

    return _normalize_startup_host('anthias.local')


def _build_offline_splash_url() -> str:
    connect_url = _resolve_startup_connect_url()
    html = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Anthias Startup</title>
    <style>
        :root {{
            --bg: #0b1220;
            --surface: #101a2f;
            --fg: #ecf2ff;
            --muted: #98a9cc;
            --accent: #4fd1c5;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            min-height: 100vh;
            background: radial-gradient(circle at 20% 20%, #1a2a4a, var(--bg));
            color: var(--fg);
            font-family: "Segoe UI", "Noto Sans", sans-serif;
            display: grid;
            place-items: center;
            padding: 1.5rem;
        }}
        .panel {{
            width: min(52rem, 100%);
            background: var(--surface);
            border: 1px solid #1f2c49;
            border-radius: 1rem;
            padding: 2rem;
            box-shadow: 0 1.5rem 2.5rem rgba(0, 0, 0, 0.35);
        }}
        h1 {{
            margin: 0 0 0.75rem;
            font-size: clamp(1.4rem, 2vw, 2rem);
            letter-spacing: 0.02em;
        }}
        p {{
            margin: 0.5rem 0;
            line-height: 1.5;
            color: var(--muted);
        }}
        .url {{
            margin-top: 1rem;
            padding: 0.8rem 1rem;
            border-left: 0.3rem solid var(--accent);
            background: #0f1730;
            color: var(--fg);
            font-size: clamp(1.05rem, 1.6vw, 1.3rem);
            overflow-wrap: anywhere;
        }}
    </style>
</head>
<body>
    <main class="panel">
        <h1>Anthias is starting</h1>
        <p>The device display is online and waiting for the server splash page.</p>
        <p>Open this address from another device on your network:</p>
        <div class="url">{connect_url}</div>
    </main>
</body>
</html>"""
    return 'data:text/html,' + quote(html)


def _show_splash_with_fallback(server_is_ready: bool | None = None) -> bool:
    if server_is_ready is None:
        server_is_ready = wait_for_server(retries=1, wt=0)

    if server_is_ready:
        logging.info('viewer startup: using server splash page')
        try:
            view_webpage(SPLASH_PAGE_URL)
            return True
        except Exception:
            logging.exception(
                'viewer startup: failed rendering server splash; '
                'falling back offline'
            )

    logging.warning('viewer startup: using offline splash fallback')
    try:
        view_webpage(_build_offline_splash_url())
    except Exception:
        logging.exception('viewer startup: failed rendering offline splash')
    return False


def _connect_browser_bus() -> Any:
    bus = pydbus.SessionBus()
    return bus.get('anthias.webview', '/Anthias')


def _ensure_browser_bus_ready() -> None:
    global browser_bus

    if browser_bus is not None:
        return

    logging.warning('viewer display: browser_bus missing; reconnecting')
    browser_bus = _connect_browser_bus()


def _log_startup_timeline_event(started_at: float, event: str) -> None:
    elapsed_seconds = monotonic() - started_at
    logging.info(
        'viewer startup timeline: t+%.3fs %s',
        elapsed_seconds,
        event,
    )


def _wait_for_subscriber_ready(
    timeout_seconds: float = SUBSCRIBER_READY_WAIT_TIMEOUT_SECONDS,
    poll_interval_seconds: float = SUBSCRIBER_READY_POLL_INTERVAL_SECONDS,
) -> bool:
    if timeout_seconds <= 0:
        return False

    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        try:
            ready_value = r.get('viewer-subscriber-ready')
        except Exception as exc:
            logging.warning(
                'viewer startup: redis readiness probe failed: %s',
                exc,
            )
            return False

        if ready_value in (1, '1', b'1', True):
            logging.info('viewer startup: subscriber readiness confirmed')
            return True

        sleep(poll_interval_seconds)

    logging.warning(
        'viewer startup: subscriber not ready after %.1fs',
        timeout_seconds,
    )
    return False


def _setup_with_retries(
    startup_started_at: float,
    max_attempts: int = SETUP_RETRY_ATTEMPTS,
    delay_seconds: float = SETUP_RETRY_DELAY_SECONDS,
) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            setup()
            _log_startup_timeline_event(
                startup_started_at,
                f'setup-attempt-{attempt}-success',
            )
            return
        except Exception:
            logging.exception(
                'viewer startup: setup attempt %s/%s failed',
                attempt,
                max_attempts,
            )
            _log_startup_timeline_event(
                startup_started_at,
                f'setup-attempt-{attempt}-failed',
            )
            if attempt == max_attempts:
                raise
            sleep(delay_seconds)


def load_browser() -> None:
    global browser, browser_stdout_cursor
    logging.info('Loading browser...')

    browser = sh.Command('AnthiasWebview')(_bg=True, _err_to_out=True)
    browser_stdout_cursor = 0

    # Bound the wait so we don't hang the viewer indefinitely if
    # AnthiasWebview fails to register on D-Bus (missing binary, broken
    # library link, handshake-line drift, etc.). The string here must
    # match `qInfo() << "Anthias service start"` in webview/src/main.cpp.
    deadline = monotonic() + BROWSER_STARTUP_TIMEOUT_SECONDS
    while monotonic() < deadline:
        _drain_browser_stdout()
        if BROWSER_HANDSHAKE_LINE in browser.process.stdout.decode('utf-8'):
            return
        if not browser.is_alive():
            raise RuntimeError(
                'AnthiasWebview exited before emitting D-Bus handshake; '
                'stdout: '
                + browser.process.stdout.decode('utf-8', errors='replace')
            )
        sleep(1)

    raise TimeoutError(
        f'AnthiasWebview did not emit "{BROWSER_HANDSHAKE_LINE}" within '
        f'{BROWSER_STARTUP_TIMEOUT_SECONDS}s'
    )


def view_webpage(uri: str) -> None:
    global current_browser_url, browser_bus

    record_render_command(
        r,
        media_type='webpage',
        uri=uri,
        transport='dbus.loadPage',
    )

    if browser is None or not browser.is_alive():
        load_browser()
        # New browser process => stale proxy must be re-resolved.
        browser_bus = None

    _ensure_browser_bus_ready()

    if current_browser_url != uri:
        try:
            browser_bus.loadPage(uri)
        except Exception:
            logging.exception(
                'viewer display: loadPage failed, reconnecting browser bus'
            )
            browser_bus = None
            _ensure_browser_bus_ready()
            try:
                browser_bus.loadPage(uri)
            except Exception as exc:
                record_render_result(
                    r,
                    media_type='webpage',
                    uri=uri,
                    status='error',
                    detail=str(exc),
                )
                raise
        current_browser_url = uri
        record_render_result(
            r,
            media_type='webpage',
            uri=uri,
            status='success',
        )
    else:
        record_render_result(
            r,
            media_type='webpage',
            uri=uri,
            status='noop_already_current',
        )
    if _display_debug_enabled():
        _drain_browser_stdout()
    logging.info('Current url is {0}'.format(current_browser_url))


def view_image(uri: str) -> None:
    global current_browser_url, browser_bus

    record_render_command(
        r,
        media_type='image',
        uri=uri,
        transport='dbus.loadImage',
    )

    if browser is None or not browser.is_alive():
        load_browser()
        # New browser process => stale proxy must be re-resolved.
        browser_bus = None

    _ensure_browser_bus_ready()

    if current_browser_url != uri:
        try:
            browser_bus.loadImage(uri)
        except Exception:
            logging.exception(
                'viewer display: loadImage failed, reconnecting browser bus'
            )
            browser_bus = None
            _ensure_browser_bus_ready()
            try:
                browser_bus.loadImage(uri)
            except Exception as exc:
                record_render_result(
                    r,
                    media_type='image',
                    uri=uri,
                    status='error',
                    detail=str(exc),
                )
                raise
        current_browser_url = uri
        record_render_result(
            r,
            media_type='image',
            uri=uri,
            status='success',
        )
    else:
        record_render_result(
            r,
            media_type='image',
            uri=uri,
            status='noop_already_current',
        )
    if _display_debug_enabled():
        _drain_browser_stdout()
    logging.info('Current url is {0}'.format(current_browser_url))

    if string_to_bool(getenv('WEBVIEW_DEBUG', '0')):
        logging.info(browser.process.stdout)


def view_video(uri: str, duration: int | str) -> None:
    logging.debug('Displaying video %s for %s ', uri, duration)
    record_render_command(
        r,
        media_type='video',
        uri=uri,
        transport='mediaplayer.play',
    )
    media_player = MediaPlayerProxy.get_instance()

    try:
        media_player.set_asset(uri, duration)
        media_player.play()

        view_image('null')

        skip_event = get_skip_event()
        skip_event.clear()
        if skip_event.wait(timeout=int(duration)):
            logging.info('Skip detected during video playback, stopping video')
            media_player.stop()
        else:
            pass

        record_render_result(
            r,
            media_type='video',
            uri=uri,
            status='success',
        )
    except sh.ErrorReturnCode_1:
        logging.info(
            'Resource URI is not correct, remote host is not responding or '
            'request was rejected.'
        )
        record_render_result(
            r,
            media_type='video',
            uri=uri,
            status='error',
            detail='sh.ErrorReturnCode_1',
        )
    except Exception as exc:
        record_render_result(
            r,
            media_type='video',
            uri=uri,
            status='error',
            detail=str(exc),
        )
        raise

    media_player.stop()


def load_settings() -> None:
    """
    Load settings and set the log level.
    """
    settings.load()
    logging.getLogger().setLevel(
        logging.DEBUG if settings['debug_logging'] else logging.INFO
    )


def asset_loop(scheduler: Any) -> None:
    asset = scheduler.get_next_asset()

    if asset is None:
        logging.info(
            'Playlist is empty. Sleeping for %s seconds', EMPTY_PL_DELAY
        )
        _show_splash_with_fallback()
        skip_event = get_skip_event()
        skip_event.clear()
        if skip_event.wait(timeout=EMPTY_PL_DELAY):
            # Skip was triggered, continue immediately to next iteration
            logging.info(
                'Skip detected during empty playlist wait, continuing'
            )
        else:
            # Duration elapsed normally, continue to next iteration
            pass

    elif path.isfile(asset['uri']) or (
        not url_fails(asset['uri']) or asset['skip_asset_check']
    ):
        name, mime, uri = asset['name'], asset['mimetype'], asset['uri']
        logging.info('Showing asset %s (%s)', name, mime)
        logging.debug('Asset URI %s', uri)
        watchdog()

        if 'image' in mime:
            view_image(uri)
        elif 'web' in mime:
            view_webpage(uri)
        elif 'video' in mime or 'streaming' in mime:
            view_video(uri, asset['duration'])
        else:
            logging.error('Unknown MimeType %s', mime)

        if 'image' in mime or 'web' in mime:
            duration = int(asset['duration'])
            logging.info('Sleeping for %s', duration)
            skip_event = get_skip_event()
            skip_event.clear()
            if skip_event.wait(timeout=duration):
                # Skip was triggered, continue immediately to next iteration
                logging.info('Skip detected, moving to next asset immediately')
            else:
                # Duration elapsed normally, continue to next asset
                pass

    else:
        logging.info(
            'Asset %s at %s is not available, skipping.',
            asset['name'],
            asset['uri'],
        )
        skip_event = get_skip_event()
        skip_event.clear()
        if skip_event.wait(timeout=0.5):
            # Skip was triggered, continue immediately to next iteration
            logging.info(
                'Skip detected during asset unavailability wait, continuing'
            )
        else:
            # Duration elapsed normally, continue to next iteration
            pass


def setup() -> None:
    global HOME, browser_bus
    HOME = getenv('HOME')
    if not HOME:
        logging.error('No HOME variable')

        # Alternatively, we can raise an Exception using a custom message,
        # or we can create a new class that extends Exception.
        sys.exit(1)

    # Skip event is now handled via threading instead of signals
    signal(SIGALRM, sigalrm)

    load_settings()
    _log_display_runtime_diagnostics()
    load_browser()

    browser_bus = _connect_browser_bus()


def wait_for_node_ip(seconds: int) -> None:
    for _ in range(seconds):
        try:
            get_node_ip()
            break
        except Exception:
            sleep(1)


def start_loop() -> None:
    global loop_is_stopped

    logging.debug('Entering infinite loop.')
    while True:
        if loop_is_stopped:
            sleep(0.1)
            continue

        asset_loop(scheduler)


def main() -> None:
    global scheduler

    startup_started_at = monotonic()
    _log_startup_timeline_event(startup_started_at, 'startup-begin')

    _setup_with_retries(startup_started_at)
    _log_startup_timeline_event(startup_started_at, 'setup-complete')

    subscriber = ViewerSubscriber(r, commands)
    subscriber.daemon = True
    subscriber.start()
    _log_startup_timeline_event(
        startup_started_at,
        'subscriber-thread-started',
    )

    subscriber_ready = _wait_for_subscriber_ready()
    _log_startup_timeline_event(
        startup_started_at,
        f'subscriber-ready={subscriber_ready}',
    )

    # Render splash through the helper so fallback exceptions are contained
    # and consistently logged.
    _show_splash_with_fallback(False)
    _log_startup_timeline_event(startup_started_at, 'offline-splash-rendered')

    server_is_ready = wait_for_server(SERVER_WAIT_TIMEOUT)
    _log_startup_timeline_event(
        startup_started_at,
        f'server-ready={server_is_ready}',
    )
    _show_splash_with_fallback(server_is_ready)
    _log_startup_timeline_event(
        startup_started_at,
        'splash-selection-complete',
    )

    scheduler = Scheduler()
    _log_startup_timeline_event(startup_started_at, 'scheduler-initialized')

    if settings['show_splash']:
        if is_balena_app():
            for attempt in Retrying(
                stop=stop_after_attempt(MAX_BALENA_IP_RETRIES),
                wait=wait_fixed(BALENA_IP_RETRY_DELAY),
            ):
                with attempt:
                    get_balena_device_info()

        _show_splash_with_fallback()
        sleep(SPLASH_DELAY)
        _log_startup_timeline_event(
            startup_started_at,
            'show-splash-delay-complete',
        )

    # Historically we switched to a very dark standby image here, which can
    # be perceived as a blank screen on some displays. Keep the splash visible
    # by default; allow opting back in via env for legacy behavior.
    if string_to_bool(getenv('SHOW_STARTUP_STANDBY', '0')):
        view_image(STANDBY_SCREEN)
        sleep(0.5)
        _log_startup_timeline_event(
            startup_started_at,
            'startup-standby-rendered',
        )

    _log_startup_timeline_event(startup_started_at, 'start-loop')

    start_loop()
