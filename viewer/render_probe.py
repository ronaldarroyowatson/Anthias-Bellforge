# -*- coding: utf-8 -*-
# Render probe helpers: persist display-command telemetry for debugging.

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

LAST_COMMAND_KEY = 'viewer.render.last_command'
LAST_RESULT_KEY = 'viewer.render.last_result'
HISTORY_KEY = 'viewer.render.history'
DISPLAY_STATE_KEY = 'viewer.display.state'
DISPLAY_HEARTBEAT_KEY = 'viewer.display.heartbeat'
KEY_TTL_SECONDS = 172800
MAX_HISTORY_ITEMS = 50


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _probe_enabled() -> bool:
    value = os.getenv('VIEWER_RENDER_PROBE_DISABLE', '0').strip().lower()
    return value not in {'1', 'true', 'yes', 'on'}


def _safe_redis_write(redis_connection: Any, key: str, payload: dict) -> None:
    if not _probe_enabled():
        return

    if redis_connection is None:
        return

    try:
        serialized = json.dumps(payload)
        redis_connection.set(key, serialized, ex=KEY_TTL_SECONDS)
        redis_connection.lpush(HISTORY_KEY, serialized)
        redis_connection.ltrim(HISTORY_KEY, 0, MAX_HISTORY_ITEMS - 1)
        redis_connection.expire(HISTORY_KEY, KEY_TTL_SECONDS)
    except Exception as exc:
        logging.warning('viewer render probe: redis write failed: %s', exc)


def record_render_command(
    redis_connection: Any,
    media_type: str,
    uri: str,
    transport: str,
) -> dict[str, str]:
    event = {
        'event_type': 'render_command',
        'timestamp': _utc_timestamp(),
        'media_type': media_type,
        'uri': uri,
        'transport': transport,
    }
    _safe_redis_write(redis_connection, LAST_COMMAND_KEY, event)
    return event


def record_render_result(
    redis_connection: Any,
    media_type: str,
    uri: str,
    status: str,
    detail: str | None = None,
) -> dict[str, str]:
    event = {
        'event_type': 'render_result',
        'timestamp': _utc_timestamp(),
        'media_type': media_type,
        'uri': uri,
        'status': status,
    }
    if detail:
        event['detail'] = detail

    _safe_redis_write(redis_connection, LAST_RESULT_KEY, event)
    return event


def record_display_state(
    redis_connection: Any,
    media_type: str,
    uri: str,
    render_status: str,
    detail: str | None = None,
) -> dict[str, str]:
    event = {
        'event_type': 'display_state',
        'timestamp': _utc_timestamp(),
        'media_type': media_type,
        'uri': uri,
        'render_status': render_status,
    }
    if detail:
        event['detail'] = detail

    if redis_connection is not None:
        if not _probe_enabled():
            return event

        try:
            serialized = json.dumps(event)
            redis_connection.set(
                DISPLAY_STATE_KEY, serialized, ex=KEY_TTL_SECONDS
            )
            redis_connection.set(
                DISPLAY_HEARTBEAT_KEY,
                event['timestamp'],
                ex=KEY_TTL_SECONDS,
            )
        except Exception as exc:
            logging.warning(
                'viewer render probe: display-state write failed: %s',
                exc,
            )

    return event
