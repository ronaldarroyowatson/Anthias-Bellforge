import uuid
from os import getenv, path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests
import yaml
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from anthias_app.models import Asset
from lib.github import is_up_to_date
from lib.utils import get_video_duration
from settings import settings


def _lookup_public_coordinates() -> tuple[str, str] | None:
    try:
        response = requests.get(
            'https://ipapi.co/json/',
            timeout=3,
            headers={'User-Agent': 'Anthias-DefaultAssets/1.0'},
        )
        response.raise_for_status()
        payload = response.json()
    except (
        requests.RequestException,
        ValueError,
        TypeError,
    ):
        return None

    latitude = str(payload.get('latitude', '')).strip()
    longitude = str(payload.get('longitude', '')).strip()
    if not latitude or not longitude:
        return None

    return latitude, longitude


def _localize_default_asset_uri(
    uri: str, coordinates: tuple[str, str] | None = None
) -> str:
    parsed_uri = urlparse(uri)
    if parsed_uri.netloc.lower() != 'weather.srly.io':
        return uri

    query_values = parse_qs(parsed_uri.query, keep_blank_values=True)
    if query_values.get('lat') and query_values.get('lng'):
        return uri

    if coordinates is None:
        coordinates = _lookup_public_coordinates()
    if coordinates is None:
        return uri

    latitude, longitude = coordinates
    query_values['lat'] = [latitude]
    query_values['lng'] = [longitude]

    localized_uri = parsed_uri._replace(
        query=urlencode(query_values, doseq=True)
    )
    return urlunparse(localized_uri)


def localize_existing_default_assets() -> int:
    coordinates = _lookup_public_coordinates()
    if coordinates is None:
        return 0

    updated_count = 0
    default_weather_assets = Asset.objects.filter(
        uri__startswith='https://weather.srly.io'
    )

    for asset in default_weather_assets:
        localized_uri = _localize_default_asset_uri(asset.uri, coordinates)
        if localized_uri == asset.uri:
            continue

        asset.uri = localized_uri
        asset.save(update_fields=['uri'])
        updated_count += 1

    return updated_count


def template(
    request: HttpRequest,
    template_name: str,
    context: dict[str, Any],
) -> HttpResponse:
    """
    This is a helper function that is used to render a template
    with some global context. This is used to avoid having to
    repeat code in other views.
    """

    context['date_format'] = settings['date_format']
    context['default_duration'] = settings['default_duration']
    context['default_streaming_duration'] = settings[
        'default_streaming_duration'
    ]
    context['template_settings'] = {
        'imports': ['from lib.utils import template_handle_unicode'],
        'default_filters': ['template_handle_unicode'],
    }
    context['up_to_date'] = is_up_to_date()
    context['use_24_hour_clock'] = settings['use_24_hour_clock']

    return render(request, template_name, context)


def prepare_default_asset(**kwargs: Any) -> dict[str, Any] | None:
    if kwargs['mimetype'] not in ['image', 'video', 'webpage']:
        return None

    asset_id = 'default_{}'.format(uuid.uuid4().hex)
    if 'video' == kwargs['mimetype']:
        video_duration = get_video_duration(kwargs['uri'])
        if video_duration is None:
            raise ValueError(
                f'Could not determine duration of video {kwargs["uri"]!r}'
            )
        duration = int(video_duration.total_seconds())
    else:
        duration = kwargs['duration']

    return {
        'asset_id': asset_id,
        'duration': duration,
        'end_date': kwargs['end_date'],
        'is_enabled': True,
        'is_processing': 0,
        'mimetype': kwargs['mimetype'],
        'name': kwargs['name'],
        'nocache': 0,
        'play_order': 0,
        'skip_asset_check': 0,
        'start_date': kwargs['start_date'],
        'uri': kwargs['uri'],
    }


def add_default_assets() -> None:
    settings.load()

    datetime_now = timezone.now()
    default_asset_settings = {
        'start_date': datetime_now,
        'end_date': datetime_now.replace(year=datetime_now.year + 6),
        'duration': settings['default_duration'],
    }

    default_assets_yaml = path.join(
        getenv('HOME') or '',
        '.anthias/default_assets.yml',
    )

    with open(default_assets_yaml, 'r') as yaml_file:
        default_assets = yaml.safe_load(yaml_file).get('assets')
        coordinates = _lookup_public_coordinates()

        for default_asset in default_assets:
            default_asset_settings.update(
                {
                    'name': default_asset.get('name'),
                    'uri': _localize_default_asset_uri(
                        default_asset.get('uri') or '',
                        coordinates,
                    ),
                    'mimetype': default_asset.get('mimetype'),
                }
            )
            asset = prepare_default_asset(**default_asset_settings)

            if asset:
                Asset.objects.create(**asset)


def remove_default_assets() -> None:
    settings.load()

    for asset in Asset.objects.all():
        if asset.asset_id.startswith('default_'):
            asset.delete()
