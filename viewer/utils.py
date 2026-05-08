import logging
import threading
from os import path, utime
from time import sleep
from types import FrameType
from typing import Any

import requests

from lib.errors import SigalrmError
from settings import LISTEN, PORT

WATCHDOG_PATH = '/tmp/anthias.watchdog'
SERVER_WAIT_REQUEST_TIMEOUT_SECONDS = 3


def sigalrm(signum: int, frame: FrameType | None) -> None:
    """
    Signal just throw an SigalrmError
    """
    raise SigalrmError('SigalrmError')


def get_skip_event() -> threading.Event:
    """
    Get the global skip event for instant asset switching.
    """
    from viewer.playback import skip_event

    return skip_event


def command_not_found(*args: Any, **kwargs: Any) -> None:
    logging.error('Command not found')


def watchdog() -> None:
    """Notify the watchdog file to be used with the watchdog-device."""
    try:
        if not path.isfile(WATCHDOG_PATH):
            open(WATCHDOG_PATH, 'w').close()
        else:
            utime(WATCHDOG_PATH, None)
    except OSError as exc:
        logging.warning('viewer watchdog update failed: %s', exc)


def wait_for_server(retries: int, wt: int = 1) -> bool:
    if retries <= 0:
        return False

    for attempt in range(retries):
        try:
            response = requests.get(
                f'http://{LISTEN}:{PORT}/splash-page',
                timeout=SERVER_WAIT_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as exc:
            logging.debug(
                'viewer startup: splash readiness probe %s/%s failed: %s',
                attempt + 1,
                retries,
                exc,
            )
            if attempt + 1 == retries:
                break
            sleep(wt)

    logging.warning(
        'viewer startup: splash endpoint did not become ready after %s '
        'attempt(s)',
        retries,
    )
    return False
