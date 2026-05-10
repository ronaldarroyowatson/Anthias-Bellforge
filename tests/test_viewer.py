#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Tests viewer startup and display-pipeline behavior.

import logging
import os
import sys
import unittest
from time import sleep
from typing import Any
from unittest import mock
from urllib.parse import unquote

sys.modules.setdefault('pydbus', mock.Mock())

import viewer
from viewer.scheduling import Scheduler

logging.disable(logging.CRITICAL)


class ViewerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.original_splash_delay = viewer.SPLASH_DELAY
        viewer.SPLASH_DELAY = 0

        self.u = viewer

        self.m_scheduler = mock.Mock(name='m_scheduler')
        self.p_scheduler = mock.patch.object(
            self.u, 'Scheduler', self.m_scheduler
        )

        self.m_cmd = mock.Mock(name='m_cmd')
        self.p_cmd = mock.patch.object(self.u.sh, 'Command', self.m_cmd)

        self.m_killall = mock.Mock(name='killall')
        self.p_killall = mock.patch.object(
            self.u.sh, 'killall', self.m_killall
        )

        self.m_reload = mock.Mock(name='reload')
        self.p_reload = mock.patch.object(
            self.u, 'load_settings', self.m_reload
        )

        self.m_sleep = mock.Mock(name='sleep')
        self.p_sleep = mock.patch.object(self.u, 'sleep', self.m_sleep)

        self.m_loadb = mock.Mock(name='load_browser')
        self.p_loadb = mock.patch.object(self.u, 'load_browser', self.m_loadb)

    def tearDown(self) -> None:
        self.u.SPLASH_DELAY = self.original_splash_delay


def noop(*a: Any, **k: Any) -> None:
    return None


class TestEmptyPl(ViewerTestCase):
    @mock.patch('viewer.constants.SERVER_WAIT_TIMEOUT', 0)
    def test_empty(self) -> None:
        m_asset_list = mock.Mock()
        m_asset_list.return_value = ([], None)

        with mock.patch('viewer.scheduling.generate_asset_list', m_asset_list):
            setattr(self.u, 'scheduler', Scheduler())

            m_asset_list.assert_called_once()


class TestLoadBrowser(ViewerTestCase):
    @mock.patch('pydbus.SessionBus', mock.MagicMock())
    def test_setup(self) -> None:
        self.p_loadb.start()
        self.u.setup()
        self.p_loadb.stop()

    def _stub_browser_stdout_static(
        self,
        browser_proc: mock.Mock,
        value: bytes,
    ) -> None:
        """
        sh.RunningCommand.process.stdout is a @property that returns the
        latest accumulated buffer on each access. Use PropertyMock so
        the test exercises the same poll-and-decode pattern as the
        production loop. Static variant: every read returns the same
        bytes value, suitable for cases where the loop doesn't depend
        on stdout changing across iterations (early-exit, timeout).
        """
        type(browser_proc.process).stdout = mock.PropertyMock(
            return_value=value
        )

    def _stub_browser_stdout_chunks(
        self,
        browser_proc: mock.Mock,
        chunks: list[bytes],
    ) -> None:
        """As above, but advance through `chunks` across reads â€” for
        the success case where the handshake appears in a later poll."""
        type(browser_proc.process).stdout = mock.PropertyMock(
            side_effect=chunks
        )

    def test_load_browser(self) -> None:
        browser_proc = self.m_cmd.return_value.return_value
        # Two stdout reads: an empty buffer on the first poll, then the
        # handshake line appended on the second. Verifies that the
        # polling loop actually re-reads stdout each iteration.
        self._stub_browser_stdout_chunks(
            browser_proc,
            [b'starting up\n', b'starting up\nAnthias service start\n'],
        )
        browser_proc.is_alive.return_value = True
        self.p_cmd.start()
        self.p_sleep.start()
        try:
            self.u.load_browser()
        finally:
            self.p_sleep.stop()
            self.p_cmd.stop()
        self.m_cmd.assert_called_once_with('AnthiasWebview')

    def test_load_browser_raises_when_process_exits_before_handshake(
        self,
    ) -> None:
        browser_proc = self.m_cmd.return_value.return_value
        # The error message also reads stdout, so use the static stub
        # that returns the same value on every access rather than a
        # one-shot side_effect.
        self._stub_browser_stdout_static(browser_proc, b'')
        browser_proc.is_alive.return_value = False
        self.p_cmd.start()
        try:
            with self.assertRaises(RuntimeError):
                self.u.load_browser()
        finally:
            self.p_cmd.stop()

    def test_load_browser_times_out_when_handshake_never_arrives(
        self,
    ) -> None:
        browser_proc = self.m_cmd.return_value.return_value
        self._stub_browser_stdout_static(browser_proc, b'irrelevant noise')
        browser_proc.is_alive.return_value = True
        # Three monotonic() reads: deadline init, one loop iteration
        # below the deadline, one above it.
        monotonic_values = iter([0.0, 0.0, 100.0])
        self.p_cmd.start()
        self.p_sleep.start()
        try:
            with mock.patch.object(
                self.u,
                'monotonic',
                side_effect=lambda: next(monotonic_values),
            ):
                with self.assertRaises(TimeoutError):
                    self.u.load_browser()
        finally:
            self.p_sleep.stop()
            self.p_cmd.stop()


