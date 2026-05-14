# Bellforge tools.image_builder

This directory contains the Dockerfile generation and build context logic for Bellforge/Anthias.

- __main__.py: Entrypoint for Dockerfile generation and build orchestration
- utils.py: Context and template helpers
- constants.py: Build constants

Restored from upstream Anthias (Screenly, Inc.)

## Usage

Run via:

```bash
uv run python -m tools.image_builder --dockerfiles-only --build-target=x86
```

Or via bin/generate_dev_mode_dockerfiles.sh
