# -*- coding: utf-8 -*-
# Tests viewer utility helpers used by startup display sequencing.

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests


def _load_viewer_utils_module():
    utils_path = Path(__file__).resolve().parents[1] / 'viewer' / 'utils.py'
    spec = importlib.util.spec_from_file_location(
        'viewer_utils_under_test', utils_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError('Unable to load viewer/utils.py for tests')

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


utils = _load_viewer_utils_module()


class WaitForServerTest(unittest.TestCase):
    def test_wait_for_server_returns_false_when_retries_non_positive(
        self,
    ) -> None:
        with patch.object(utils.requests, 'get') as m_get:
            ready = utils.wait_for_server(retries=0, wt=0)

        self.assertFalse(ready)
        m_get.assert_not_called()

    def test_wait_for_server_uses_short_http_timeout(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None

        with patch.object(
            utils.requests, 'get', return_value=response
        ) as m_get:
            ready = utils.wait_for_server(retries=1, wt=0)

        self.assertTrue(ready)
        m_get.assert_called_once_with(
            f'http://{utils.LISTEN}:{utils.PORT}/splash-page',
            timeout=3,
        )

    def test_wait_for_server_returns_false_after_retries(self) -> None:
        with (
            patch.object(
                utils.requests,
                'get',
                side_effect=requests.exceptions.RequestException,
            ) as m_get,
            patch.object(utils, 'sleep') as m_sleep,
        ):
            ready = utils.wait_for_server(retries=3, wt=2)

        self.assertFalse(ready)
        self.assertEqual(m_get.call_count, 3)
        self.assertEqual(m_sleep.call_count, 2)

    def test_wait_for_server_logs_debug_for_each_failed_probe(self) -> None:
        with (
            patch.object(
                utils.requests,
                'get',
                side_effect=requests.exceptions.RequestException,
            ),
            patch.object(utils, 'sleep') as m_sleep,
            patch.object(utils.logging, 'debug') as m_log_debug,
        ):
            ready = utils.wait_for_server(retries=2, wt=1)

        self.assertFalse(ready)
        self.assertEqual(m_sleep.call_count, 1)
        self.assertEqual(m_log_debug.call_count, 2)


if __name__ == '__main__':
    unittest.main()