class TestWatchdog(ViewerTestCase):
    def test_watchdog_should_create_file_if_not_exists(self) -> None:
        try:
            os.remove(self.u.utils.WATCHDOG_PATH)
        except OSError:
            pass
        self.u.watchdog()
        self.assertEqual(os.path.exists(self.u.utils.WATCHDOG_PATH), True)

    def test_watchdog_should_update_mtime(self) -> None:
        # for watchdog file creation
        self.u.watchdog()
        mtime = os.path.getmtime(self.u.utils.WATCHDOG_PATH)

        # Python is too fast?
        sleep(0.01)

        self.u.watchdog()
        mtime2 = os.path.getmtime(self.u.utils.WATCHDOG_PATH)
        self.assertGreater(mtime2, mtime)


class TestStartupSplashFallback(ViewerTestCase):
    def test_main_uses_fallback_splash_when_server_unavailable(self) -> None:
        m_subscriber_instance = mock.Mock(name='subscriber_instance')
        m_subscriber = mock.Mock(return_value=m_subscriber_instance)

        with (
            mock.patch.object(self.u, 'setup', side_effect=noop),
            mock.patch.object(self.u, 'ViewerSubscriber', m_subscriber),
            mock.patch.object(self.u, 'view_webpage') as m_view_webpage,
            mock.patch.object(self.u, 'wait_for_server', return_value=False),
            mock.patch.object(self.u, 'Scheduler', return_value=mock.Mock()),
            mock.patch.object(self.u, 'start_loop', side_effect=noop),
            mock.patch.object(self.u, 'sleep', side_effect=noop),
            mock.patch.object(self.u, 'is_balena_app', return_value=False),
        ):
            original_show_splash = self.u.settings['show_splash']
            self.u.settings['show_splash'] = True
            try:
                self.u.main()
            finally:
                self.u.settings['show_splash'] = original_show_splash

        called_urls = [call.args[0] for call in m_view_webpage.call_args_list]
        self.assertTrue(called_urls)
        self.assertTrue(called_urls[0].startswith('data:text/html,'))
        self.assertNotIn(self.u.SPLASH_PAGE_URL, called_urls)

    def test_asset_loop_uses_fallback_splash_when_server_unavailable(
        self,
    ) -> None:
        m_scheduler = mock.Mock()
        m_scheduler.get_next_asset.return_value = None

        m_skip_event = mock.Mock()
        m_skip_event.wait.return_value = False

        with (
            mock.patch.object(self.u, 'wait_for_server', return_value=False),
            mock.patch.object(self.u, 'view_webpage') as m_view_webpage,
            mock.patch.object(
                self.u, 'get_skip_event', return_value=m_skip_event
            ),
        ):
            self.u.asset_loop(m_scheduler)

        self.assertEqual(m_view_webpage.call_count, 1)
        called_url = m_view_webpage.call_args.args[0]
        self.assertTrue(called_url.startswith('data:text/html,'))


