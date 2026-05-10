# -*- coding: utf-8 -*-
# Tests display-health evaluation in remote Pi display doctor automation.

import importlib.util
import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _load_remote_doctor_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / 'bin'
        / 'remote_pi_display_doctor.py'
    )
    spec = importlib.util.spec_from_file_location(
        'remote_pi_display_doctor_under_test',
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(
            'Unable to load bin/remote_pi_display_doctor.py for tests'
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


doctor = _load_remote_doctor_module()


class RemotePiDisplayDoctorTest(unittest.TestCase):
    def _snapshot_output(self, state_payload: dict[str, str]) -> str:
        command = json.dumps(
            {
                'event_type': 'render_command',
                'timestamp': datetime.now(UTC).isoformat(),
            }
        )
        result = json.dumps(
            {
                'event_type': 'render_result',
                'timestamp': datetime.now(UTC).isoformat(),
                'status': 'success',
            }
        )
        history = json.dumps({'event_type': 'render_result'})
        return (
            f'{command}\n'
            f'---\n'
            f'{result}\n'
            f'---\n'
            f'{history}\n'
            f'---\n'
            f'{json.dumps(state_payload)}\n'
            f'---\n'
            f'{state_payload["timestamp"]}\n'
        )

    def test_display_health_is_ok_when_state_is_fresh_and_success(
        self,
    ) -> None:
        state_payload = {
            'event_type': 'display_state',
            'timestamp': datetime.now(UTC).isoformat(),
            'media_type': 'webpage',
            'uri': 'http://example.local/splash-page',
            'render_status': 'success',
        }

        result = doctor._evaluate_display_health(
            self._snapshot_output(state_payload)
        )

        self.assertEqual(result['ok'], True)

    def test_display_health_fails_when_state_is_stale(self) -> None:
        stale_timestamp = (
            datetime.now(UTC) - timedelta(seconds=120)
        ).isoformat()
        state_payload = {
            'event_type': 'display_state',
            'timestamp': stale_timestamp,
            'media_type': 'webpage',
            'uri': 'http://example.local/splash-page',
            'render_status': 'success',
        }

        result = doctor._evaluate_display_health(
            self._snapshot_output(state_payload)
        )

        self.assertEqual(result['ok'], False)
        self.assertEqual(result['reason'], 'viewer.display.state is stale')

    def test_display_health_fails_when_state_reports_error(self) -> None:
        state_payload = {
            'event_type': 'display_state',
            'timestamp': datetime.now(UTC).isoformat(),
            'media_type': 'webpage',
            'uri': 'http://example.local/splash-page',
            'render_status': 'error',
        }

        result = doctor._evaluate_display_health(
            self._snapshot_output(state_payload)
        )

        self.assertEqual(result['ok'], False)
        self.assertEqual(
            result['reason'],
            'viewer.display.state reports render error',
        )

    def test_compose_up_script_exports_my_ip_before_compose_start(
        self,
    ) -> None:
        script = doctor._remote_compose_up_script(
            repo_dir='~/Anthias-Bellforge',
            rebuild=False,
        )

        self.assertIn('export MY_IP', script)
        self.assertIn('hostname -I', script)
        self.assertIn('ip route get 1.1.1.1', script)
        self.assertIn(
            'docker compose -f docker-compose.dev.yml -f docker-compose.viewer.yml up -d',
            script,
        )


if __name__ == '__main__':
    unittest.main()
