#!/usr/bin/env bash
# Run display pipeline regression tests in a Linux environment.
set -euo pipefail

./manage.py test --noinput --exclude-tag=integration tests.test_viewer
./manage.py test --noinput --exclude-tag=integration tests.test_viewer_utils
./manage.py test --noinput --exclude-tag=integration tests.test_render_probe