class TestDisplayPipelineRouting(ViewerTestCase):
    def test_asset_loop_logs_unknown_mimetype_without_forcing_video(
        self,
    ) -> None:
        m_scheduler = mock.Mock()
        m_scheduler.get_next_asset.return_value = {
            'name': 'UnknownAsset',
            'mimetype': 'application/json',
            'uri': 'http://example.com/asset.json',
            'duration': 5,
            'skip_asset_check': True,
        }

        m_skip_event = mock.Mock()
        m_skip_event.wait.return_value = False

        with (
            mock.patch.object(self.u.path, 'isfile', return_value=False),
            mock.patch.object(self.u, 'url_fails', return_value=False),
            mock.patch.object(self.u, 'view_video') as m_view_video,
            mock.patch.object(self.u, 'view_image') as m_view_image,
            mock.patch.object(self.u, 'view_webpage') as m_view_webpage,
            mock.patch.object(
                self.u, 'get_skip_event', return_value=m_skip_event
            ),
            mock.patch.object(self.u.logging, 'error') as m_log_error,
        ):
            self.u.asset_loop(m_scheduler)

        self.assertEqual(m_view_video.call_count, 0)
        self.assertEqual(m_view_image.call_count, 0)
        self.assertEqual(m_view_webpage.call_count, 0)
        m_log_error.assert_called_once_with(
            'Unknown MimeType %s', 'application/json'
        )

    def test_offline_splash_data_url_has_expected_prefix(self) -> None:
        with mock.patch.object(self.u, 'getenv', return_value='192.168.1.5'):
            offline_url = self.u._build_offline_splash_url()

        self.assertTrue(offline_url.startswith('data:text/html,'))

    def test_offline_splash_prefers_non_local_node_ip(self) -> None:
        with (
            mock.patch.object(self.u, 'getenv', return_value='localhost'),
            mock.patch.object(
                self.u, 'get_node_ip', return_value='192.168.2.180'
            ),
        ):
            offline_url = self.u._build_offline_splash_url()

        rendered_html = unquote(offline_url[len('data:text/html,') :])
        self.assertIn('http://192.168.2.180', rendered_html)

    def test_offline_splash_uses_first_non_local_candidate(self) -> None:
        with (
            mock.patch.object(self.u, 'getenv', return_value='localhost'),
            mock.patch.object(
                self.u,
                'get_node_ip',
                return_value='127.0.0.1 10.0.0.20 192.168.1.50',
            ),
        ):
            offline_url = self.u._build_offline_splash_url()

        rendered_html = unquote(offline_url[len('data:text/html,') :])
        self.assertIn('http://10.0.0.20', rendered_html)

    def test_offline_splash_uses_host_local_domain_when_ip_unavailable(
        self,
    ) -> None:
        with (
            mock.patch.object(self.u, 'getenv', return_value='localhost'),
            mock.patch.object(
                self.u,
                'get_node_ip',
                return_value='Unable to retrieve IP.',
            ),
            mock.patch.object(
                self.u,
                'get_node_hostname',
                return_value='RPi5Dev',
                create=True,
            ),
        ):
            offline_url = self.u._build_offline_splash_url()

        rendered_html = unquote(offline_url[len('data:text/html,') :])
        self.assertIn('http://rpi5dev.local', rendered_html)
        self.assertNotIn('http://anthias.local', rendered_html)

    def test_offline_splash_uses_anthias_local_when_hostname_unavailable(
        self,
    ) -> None:
        with (
            mock.patch.object(self.u, 'getenv', return_value='localhost'),
            mock.patch.object(
                self.u,
                'get_node_ip',
                return_value='Unable to retrieve IP.',
            ),
            mock.patch.object(
                self.u,
                'get_node_hostname',
                return_value='',
                create=True,
            ),
        ):
            offline_url = self.u._build_offline_splash_url()

        rendered_html = unquote(offline_url[len('data:text/html,') :])
        self.assertIn('http://anthias.local', rendered_html)


