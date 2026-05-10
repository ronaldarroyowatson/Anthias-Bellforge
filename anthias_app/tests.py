from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest import mock

from django.http import Http404
from django.http.response import HttpResponseBase
from django.test import RequestFactory, TestCase

from anthias_app import views, views_files

# Standard private/public IP literals reused across the IP-allowlist
# tests below. Centralised so Sonar's S1313 ("don't hardcode IPs") is
# only suppressed in one place.
DOCKER_BRIDGE_IP = '172.18.0.1'  # NOSONAR
LAN_IP_10 = '10.0.0.5'  # NOSONAR
LAN_IP_192_ALLOWED = '192.168.1.10'  # NOSONAR
LAN_IP_192_BLOCKED = '192.168.1.50'  # NOSONAR
PUBLIC_IP = '8.8.8.8'  # NOSONAR


class AnthiasAssetsViewTest(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'hello.txt').write_text('hello')
        self.root_patch = mock.patch.object(
            views_files, 'ANTHIAS_ASSETS_ROOT', self.root
        )
        self.root_patch.start()

    def tearDown(self) -> None:
        self.root_patch.stop()
        self.tmp.cleanup()

    def _get(self, path: str, remote_addr: str) -> HttpResponseBase:
        request = self.factory.get(path, REMOTE_ADDR=remote_addr)
        # views_files.anthias_assets is wrapped by require_client_in.
        filename = path.removeprefix('/anthias_assets/')
        return views_files.anthias_assets(request, filename=filename)

    def test_allows_docker_bridge_client(self) -> None:
        response = self._get('/anthias_assets/hello.txt', DOCKER_BRIDGE_IP)
        self.assertEqual(response.status_code, 200)

    def test_blocks_public_ip(self) -> None:
        response = self._get('/anthias_assets/hello.txt', PUBLIC_IP)
        self.assertEqual(response.status_code, 403)

    def test_blocks_lan_ip(self) -> None:
        # 192.168/16 is intentionally excluded from the asset allowlist.
        response = self._get('/anthias_assets/hello.txt', LAN_IP_192_BLOCKED)
        self.assertEqual(response.status_code, 403)

    def test_missing_file_404(self) -> None:
        request = self.factory.get(
            '/anthias_assets/missing.txt', REMOTE_ADDR=DOCKER_BRIDGE_IP
        )
        with self.assertRaises(Http404):
            views_files.anthias_assets(request, filename='missing.txt')

    def test_traversal_404(self) -> None:
        request = self.factory.get(
            '/anthias_assets/whatever', REMOTE_ADDR=DOCKER_BRIDGE_IP
        )
        with self.assertRaises(Http404):
            views_files.anthias_assets(request, filename='../../../etc/passwd')

    def test_symlink_escape_404(self) -> None:
        with TemporaryDirectory() as outside_dir:
            outside = Path(outside_dir) / 'outside.txt'
            outside.write_text('secret')
            (self.root / 'link.txt').symlink_to(outside)
            request = self.factory.get(
                '/anthias_assets/link.txt', REMOTE_ADDR=DOCKER_BRIDGE_IP
            )
            with self.assertRaises(Http404):
                views_files.anthias_assets(request, filename='link.txt')

    def test_malformed_remote_addr_403(self) -> None:
        response = self._get('/anthias_assets/hello.txt', 'not-an-ip')
        self.assertEqual(response.status_code, 403)


