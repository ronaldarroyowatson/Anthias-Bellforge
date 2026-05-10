import ipaddress
import os

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from lib.auth import authorized
from lib.utils import (
    connect_to_redis,
    get_node_hostname,
    get_node_ip,
    is_internet_reachable,
    probe_management_server,
)
from settings import settings

from .helpers import (
    template,
)

r = connect_to_redis()


def _is_container_internal_host(host: str) -> bool:
    hostname = host.split(':', 1)[0].strip().strip('[]').lower()
    if not hostname:
        return True

    return hostname in {
        'anthias-server',
        'anthias-viewer',
        'anthias-celery',
        'redis',
        '127.0.0.1',
        '0.0.0.0',
        '::1',
    }


@authorized
def react(request: HttpRequest) -> HttpResponse:
    return template(request, 'react.html', {})


@require_http_methods(['GET', 'POST'])
def login(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        username = request.POST.get('username') or ''
        password = request.POST.get('password') or ''

        auth = settings.auth
        if (
            auth is not None
            and hasattr(auth, '_check')
            and auth._check(username, password)
        ):
            # Store credentials in session
            request.session['auth_username'] = username
            request.session['auth_password'] = password

            return redirect(reverse('anthias_app:react'))
        else:
            messages.error(request, 'Invalid username or password')
            return template(
                request, 'login.html', {'next': request.GET.get('next', '/')}
            )

    return template(
        request, 'login.html', {'next': request.GET.get('next', '/')}
    )


@require_http_methods(['GET'])
def splash_page(request: HttpRequest) -> HttpResponse:
    # MANAGEMENT_PORT lets the dev compose override the default HTTP port
    # so advertised URLs include the non-standard port (e.g. :8000).
    try:
        management_port = int(os.getenv('MANAGEMENT_PORT', '80').strip())
    except ValueError:
        management_port = 80

    def _build_url(ip: str) -> str:
        if management_port == 80:
            return f'http://{ip}'
        return f'http://{ip}:{management_port}'

    ip_candidates: list[str] = []

    for ip_address in get_node_ip().split():
        try:
            ip_address_object = ipaddress.ip_address(ip_address)
        except ValueError:
            continue

        if ip_address_object.is_loopback or ip_address_object.is_unspecified:
            continue

        if isinstance(ip_address_object, ipaddress.IPv6Address):
            port_suffix = (
                '' if management_port == 80 else f':{management_port}'
            )
            ip_candidates.append(f'http://[{ip_address}]{port_suffix}')
        else:
            ip_candidates.append(_build_url(ip_address))

    if not ip_candidates:
        hostname = get_node_hostname().strip().lower()
        if hostname and hostname != 'anthias':
            ip_candidates.append(f'http://{hostname}.local')
        elif os.getenv('ENVIRONMENT') == 'development':
            host = request.get_host().strip()
            if (
                host
                and host != 'testserver'
                and not _is_container_internal_host(host)
            ):
                scheme = 'https' if request.is_secure() else 'http'
                ip_candidates.append(f'{scheme}://{host}')
            else:
                ip_candidates.append('http://anthias.local')
        else:
            ip_candidates.append('http://anthias.local')

    # Only advertise URLs the server can actually answer on. If every probe
    # fails (e.g. offline test environment) fall back to showing all
    # candidates so users are never left with a blank splash page.
    reachable = [url for url in ip_candidates if probe_management_server(url)]
    ip_addresses = reachable if reachable else ip_candidates

    internet_reachable = is_internet_reachable()

    return template(
        request,
        'splash-page.html',
        {
            'ip_addresses': ip_addresses,
            'internet_reachable': internet_reachable,
            'splash_logo_url': settings['splash_logo_url'],
        },
    )