class TestViewerNavigationIdempotency(ViewerTestCase):
    def test_view_webpage_does_not_reload_same_url_value(self) -> None:
        original_browser = self.u.browser
        original_browser_bus = self.u.browser_bus
        original_current_browser_url = self.u.current_browser_url

        browser_mock = mock.Mock()
        browser_mock.is_alive.return_value = True

        self.u.browser = browser_mock
        browser_bus_mock = mock.Mock()
        self.u.browser_bus = browser_bus_mock

        expected_url = 'http://example.local/dashboard'
        self.u.current_browser_url = ''.join(expected_url)
        new_uri_instance = ''.join([c for c in expected_url])

        try:
            self.u.view_webpage(new_uri_instance)
        finally:
            self.u.browser = original_browser
            self.u.browser_bus = original_browser_bus
            self.u.current_browser_url = original_current_browser_url

        browser_bus_mock.loadPage.assert_not_called()

    def test_view_webpage_reloads_splash_page_even_if_url_matches(
        self,
    ) -> None:
        original_browser = self.u.browser
        original_browser_bus = self.u.browser_bus
        original_current_browser_url = self.u.current_browser_url

        browser_mock = mock.Mock()
        browser_mock.is_alive.return_value = True

        self.u.browser = browser_mock
        browser_bus_mock = mock.Mock()
        self.u.browser_bus = browser_bus_mock

        expected_url = 'http://anthias-server:8080/splash-page'
        self.u.current_browser_url = ''.join(expected_url)
        new_uri_instance = ''.join([c for c in expected_url])

        try:
            self.u.view_webpage(new_uri_instance)
        finally:
            self.u.browser = original_browser
            self.u.browser_bus = original_browser_bus
            self.u.current_browser_url = original_current_browser_url

        browser_bus_mock.loadPage.assert_called_once_with(new_uri_instance)

    def test_view_image_does_not_reload_same_url_value(self) -> None:
        original_browser = self.u.browser
        original_browser_bus = self.u.browser_bus
        original_current_browser_url = self.u.current_browser_url

        browser_mock = mock.Mock()
        browser_mock.is_alive.return_value = True

        self.u.browser = browser_mock
        browser_bus_mock = mock.Mock()
        self.u.browser_bus = browser_bus_mock

        expected_url = 'http://example.local/static/img/standby.png'
        self.u.current_browser_url = ''.join(expected_url)
        new_uri_instance = ''.join([c for c in expected_url])

        try:
            self.u.view_image(new_uri_instance)
        finally:
            self.u.browser = original_browser
            self.u.browser_bus = original_browser_bus
            self.u.current_browser_url = original_current_browser_url

        browser_bus_mock.loadImage.assert_not_called()


class TestStartupCommsDiagnostics(ViewerTestCase):
    def test_wait_for_subscriber_ready_returns_true_when_flag_present(
        self,
    ) -> None:
        with mock.patch.object(self.u, 'r') as redis_mock:
            redis_mock.get.return_value = b'1'

            ready = self.u._wait_for_subscriber_ready(
                timeout_seconds=1,
                poll_interval_seconds=0,
            )

        self.assertTrue(ready)

    def test_wait_for_subscriber_ready_returns_false_on_timeout(
        self,
    ) -> None:
        with (
            mock.patch.object(self.u, 'r') as redis_mock,
            mock.patch.object(self.u, 'sleep', side_effect=noop),
            mock.patch.object(self.u.logging, 'warning') as m_log_warning,
        ):
            redis_mock.get.return_value = b'0'
            monotonic_values = iter([0.0, 0.1, 0.2, 0.4])

            with mock.patch.object(
                self.u,
                'monotonic',
                side_effect=lambda: next(monotonic_values),
            ):
                ready = self.u._wait_for_subscriber_ready(
                    timeout_seconds=0.3,
                    poll_interval_seconds=0,
                )

        self.assertFalse(ready)
        m_log_warning.assert_called_once_with(
            'viewer startup: subscriber not ready after %.1fs',
            0.3,
        )

    def test_show_splash_with_fallback_returns_false_when_render_raises(
        self,
    ) -> None:
        with (
            mock.patch.object(self.u, 'wait_for_server', return_value=False),
            mock.patch.object(
                self.u,
                'view_webpage',
                side_effect=RuntimeError('render error'),
            ),
            mock.patch.object(self.u.logging, 'exception') as m_log_exception,
        ):
            showed_server_splash = self.u._show_splash_with_fallback()

        self.assertFalse(showed_server_splash)
        m_log_exception.assert_called_once_with(
            'viewer startup: failed rendering offline splash'
        )

    def test_main_emits_startup_timeline_markers(self) -> None:
        timeline_events: list[str] = []

        def capture_event(started_at: float, event: str) -> None:
            timeline_events.append(event)

        m_subscriber_instance = mock.Mock(name='subscriber_instance')
        m_subscriber = mock.Mock(return_value=m_subscriber_instance)

        with (
            mock.patch.object(self.u, 'setup', side_effect=noop),
            mock.patch.object(self.u, 'ViewerSubscriber', m_subscriber),
            mock.patch.object(
                self.u, '_wait_for_subscriber_ready', return_value=True
            ),
            mock.patch.object(self.u, 'wait_for_server', return_value=True),
            mock.patch.object(
                self.u, '_show_splash_with_fallback', return_value=True
            ),
            mock.patch.object(self.u, 'view_webpage', side_effect=noop),
            mock.patch.object(self.u, 'Scheduler', return_value=mock.Mock()),
            mock.patch.object(self.u, 'start_loop', side_effect=noop),
            mock.patch.object(self.u, 'sleep', side_effect=noop),
            mock.patch.object(self.u, 'is_balena_app', return_value=False),
            mock.patch.object(
                self.u,
                '_log_startup_timeline_event',
                side_effect=capture_event,
            ),
        ):
            original_show_splash = self.u.settings['show_splash']
            self.u.settings['show_splash'] = True
            try:
                self.u.main()
            finally:
                self.u.settings['show_splash'] = original_show_splash

        self.assertIn('startup-begin', timeline_events)
        self.assertIn('setup-complete', timeline_events)
        self.assertIn('subscriber-thread-started', timeline_events)
        self.assertIn('offline-splash-rendered', timeline_events)
        self.assertIn('scheduler-initialized', timeline_events)
        self.assertIn('start-loop', timeline_events)

    def test_setup_with_retries_succeeds_after_initial_failure(self) -> None:
        setup_effects = [RuntimeError('transient startup failure'), None]

        with (
            mock.patch.object(self.u, 'setup', side_effect=setup_effects),
            mock.patch.object(self.u, 'sleep', side_effect=noop) as m_sleep,
            mock.patch.object(
                self.u,
                '_log_startup_timeline_event',
                side_effect=noop,
            ),
        ):
            self.u._setup_with_retries(startup_started_at=0.0)

        m_sleep.assert_called_once_with(self.u.SETUP_RETRY_DELAY_SECONDS)

    def test_setup_with_retries_raises_after_max_attempts(self) -> None:
        with (
            mock.patch.object(
                self.u,
                'setup',
                side_effect=RuntimeError('persistent startup failure'),
            ),
            mock.patch.object(self.u, 'sleep', side_effect=noop),
            mock.patch.object(
                self.u,
                '_log_startup_timeline_event',
                side_effect=noop,
            ),
        ):
            with self.assertRaises(RuntimeError):
                self.u._setup_with_retries(
                    startup_started_at=0.0,
                    max_attempts=2,
                    delay_seconds=0,
                )