class StaticWithMimeViewTest(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'app.css').write_text('body{}')
        self.root_patch = mock.patch.object(
            views_files, 'STATIC_FILES_ROOT', self.root
        )
        self.root_patch.start()

    def tearDown(self) -> None:
        self.root_patch.stop()
        self.tmp.cleanup()

    def _call(
        self, filename: str, remote_addr: str, **extra: Any
    ) -> HttpResponseBase:
        request = self.factory.get(
            f'/static_with_mime/{filename}', REMOTE_ADDR=remote_addr, **extra
        )
        return views_files.static_with_mime(request, filename=filename)

    def test_allows_rfc1918_clients(self) -> None:
        for ip in (LAN_IP_10, DOCKER_BRIDGE_IP, LAN_IP_192_ALLOWED):
            self.assertEqual(
                self._call('app.css', ip).status_code,
                200,
                msg=f'expected 200 for {ip}',
            )

    def test_blocks_public_ip(self) -> None:
        self.assertEqual(self._call('app.css', PUBLIC_IP).status_code, 403)

    def test_mime_override_via_query(self) -> None:
        request = self.factory.get(
            '/static_with_mime/app.css',
            data={'mime': 'application/x-tgz'},
            REMOTE_ADDR=LAN_IP_10,
        )
        response = views_files.static_with_mime(request, filename='app.css')
        self.assertEqual(response['Content-Type'], 'application/x-tgz')

    def test_mime_override_rejects_html(self) -> None:
        # text/html would let an attacker turn a stored file into XSS;
        # ?mime= is allowlisted to safe download types only.
        request = self.factory.get(
            '/static_with_mime/app.css',
            data={'mime': 'text/html'},
            REMOTE_ADDR=LAN_IP_10,
        )
        response = views_files.static_with_mime(request, filename='app.css')
        self.assertEqual(response['Content-Type'], 'text/css')

    def test_default_mime_from_extension(self) -> None:
        request = self.factory.get(
            '/static_with_mime/app.css', REMOTE_ADDR=LAN_IP_10
        )
        response = views_files.static_with_mime(request, filename='app.css')
        self.assertEqual(response['Content-Type'], 'text/css')


