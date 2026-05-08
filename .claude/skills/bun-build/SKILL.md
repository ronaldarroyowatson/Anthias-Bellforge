# bun-build Skill

Run a production frontend build and verify output artifacts.

## Usage

Tell the agent: "Build the frontend" or "Rebuild JS and CSS assets".

## Steps

1. Install dependencies:
   ```bash
   bun install
   ```

2. Production build (JS + CSS):
   ```bash
   bun run build
   ```

3. Verify output artifacts exist:
   ```bash
   # Should produce:
   # static/dist/js/anthias.js
   # static/dist/css/anthias.css
   ls static/dist/js/anthias.js static/dist/css/anthias.css
   ```

4. For watch/dev mode:
   ```bash
   bun run dev
   ```

## Build Configuration

- JS entry: `static/src/index.tsx`
- JS output: `static/dist/js/anthias.js`
- CSS entry: `static/sass/anthias.scss`
- CSS output: `static/dist/css/anthias.css`
- Production JS sets: `process.env.ENVIRONMENT = "production"`
- Target: browser (ES2020)

## Notes

- `static/dist/` is git-ignored and served by WhiteNoise in production.
- Inside Docker dev: `docker compose -f docker-compose.dev.yml exec anthias-server bun run dev`