class TestBrowserBusRecovery(ViewerTestCase):
    def test_view_webpage_recovers_when_browser_bus_missing(self) -> None:
        original_browser = self.u.browser
        original_browser_bus = self.u.browser_bus
        original_current_browser_url = self.u.current_browser_url

        browser_mock = mock.Mock()
        browser_mock.is_alive.return_value = True
        recovered_browser_bus = mock.Mock()

        self.u.browser = browser_mock
        self.u.browser_bus = None
        self.u.current_browser_url = None

        with mock.patch.object(
            self.u,
            '_connect_browser_bus',
            return_value=recovered_browser_bus,
        ):
            try:
                self.u.view_webpage('http://example.local/splash-page')
            finally:
                self.u.browser = original_browser
                self.u.browser_bus = original_browser_bus
                self.u.current_browser_url = original_current_browser_url

        recovered_browser_bus.loadPage.assert_called_once_with(
            'http://example.local/splash-page'
        )

    def test_view_image_retries_once_after_bus_transport_error(self) -> None:
        original_browser = self.u.browser
        original_browser_bus = self.u.browser_bus
        original_current_browser_url = self.u.current_browser_url

        browser_mock = mock.Mock()
        browser_mock.is_alive.return_value = True

        first_bus = mock.Mock()
        first_bus.loadImage.side_effect = RuntimeError('transport down')
        second_bus = mock.Mock()

        self.u.browser = browser_mock
        self.u.browser_bus = first_bus
        self.u.current_browser_url = None

        with mock.patch.object(
            self.u,
            '_connect_browser_bus',
            return_value=second_bus,
        ):
            try:
                self.u.view_image(
                    'http://example.local/static/img/standby.png'
                )
            finally:
                self.u.browser = original_browser
                self.u.browser_bus = original_browser_bus
                self.u.current_browser_url = original_current_browser_url

        first_bus.loadImage.assert_called_once_with(
            'http://example.local/static/img/standby.png'
        )
        second_bus.loadImage.assert_called_once_with(
            'http://example.local/static/img/standby.png'
        )

    def test_main_uses_splash_helper_for_initial_render(self) -> None:
        m_subscriber_instance = mock.Mock(name='subscriber_instance')
        m_subscriber = mock.Mock(return_value=m_subscriber_instance)

        with (
            mock.patch.object(self.u, '_setup_with_retries', side_effect=noop),
            mock.patch.object(self.u, 'ViewerSubscriber', m_subscriber),
            mock.patch.object(
                self.u, '_wait_for_subscriber_ready', return_value=True
            ),
            mock.patch.object(self.u, 'wait_for_server', return_value=True),
            mock.patch.object(
                self.u,
                '_show_splash_with_fallback',
                return_value=True,
            ) as m_show_splash,
            mock.patch.object(self.u, 'view_webpage') as m_view_webpage,
            mock.patch.object(self.u, 'Scheduler', return_value=mock.Mock()),
            mock.patch.object(self.u, 'start_loop', side_effect=noop),
            mock.patch.object(self.u, 'sleep', side_effect=noop),
            mock.patch.object(self.u, 'is_balena_app', return_value=False),
            mock.patch.object(
                self.u,
                '_log_startup_timeline_event',
                side_effect=noop,
            ),
        ):
            original_show_splash = self.u.settings['show_splash']
            self.u.settings['show_splash'] = False
            try:
                self.u.main()
            finally:
                self.u.settings['show_splash'] = original_show_splash

        m_show_splash.assert_any_call(False)
        m_view_webpage.assert_not_called()


