#!/usr/bin/env bash
# Run display pipeline regression tests in a Linux environment.
set -euo pipefail

VIEWER_RENDER_PROBE_DISABLE=1 ./manage.py test --noinput --exclude-tag=integration tests.test_viewer
VIEWER_RENDER_PROBE_DISABLE=1 ./manage.py test --noinput --exclude-tag=integration tests.test_viewer_utils
VIEWER_RENDER_PROBE_DISABLE=1 ./manage.py test --noinput --exclude-tag=integration tests.test_render_probe
