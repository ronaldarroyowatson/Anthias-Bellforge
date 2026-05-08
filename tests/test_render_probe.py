# -*- coding: utf-8 -*-
# Tests render probe telemetry persistence behavior.

import importlib.util
import json
import unittest
from pathlib import Path


def _load_render_probe_module():
    module_path = (
        Path(__file__).resolve().parents[1] / 'viewer' / 'render_probe.py'
    )
    spec = importlib.util.spec_from_file_location(
        'viewer_render_probe_under_test',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError('Unable to load viewer/render_probe.py for tests')

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


render_probe = _load_render_probe_module()


class FakeRedis:
    def __init__(self) -> None:
        self.key_values: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.expirations: dict[str, int] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.key_values[key] = value
        if ex is not None:
            self.expirations[key] = ex

    def lpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).insert(0, value)

    def ltrim(self, key: str, start: int, end: int) -> None:
        items = self.lists.get(key, [])
        self.lists[key] = items[start : end + 1]

    def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds


class RenderProbeTest(unittest.TestCase):
    def test_record_render_command_persists_last_command(self) -> None:
        redis_client = FakeRedis()

        event = render_probe.record_render_command(
            redis_connection=redis_client,
            media_type='webpage',
            uri='http://example.local/page',
            transport='dbus.loadPage',
        )

        persisted = json.loads(
            redis_client.key_values[render_probe.LAST_COMMAND_KEY]
        )
        self.assertEqual(persisted['event_type'], 'render_command')
        self.assertEqual(persisted['media_type'], 'webpage')
        self.assertEqual(persisted['uri'], 'http://example.local/page')
        self.assertEqual(persisted['transport'], 'dbus.loadPage')
        self.assertEqual(event['event_type'], 'render_command')

    def test_record_render_result_persists_last_result(self) -> None:
        redis_client = FakeRedis()

        event = render_probe.record_render_result(
            redis_connection=redis_client,
            media_type='image',
            uri='http://example.local/img.png',
            status='success',
        )

        persisted = json.loads(
            redis_client.key_values[render_probe.LAST_RESULT_KEY]
        )
        self.assertEqual(persisted['event_type'], 'render_result')
        self.assertEqual(persisted['media_type'], 'image')
        self.assertEqual(persisted['uri'], 'http://example.local/img.png')
        self.assertEqual(persisted['status'], 'success')
        self.assertEqual(event['event_type'], 'render_result')

    def test_history_is_trimmed_to_max_items(self) -> None:
        redis_client = FakeRedis()

        for idx in range(render_probe.MAX_HISTORY_ITEMS + 5):
            render_probe.record_render_result(
                redis_connection=redis_client,
                media_type='webpage',
                uri=f'http://example.local/{idx}',
                status='success',
            )

        self.assertEqual(
            len(redis_client.lists[render_probe.HISTORY_KEY]),
            render_probe.MAX_HISTORY_ITEMS,
        )


if __name__ == '__main__':
    unittest.main()