class TestRenderProbeTelemetry(ViewerTestCase):
    def test_view_webpage_records_command_and_success_result(self) -> None:
        original_browser = self.u.browser
        original_browser_bus = self.u.browser_bus
        original_current_browser_url = self.u.current_browser_url

        browser_mock = mock.Mock()
        browser_mock.is_alive.return_value = True
        browser_bus_mock = mock.Mock()

        self.u.browser = browser_mock
        self.u.browser_bus = browser_bus_mock
        self.u.current_browser_url = None

        with (
            mock.patch.object(
                self.u, 'record_render_command'
            ) as m_record_command,
            mock.patch.object(
                self.u, 'record_render_result'
            ) as m_record_result,
            mock.patch.object(
                self.u, 'record_display_state'
            ) as m_record_display_state,
        ):
            try:
                self.u.view_webpage('http://example.local/page')
            finally:
                self.u.browser = original_browser
                self.u.browser_bus = original_browser_bus
                self.u.current_browser_url = original_current_browser_url

        m_record_command.assert_called_once()
        m_record_result.assert_called_once_with(
            self.u.r,
            media_type='webpage',
            uri='http://example.local/page',
            status='success',
        )
        m_record_display_state.assert_called_once_with(
            self.u.r,
            media_type='webpage',
            uri='http://example.local/page',
            render_status='success',
        )

    def test_view_image_records_noop_when_url_is_already_current(self) -> None:
        original_browser = self.u.browser
        original_browser_bus = self.u.browser_bus
        original_current_browser_url = self.u.current_browser_url

        browser_mock = mock.Mock()
        browser_mock.is_alive.return_value = True
        browser_bus_mock = mock.Mock()

        self.u.browser = browser_mock
        self.u.browser_bus = browser_bus_mock
        self.u.current_browser_url = 'http://example.local/static/img/a.png'

        with (
            mock.patch.object(
                self.u, 'record_render_command'
            ) as m_record_command,
            mock.patch.object(
                self.u, 'record_render_result'
            ) as m_record_result,
            mock.patch.object(
                self.u, 'record_display_state'
            ) as m_record_display_state,
        ):
            try:
                self.u.view_image('http://example.local/static/img/a.png')
            finally:
                self.u.browser = original_browser
                self.u.browser_bus = original_browser_bus
                self.u.current_browser_url = original_current_browser_url

        m_record_command.assert_called_once()
        m_record_result.assert_called_once_with(
            self.u.r,
            media_type='image',
            uri='http://example.local/static/img/a.png',
            status='noop_already_current',
        )
        m_record_display_state.assert_called_once_with(
            self.u.r,
            media_type='image',
            uri='http://example.local/static/img/a.png',
            render_status='noop_already_current',
        )

    def test_view_video_records_failure_when_player_raises(self) -> None:
        media_player = mock.Mock()
        media_player.play.side_effect = RuntimeError('player failed')

        with (
            mock.patch.object(
                self.u.MediaPlayerProxy,
                'get_instance',
                return_value=media_player,
            ),
            mock.patch.object(
                self.u, 'record_render_command'
            ) as m_record_command,
            mock.patch.object(
                self.u, 'record_render_result'
            ) as m_record_result,
            mock.patch.object(self.u, 'view_image', side_effect=noop),
        ):
            with self.assertRaises(RuntimeError):
                self.u.view_video('http://example.local/video.mp4', 10)

        m_record_command.assert_called_once()
        m_record_result.assert_called_once()
        _, kwargs = m_record_result.call_args
        self.assertEqual(kwargs['status'], 'error')