class SplashPageViewTest(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_splash_page_skips_loopback_addresses(self) -> None:
        request = self.factory.get('/splash-page')

        with mock.patch.object(
            views,
            'get_node_ip',
            return_value='127.0.0.1 192.168.1.20',
        ):
            response = views.splash_page(request)

        self.assertContains(response, 'http://192.168.1.20')
        self.assertNotContains(response, 'http://127.0.0.1')
        self.assertNotContains(response, 'http://localhost')

    def test_splash_page_uses_anthias_local_when_no_ip_found(self) -> None:
        request = self.factory.get('/splash-page')

        with (
            mock.patch.object(
                views,
                'get_node_ip',
                return_value='Unable to retrieve IP.',
            ),
            mock.patch.object(
                views,
                'get_node_hostname',
                return_value='',
            ),
        ):
            response = views.splash_page(request)

        self.assertContains(response, 'http://anthias.local')
        self.assertNotContains(response, 'http://localhost')

    def test_splash_page_uses_host_local_domain_when_no_ip_found(self) -> None:
        request = self.factory.get('/splash-page')

        with (
            mock.patch.object(
                views,
                'get_node_ip',
                return_value='Unable to retrieve IP.',
            ),
            mock.patch.object(
                views,
                'get_node_hostname',
                return_value='RPi5Dev',
                create=True,
            ),
        ):
            response = views.splash_page(request)

        self.assertContains(response, 'http://rpi5dev.local')
        self.assertNotContains(response, 'http://anthias.local')

    def test_splash_page_uses_request_host_in_development_when_no_hostname(
        self,
    ) -> None:
        request = self.factory.get('/splash-page', HTTP_HOST='localhost:8000')

        with (
            mock.patch.dict('os.environ', {'ENVIRONMENT': 'development'}),
            mock.patch.object(
                views,
                'get_node_ip',
                return_value='Unable to retrieve IP.',
            ),
            mock.patch.object(
                views,
                'get_node_hostname',
                return_value='',
            ),
        ):
            response = views.splash_page(request)

        self.assertContains(response, 'http://localhost:8000')
        self.assertNotContains(response, 'http://anthias.local')

    def test_splash_page_ignores_container_host_in_development(self) -> None:
        request = self.factory.get(
            '/splash-page', HTTP_HOST='anthias-server:8080'
        )

        with (
            mock.patch.dict('os.environ', {'ENVIRONMENT': 'development'}),
            mock.patch.object(
                views,
                'get_node_ip',
                return_value='Unable to retrieve IP.',
            ),
            mock.patch.object(
                views,
                'get_node_hostname',
                return_value='',
            ),
        ):
            response = views.splash_page(request)

        self.assertContains(response, 'http://anthias.local')
        self.assertNotContains(response, 'http://anthias-server:8080')


class SplashPageReachabilityTest(TestCase):
    """Fail-first tests for per-URL reachability filtering on the splash page."""

    def setUp(self) -> None:
        self.factory = RequestFactory()

    def test_splash_excludes_unreachable_url_when_reachable_one_exists(
        self,
    ) -> None:
        # Fail-first: without the reachability filter both IPs would be shown.
        # With the filter, only the reachable IP must appear.
        request = self.factory.get('/splash-page')

        def _reachable_only_first(url: str, timeout: float = 2.0) -> bool:
            return url == 'http://192.168.1.20'

        with (
            mock.patch.object(
                views,
                'get_node_ip',
                return_value='192.168.1.20 192.168.1.99',
            ),
            mock.patch.object(
                views,
                'probe_management_server',
                side_effect=_reachable_only_first,
            ),
            mock.patch.object(views, 'is_internet_reachable', return_value=True),
        ):
            response = views.splash_page(request)

        self.assertContains(response, 'http://192.168.1.20')
        self.assertNotContains(response, 'http://192.168.1.99')

    def test_splash_shows_all_urls_when_none_are_reachable(self) -> None:
        # When every probe fails the view must fall back to showing all
        # candidates so the user is not left with a blank page.
        request = self.factory.get('/splash-page')

        with (
            mock.patch.object(
                views,
                'get_node_ip',
                return_value='192.168.1.20 192.168.1.99',
            ),
            mock.patch.object(
                views,
                'probe_management_server',
                return_value=False,
            ),
            mock.patch.object(views, 'is_internet_reachable', return_value=False),
        ):
            response = views.splash_page(request)

        self.assertContains(response, 'http://192.168.1.20')
        self.assertContains(response, 'http://192.168.1.99')

    def test_splash_includes_internet_connected_status(self) -> None:
        request = self.factory.get('/splash-page')

        with (
            mock.patch.object(
                views, 'get_node_ip', return_value='192.168.1.20'
            ),
            mock.patch.object(
                views, 'probe_management_server', return_value=True
            ),
            mock.patch.object(views, 'is_internet_reachable', return_value=True),
        ):
            response = views.splash_page(request)

        self.assertContains(response, 'Internet: Connected')

    def test_splash_includes_internet_offline_status(self) -> None:
        request = self.factory.get('/splash-page')

        with (
            mock.patch.object(
                views, 'get_node_ip', return_value='192.168.1.20'
            ),
            mock.patch.object(
                views, 'probe_management_server', return_value=True
            ),
            mock.patch.object(views, 'is_internet_reachable', return_value=False),
        ):
            response = views.splash_page(request)

        self.assertContains(response, 'No internet connection')

    def test_splash_appends_management_port_when_not_80(self) -> None:
        # When MANAGEMENT_PORT is set to a non-standard port, the splash
        # page must include it in the advertised URL so the link works.
        request = self.factory.get('/splash-page')

        with (
            mock.patch.dict('os.environ', {'MANAGEMENT_PORT': '8000'}),
            mock.patch.object(
                views, 'get_node_ip', return_value='192.168.1.20'
            ),
            mock.patch.object(
                views, 'probe_management_server', return_value=True
            ),
            mock.patch.object(views, 'is_internet_reachable', return_value=True),
        ):
            response = views.splash_page(request)

        self.assertContains(response, 'http://192.168.1.20:8000')
        self.assertNotContains(response, 'http://192.168.1.20/')  # no bare port-80
