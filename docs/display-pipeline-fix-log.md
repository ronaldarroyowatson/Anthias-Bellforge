# Display Pipeline Fix Log

Purpose: running, append-only log of display-pipeline defects, diagnostics, and fixes.

## 2026-05-08

### ISSUE-001: Offline splash URL prefix mismatch
- Symptoms: fallback splash tests expected data:text/html URL prefix but runtime emitted data:text/html;charset=utf-8 prefix.
- Impact: fail-first tests for splash fallback semantics failed.
- Debug evidence: unit assertions on startup and empty-playlist fallback URL format.
- Fix: normalize fallback URL prefix to data:text/html for deterministic matching.
- Files:
  - viewer/__init__.py
  - tests/test_viewer.py
- Status: fixed in code, pending Linux CI/runtime verification.

### ISSUE-002: Unknown MIME types incorrectly routed to video player
- Symptoms: non-image, non-web assets were always routed to view_video().
- Root cause: boolean expression used "'video' or 'streaming' in mime" which is always truthy.
- Impact: unknown MIME content could trigger incorrect playback behavior and hide errors.
- Debug evidence: fail-first test ensures application/json logs Unknown MimeType and does not call view_video().
- Fix: change expression to explicit membership checks: 'video' in mime or 'streaming' in mime.
- Files:
  - viewer/__init__.py
  - tests/test_viewer.py
- Status: fixed in code, pending Linux CI/runtime verification.

### ISSUE-003: wait_for_server request could block too long per attempt
- Symptoms: readiness checks had retry loops but no explicit per-request timeout.
- Impact: startup gating could stall unpredictably when network stack partially hangs.
- Debug evidence: fail-first test requires timeout argument on requests.get().
- Fix: add explicit timeout=3 seconds for each splash readiness probe.
- Files:
  - viewer/utils.py
  - tests/test_viewer_utils.py
- Status: fixed in code, pending Linux CI/runtime verification.

### ISSUE-004: Startup splash path decision lacked explicit trace logs
- Symptoms: hard to determine from logs whether server splash or offline fallback was shown.
- Impact: slower triage for blank-screen startup regressions.
- Debug evidence: startup log stream lacked a clear branch marker.
- Fix: add explicit log lines for server splash path and offline fallback path selection.
- Files:
  - viewer/__init__.py
- Status: fixed in code, pending Linux runtime verification.

### ISSUE-005: URL identity comparison caused unnecessary reloads
- Symptoms: view_webpage and view_image compared URLs with object identity instead of value equality.
- Impact: equivalent URL strings built from different objects could still trigger loadPage/loadImage and introduce visual churn.
- Debug evidence: fail-first tests create equal-value distinct string instances and verify no reload calls.
- Fix: change URL comparison to value equality (current_browser_url != uri).
- Files:
  - viewer/__init__.py
  - tests/test_viewer.py
- Status: fixed in code, pending Linux runtime verification.

### OPEN-ENV-001: Local Windows host cannot execute viewer tests directly
- Symptoms: importing viewer module fails on Windows due missing SIGALRM in signal module.
- Impact: full test validation for viewer startup suite cannot run from current host shell.
- Workaround: run viewer tests in Linux test container or CI where SIGALRM is available.
- Status: open environment constraint.

### OPEN-ENV-002: Docker Linux engine unavailable on host
- Symptoms: docker compose test startup failed with missing dockerDesktopLinuxEngine pipe.
- Impact: cannot currently run Linux-container verification loop from this session.
- Workaround: start Docker Desktop Linux engine or run in CI/devcontainer with Docker engine access.
- Status: open environment constraint.

### ISSUE-006: Splash rendering path could crash on browser transport errors
- Symptoms: splash fallback helper would propagate webview/bus rendering exceptions.
- Impact: startup could crash before any visible fallback guidance appears, resulting in apparent blank display.
- Debug evidence: fail-first test forces view_webpage exception and verifies graceful false return path.
- Fix: guard server/offline splash rendering with exception logging and non-crashing fallback return.
- Files:
  - viewer/__init__.py
  - tests/test_viewer.py
- Status: fixed in code, pending Linux runtime verification.

### ISSUE-007: Startup lacked phase-timeline observability for blank-screen triage
- Symptoms: logs did not include clear startup phase timing markers.
- Impact: difficult to isolate whether blank periods happen during setup, subscriber start, server readiness, or scheduler init.
- Debug evidence: fail-first test validates phase markers emitted by main().
- Fix: add structured timeline markers using monotonic timestamps for key startup phases.
- Files:
  - viewer/__init__.py
  - tests/test_viewer.py
- Status: fixed in code, pending Linux runtime verification.

### ISSUE-008: Subscriber readiness race was not explicitly observed during startup
- Symptoms: startup proceeded without a direct readiness check for the command subscriber.
- Impact: redis/pubsub startup races were harder to detect and correlate with command-path behavior.
- Debug evidence: fail-first tests validate ready/timeout branches for readiness helper.
- Fix: add bounded readiness polling with explicit warning logs on timeout and redis probe failures.
- Files:
  - viewer/__init__.py
  - tests/test_viewer.py
- Status: fixed in code, pending Linux runtime verification.

### ISSUE-009: Linux-only display tests were not guaranteed as a dedicated CI gate
- Symptoms: display-pipeline tests depended on broad unit-test discovery and local host constraints prevented direct execution.
- Impact: regressions in startup/splash behavior could slip without an explicit Linux regression step.
- Debug evidence: OPEN-ENV-001 and OPEN-ENV-002 constraints observed on local Windows host.
- Fix: add bin/run_display_pipeline_tests.sh and call it explicitly in .github/workflows/test-runner.yml for python runs.
- Files:
  - bin/run_display_pipeline_tests.sh
  - .github/workflows/test-runner.yml
- Status: fixed in CI config, pending first CI run confirmation.

### ISSUE-010: Single-attempt setup could exit viewer on transient startup failures
- Symptoms: setup path attempted load once and raised on failure.
- Impact: transient webview/DRM timing failures could terminate viewer startup and leave display blank.
- Debug evidence: fail-first tests verify retry-success branch and terminal failure branch.
- Fix: add bounded setup retry loop with exception logging and timeline markers.
- Files:
  - viewer/__init__.py
  - tests/test_viewer.py
- Status: fixed in code, pending Linux runtime verification.

### ISSUE-011: Missing/stale D-Bus proxy could leave render path broken after reboot/transient restarts
- Symptoms: view_webpage/view_image assumed browser_bus remained valid and would raise when missing/stale.
- Impact: startup or first render could fail and viewer could appear blank despite signal.
- Debug evidence: fail-first tests cover browser_bus missing recovery, transport failure retry, and initial-splash helper routing.
- Fix: add browser bus reconnect helper, reset stale proxy after browser restart, and retry one render call after reconnect.
- Files:
  - viewer/__init__.py
  - tests/test_viewer.py
- Status: fixed in code, pending Linux runtime verification.

### ISSUE-012: No machine-readable proof of what render command/result was last sent
- Symptoms: debugging required manual monitor confirmation to know what was actively sent to display transport.
- Impact: slower diagnosis loops and weaker remote triage during blank-screen incidents.
- Debug evidence: no persistent command/result records existed in Redis or debug bundles.
- Fix: add viewer render probe telemetry (last command, last result, bounded history) and include probe keys in display debug bundle collection.
- Files:
  - viewer/render_probe.py
  - viewer/__init__.py
  - tests/test_viewer.py
  - tests/test_render_probe.py
  - bin/collect_display_debug_bundle.sh
  - bin/run_display_pipeline_tests.sh
- Status: fixed in code, pending Linux runtime verification.

### ISSUE-013: Pi debug loop required manual operator steps that slowed regression fixing
- Symptoms: each investigation required manual SSH commands and ad-hoc bundle collection.
- Impact: slower iteration cycles, longer MTTR, and inconsistent evidence capture across runs.
- Debug evidence: repeated user-driven steps were required to run tests, gather telemetry, and download diagnostics.
- Fix: add an SSH automation runner that executes remote repo sync, compose bring-up, display pipeline tests, render telemetry snapshot, and debug bundle download in one command.
- Files:
  - bin/remote_pi_display_doctor.py
  - docs/developer-documentation.md
- Status: fixed in code, pending first run against reachable Pi target.

### ISSUE-014: Display pipeline tests failed in Pi container due external `mock` dependency
- Symptoms: automated Pi run failed on `tests.test_viewer` import with `ModuleNotFoundError: No module named 'mock'`.
- Impact: blocked automated Linux regression gate and slowed remote debug loop.
- Debug evidence: `display_tests.stderr.log` from remote doctor run `20260508T162940Z`.
- Fix: switch display test import from external `mock` package to stdlib `unittest.mock`.
- Files:
  - tests/test_viewer.py
- Status: fixed in code, pending rerun on Pi automation.

### ISSUE-015: Pi viewer could not mode-set/page-flip due DRM permission denial
- Symptoms: webview logs repeatedly reported `Could not set DRM mode for screen HDMI1 (Permission denied)` and `Could not queue DRM page flip on screen HDMI1 (Permission denied)` while telemetry showed splash render commands succeeded.
- Impact: render intent was emitted but display updates could fail on panel, causing apparent blank screen despite green tests.
- Debug evidence: downloaded bundle `artifacts/pi-display-doctor/20260508T163742Z/anthias-display-debug-20260508T163742Z.tar.gz` (`compose_viewer_logs.txt`, `viewer_webview_eglfs_probe.txt`).
- Fix: add configurable root-run startup path in `bin/start_viewer.sh` and enable it in Pi viewer compose overlay with `VIEWER_RUN_AS_ROOT=1`.
- Files:
  - bin/start_viewer.sh
  - docker-compose.viewer.yml
- Status: fixed in code, pending autonomous Pi rerun and runtime confirmation.

### ISSUE-015 Status Update
- Evidence update: autonomous run `20260508T164344Z` synced the startup/compose files and no longer emits the prior DRM permission-denied mode-set/page-flip signatures in `compose_viewer_logs.txt`.
- Remaining risk: removing DRM permission errors exposed a subsequent root-only QtWebEngine startup blocker (see ISSUE-016).
- Status: partially validated; blocked by new root sandbox failure.

### ISSUE-016: Root-run QtWebEngine failed due Chromium sandbox restriction
- Symptoms: after enabling `VIEWER_RUN_AS_ROOT=1`, webview setup failed with `Running as root without --no-sandbox is not supported`.
- Impact: viewer setup retries fail and display can remain blank even though DRM permission errors are cleared.
- Debug evidence: bundle `artifacts/pi-display-doctor/20260508T164344Z/anthias-display-debug-20260508T164344Z.tar.gz` (`compose_viewer_logs.txt`, around setup failure and QtWebEngine startup).
- Fix: when `VIEWER_RUN_AS_ROOT=1`, append `--no-sandbox` to `QTWEBENGINE_CHROMIUM_FLAGS` in `bin/start_viewer.sh` before launching `viewer.__main__`.
- Files:
  - bin/start_viewer.sh
- Status: fixed in code, pending autonomous Pi rerun and runtime confirmation.

### ISSUE-016 Status Update
- Evidence update: bundle `artifacts/pi-display-doctor/20260508T164633Z/anthias-display-debug-20260508T164633Z.tar.gz` shows root process execution in `viewer_processes.txt` and `QTWEBENGINE_CHROMIUM_FLAGS=... --no-sandbox` in `viewer_webview_proc_environ.txt`.
- Result: root QtWebEngine sandbox blocker no longer appears in viewer logs.
- Status: validated as resolved.

### ISSUE-017: Remote doctor did not sync startup/compose display fixes by default
- Symptoms: autonomous runs initially kept reproducing stale behavior after local startup/compose edits.
- Impact: false-negative reruns where Pi diagnostics did not include latest startup-path fixes.
- Debug evidence: `summary.json` for run `20260508T164204Z` showed `synced_count=8` without `bin/start_viewer.sh` and `docker-compose.viewer.yml`.
- Fix: add both files to `files_to_sync` in `bin/remote_pi_display_doctor.py`.
- Files:
  - bin/remote_pi_display_doctor.py
- Status: fixed in code and validated by run `20260508T164344Z` (`synced_count=10`).

### ISSUE-018: DRM mode-set/page-flip permission denial still persists after root/no-sandbox fixes
- Symptoms: viewer logs continue to emit `Could not set DRM mode for screen HDMI1 (Permission denied)` and `Could not queue DRM page flip on screen HDMI1 (Permission denied)` during splash rendering.
- Impact: panel updates can still fail, leaving blank-screen risk unresolved.
- Debug evidence: bundles `artifacts/pi-display-doctor/20260508T164633Z/anthias-display-debug-20260508T164633Z.tar.gz` and `artifacts/pi-display-doctor/20260508T164924Z/anthias-display-debug-20260508T164924Z.tar.gz` (`compose_viewer_logs.txt`).
- Mitigation attempted: set `QT_QPA_EGLFS_KMS_ATOMIC=0` in viewer overlay.
- Files:
  - docker-compose.viewer.yml
- Status: mitigation deployed but ineffective; issue remains open.

### ISSUE-019: Host display manager (Xorg/lightdm) held DRM master and blocked viewer KMS mode-set
- Symptoms: host diagnostics showed `Xorg` holding `/dev/dri` while viewer container attempted eglfs DRM mode-set.
- Impact: viewer rendered commands successfully but panel could remain blank due to denied DRM ownership/mode-set operations.
- Debug evidence:
  - live host check showed PID 1138 `Xorg :0 ... vt7` as DRM holder.
  - run `artifacts/pi-display-doctor/20260508T165825Z/summary.json` includes `release_drm_owners` step.
  - run bundle `artifacts/pi-display-doctor/20260508T165825Z/anthias-display-debug-20260508T165825Z.tar.gz` shows display managers inactive and viewer-only DRM holders (`viewer_dri_holders.txt`).
- Fix: add doctor automation step to stop active host display managers (`lightdm`, `gdm3`, `sddm`, `xdm`) before compose startup, and add explicit DRM-holder diagnostics to debug bundle.
- Files:
  - bin/remote_pi_display_doctor.py
  - bin/collect_display_debug_bundle.sh
- Status: fixed in automation and validated in autonomous reruns.

## 2026-05-11

### ISSUE-020: Production boot/update path still targeted upstream Anthias checkout instead of Bellforge repo
- Symptoms: Pi showed a Screenly-branded splash page after reboot even though the Bellforge repo, splash template, and runtime config in the active workspace were already Bellforge-branded.
- Impact: deployed devices could boot a stale upstream checkout and staticfiles tree, causing branding drift and making splash/debug fixes appear ineffective.
- Debug evidence:
  - `anthias_app/views.py` and `templates/splash-page.html` in Bellforge render Bellforge branding and `splash_logo_url=/static/img/bellforge-logo.svg`.
  - local runtime config and rendered `/splash-page` HTML both resolved to Bellforge assets.
  - `bin/install.sh`, `bin/upgrade_containers.sh`, `ansible/roles/anthias/tasks/main.yml`, and `ansible/roles/anthias/templates/anthias-host-agent.service` still referenced upstream Screenly URLs and `/home/${USER}/anthias`.
- Fix: repoint install/update/systemd paths to the Bellforge repository, switch production compose generation to the current repo root, and mount staticfiles from the Bellforge checkout.
- Files:
  - bin/install.sh
  - bin/upgrade_containers.sh
  - docker-compose.yml.tmpl
  - ansible/roles/anthias/tasks/main.yml
  - ansible/roles/anthias/templates/anthias-host-agent.service
  - ansible/roles/anthias/vars/main.yml
- Status: fixed in code, pending Pi-side deployment and reboot verification.

### ISSUE-018 Status Update
- Evidence update:
  - run `artifacts/pi-display-doctor/20260508T165825Z/summary.json`: full pipeline passed after DRM-owner release.
  - run `artifacts/pi-display-doctor/20260508T170017Z/summary.json`: second confirmation run also passed.
  - viewer logs from `artifacts/pi-display-doctor/20260508T165825Z/anthias-display-debug-20260508T165825Z.tar.gz` no longer include prior DRM permission-denied signatures.
  - user runtime validation confirms display is visible and showing Anthias startup screen.
- Status: resolved via host DRM-owner release (display manager stop) in automated Pi doctor flow.

### ISSUE-020: Startup splash could advertise localhost despite reachable LAN IP
- Symptoms: startup splash could still show localhost-style guidance when `MY_IP` was local/loopback or when candidate parsing accepted non-IP tokens.
- Impact: users on other devices could receive non-routable startup guidance during first boot/offline fallback.
- Debug evidence: remote run artifacts and startup fallback analysis showed LAN URL selection was not consistently prioritized.
- Fix:
  - add viewer startup URL resolver that prefers valid non-local IP candidates and falls back to `anthias.local`.
  - harden server `splash_page` to filter loopback/unspecified addresses and use `anthias.local` fallback instead of localhost.
  - add regression tests for both viewer and server startup-address selection behavior.
- Files:
  - viewer/__init__.py
  - tests/test_viewer.py
  - anthias_app/views.py
  - anthias_app/tests.py
- Status: fixed in code and validated in Pi doctor run `artifacts/pi-display-doctor/20260508T171214Z/summary.json`.

### ISSUE-021: Bundle lacked direct capture of rendered startup HTML URL line
- Symptoms: diagnostics included viewer/system logs but not the actual offline splash HTML payload rendered in container.
- Impact: extra manual shell probing was required to verify displayed startup URL, slowing regression triage.
- Debug evidence: run `artifacts/pi-display-doctor/20260508T171214Z/` required manual follow-up to inspect `/tmp/display.html`.
- Fix:
  - add `viewer_display_html.txt` and `viewer_display_url_line.txt` captures to display debug bundle.
  - include startup splash server files in remote sync set so Pi doctor runs validate current startup-address behavior end-to-end.
- Files:
  - bin/collect_display_debug_bundle.sh
  - bin/remote_pi_display_doctor.py
- Status: fixed in code, pending next bundle run confirmation.

### ISSUE-022: Startup guidance could advertise anthias.local when host mDNS name differed
- Symptoms: display guidance could show `http://anthias.local` even when device hostname/mDNS was not `anthias`, causing operators to follow a non-resolving address.
- Impact: management UI could appear unreachable during startup/offline fallback even when the device was reachable at `<actual-hostname>.local` or LAN IP.
- Debug evidence:

## 2026-05-10

### ISSUE-023: Reboot regression when host display manager reacquired DRM master
- Symptoms: after reboot, Pi monitor returned to blank output while server/splash endpoints remained reachable over network.
- Impact: viewer container stayed up but could not present frames on HDMI, creating a false impression of an application-level splash/display regression.
- Debug evidence:
  - viewer logs repeatedly showed `Could not set DRM mode for screen HDMI1 (Permission denied)` and `Could not queue DRM page flip on screen HDMI1 (Permission denied)`.
  - host check showed `Xorg` (lightdm) owning `/dev/dri/card1` and `/dev/dri/renderD128`.
  - render telemetry remained healthy (`viewer.render.last_command`, `viewer.render.last_result`, `viewer.render.history`), proving render intent/debug path was active while scanout failed.
- Fix:
  - immediate runtime mitigation on Pi: disable/mask `lightdm` and restart viewer/server stack.
  - persistent fix in repo: add `ExecStartPre` display-manager stop guards to `bin/anthias-dev.service` before compose startup.
- Files:
  - bin/anthias-dev.service
- Status: fixed in code and validated on Pi runtime after restart (DRM permission-denied signatures cleared; splash and management UI reachable).
  - server `splash_page` fallback used hardcoded `http://anthias.local` when no routable IP candidates were returned.
  - viewer offline splash resolver also defaulted to `anthias.local` when IP lookup was unavailable.
  - Pi diagnostics captured host `HOSTNAME=RPi5Dev` while rendered startup guidance still showed `anthias.local`.
- Fix:
  - publish host hostname from host-agent into Redis (`host_hostname`) during IP refresh.
  - add shared hostname lookup in `lib.utils.get_node_hostname()`.
  - update server splash and viewer offline fallback to prefer `http://<hostname>.local`, with `anthias.local` as last-resort fallback.
  - add regression tests for hostname-local fallback and explicit `anthias.local` fallback when hostname data is unavailable.
- Files:
  - host_agent.py
  - lib/utils.py
  - anthias_app/views.py
  - anthias_app/tests.py
  - viewer/__init__.py
  - tests/test_viewer.py
- Status: fixed in code; test execution blocked in this session due missing Docker Linux engine and missing local Django dependency.

### ISSUE-022 Status Update
- Evidence update: the original ISSUE-022 section was split by the later ISSUE-023 append and now contains fragmented bullets.
- Clarified debug evidence:
  - `splash_page` fallback previously used `http://anthias.local` when no routable IP candidate was available.
  - viewer offline fallback also defaulted to `anthias.local` when IP lookup failed.
  - Pi diagnostics captured hostname `RPi5Dev` while startup guidance still showed `anthias.local`.
- Clarified fix summary:
  - host agent publishes hostname to Redis key `host_hostname`.
  - shared hostname resolver in `lib.utils.get_node_hostname()`.
  - startup URL selection prefers `http://<hostname>.local` before `anthias.local`.
- Status: resolved in code (supersedes fragmented ISSUE-022 bullets above).

### ISSUE-023 Status Update
- Evidence update:
  - latest Pi runtime checks show display managers inactive (`lightdm`, `gdm3`, `sddm`, `xdm` all `inactive`).
  - viewer render telemetry remains active (`viewer.render.last_command` and `viewer.render.last_result` continue to show splash-page rendering activity).
  - server logs continue serving `/splash-page` with HTTP 200 responses.
- Remaining risk:
  - physical panel visibility can still diverge from telemetry if connector routing/monitor state changes outside app control.
- Status: mitigation in place and runtime healthy; continue reboot-level physical validation after each service/system update.

### ISSUE-024: HTTP self-probe in splash URL filtering triggered recursive request storm
- Symptoms: splash endpoint calls increased rapidly and remote curl checks to `/splash-page` could hang/timed out.
- Impact: startup guidance validation path risked request recursion and unstable splash rendering under load.
- Debug evidence:
  - server logs showed repeated back-to-back `/splash-page` 200 responses from container-local clients.
  - regression introduced when `probe_management_server()` used in-request HTTP GET probing for each candidate URL.
- Fix:
  - replace HTTP reachability probing with TCP socket connect probing in `probe_management_server()`.
  - add deterministic tests for socket-based management probe and internet probe behavior.
  - update splash reachability assertions to include non-default management port (`:8000`) in dev stack.
- Files:
  - lib/utils.py
  - tests/test_utils.py
  - anthias_app/tests.py
- Status: fixed in code; pending final Pi runtime confirmation after redeploy.

### ISSUE-025: Startup guidance and default widgets were not localized on Pi dev runtime
- Symptoms:
  - offline startup splash could advertise non-working guidance without the
    dev management port.
  - default weather widget showed San Francisco when weather URL had no
    coordinates.
  - Pi host timezone remained UTC, causing clock/widget time drift from local
    expectation.
- Impact:
  - slower setup/recovery during display incidents.
  - misleading location/time during default-asset playback.
- Debug evidence:
  - runtime telemetry showed alternating renders of
    `https://weather.srly.io` and `https://clock.srly.io`.
  - `timedatectl` on Pi reported `UTC` before runtime correction.
  - weather widget source and query probe confirmed `lat/lng` are supported
    and absent by default.
- Fix:
  - viewer offline URL normalization now appends `MANAGEMENT_PORT` when set
    (for example, `:8000` in dev).
  - viewer dev overlay now passes `MY_IP` and `MANAGEMENT_PORT` to the viewer
    service.
  - default-asset insertion now localizes `weather.srly.io` URIs by looking up
    public coordinates and appending `lat`/`lng` query values.
  - Django timezone resolution now honors `ANTHIAS_TIME_ZONE` or `TZ` before
    `/etc/timezone` fallback.
  - regression tests added for weather URI localization and offline splash port
    behavior.
- Files:
  - viewer/__init__.py
  - docker-compose.viewer.yml
  - anthias_app/helpers.py
  - anthias_app/tests.py
  - tests/test_viewer.py
  - anthias_django/settings.py
- Status: fixed in code; runtime timezone corrected on Pi; weather URI runtime
  rewrite pending direct DB update command execution.

### ISSUE-025 Status Update
- Evidence update:
  - persisted default weather asset on Pi now includes coordinates:
    `https://weather.srly.io?lat=36.15398&lng=-95.99277`.
  - render telemetry confirms localized weather URI is now actively rendered.
  - host and viewer runtime clocks both report `America/Chicago` / `CDT`.
- Permanent update-hardening:
  - added `anthias_app` management command `localize_default_assets`.
  - wired startup reconciliation in `bin/start_server.sh` so upgrades
    localize existing default weather assets automatically.
  - timezone resolution now prefers env override, then `/etc/localtime`
    symlink-derived zone, then `/etc/timezone` fallback.
  - targeted Linux tests pass for default-asset localization and offline
    splash management-port URL behavior.
- Files:
  - anthias_app/helpers.py
  - anthias_app/management/commands/localize_default_assets.py
  - anthias_app/tests.py
  - bin/start_server.sh
  - anthias_django/settings.py
  - viewer/__init__.py
  - tests/test_viewer.py
- Status: resolved and validated on Pi runtime with upgrade-safe path.

### ISSUE-026: Clock widget could drift when `/etc/timezone` stayed stale after host timezone change
- Symptoms:
  - weather widget time/location correct (geo-driven), but clock widget still
    displayed an incorrect hour after reboot.
  - host `timedatectl` and `/etc/localtime` reflected local timezone while
    `/etc/timezone` still contained stale `UTC`.
- Impact:
  - default clock page could show wrong local time on otherwise healthy
    startup/runtime pipelines.
- Debug evidence:
  - host: `timedatectl -> America/Chicago`, `readlink -f /etc/localtime ->
    /usr/share/zoneinfo/America/Chicago`, but `cat /etc/timezone -> UTC`.
  - viewer render history alternated expected clock/weather pages, indicating
    display intent was healthy and issue was timezone source consistency.
- Fix:
  - update timezone ansible task to reconcile `/etc/timezone` from
    `/etc/localtime` fallback even when `/etc/timezone` already exists.
  - update `bin/start_viewer.sh` to derive/export `TZ` from
    `/etc/localtime` symlink at startup, with `/etc/timezone` as secondary
    fallback.
- Files:
  - ansible/roles/system/tasks/timezone.yml
  - bin/start_viewer.sh
- Status: fixed in code; pending user visual confirmation after reboot/start.

## 2026-05-11

### ISSUE-027: Startup splash needed setup-aware hold timing
- Symptoms:
  - when assets were configured, startup could transition too quickly for users to note management URL guidance.
  - operators requested a "first setup stays visible, post-setup short reminder" behavior.
- Impact:
  - first-time onboarding and post-setup boot experience used the same timing model, which did not fit both scenarios.
- Debug evidence:
  - startup hold logic was not aware of whether playlist content already existed.
- Fix:
  - add setup-aware startup hold logic in viewer startup.
  - if scheduler starts with no assets, skip timed startup hold and let empty-playlist loop keep splash visible.
  - if assets exist, apply configurable short startup hold via `STARTUP_SPLASH_MIN_SECONDS` (default 15s).
  - add tests for env parsing, post-setup hold, and empty-playlist hold skip behavior.
- Files:
  - viewer/__init__.py
  - tests/test_viewer.py
  - docs/display-pipeline-fix-log.md
- Status: fixed in code, pending Linux runtime verification.

## 2025-05-11

### ISSUE-027: Offline splash watchdog timeout insufficient for Qt6 WebEngine D-Bus blocking

## 2026-05-13

### ISSUE-028: Reboot-time black screen recurrence with healthy render telemetry
- Symptoms:
  - after reboot, display briefly appeared healthy and then turned black again.
  - network checks and startup endpoint remained reachable while panel output regressed.
- Impact:
  - operators could not trust reboot persistence even when service health checks looked good.
- Debug evidence:
  - render telemetry stayed healthy (`viewer.render.last_result` advanced continuously with success states).
  - viewer container stayed running and produced active EGL/KMS output logs.
  - Pi boot configuration was using `dtoverlay=vc4-fkms-v3d` and lacked explicit console blank disable.
- Fix:
  - switch Pi boot overlay to full KMS (`dtoverlay=vc4-kms-v3d`).
  - add `consoleblank=0` to kernel cmdline.
  - persistently disable/mask host display manager service (`lightdm`) to prevent DRM ownership races after updates/reboots.
  - revalidate with reboot and runtime soak checks (viewer up, splash HTTP 200, render telemetry progressing).
- Files:
  - /boot/firmware/config.txt (Pi runtime)
  - /boot/firmware/cmdline.txt (Pi runtime)
  - bin/anthias-dev.service
- Status: mitigated on Pi runtime and currently stable; continue reboot-level physical display validation for confidence.
- Symptoms: offline splash watchdog timed out after 30 seconds while actual D-Bus rendering call to iew_webpage() took ~79 seconds on Raspberry Pi 5 with Qt6 WebEngine.
- Impact: splash rendering would timeout and trigger retry logic, logging "offline-splash watchdog timeout after 30.xxs on attempt 1" even though the splash eventually rendered successfully. Display appeared to hang momentarily as the system recovered, degrading user experience during boot.
- Root cause: iew_webpage() D-Bus call is blocking and waits for the Qt webview process to receive the message, render the HTML, and acknowledge completion. On Pi 5 with Qt6 WebEngine, this process takes ~79 seconds due to webview initialization overhead.
- Debug evidence:
  - Container logs showed consistent timing: "offline splash rendered successfully (79.14s)" but watchdog warning at "offline-splash watchdog timeout after 30.xxs on attempt 1".
  - The splash eventually completed and returned True, proving the timeout was a warning-only condition, not a hard blocker.
  - Multiple container restarts during troubleshooting confirmed the 79-second duration was consistent across attempts.
- Fix:
  - increased SPLASH_WATCHDOG_TIMEOUT_SECONDS from 30.0 to 90.0 in viewer/__init__.py.
  - provides 11 seconds of headroom for the actual ~79-second blocking operation.
  - maintains watchdog's protective function for truly stuck renders while accommodating legitimate slow webview startup.
- Files:
  - viewer/__init__.py (SPLASH_WATCHDOG_TIMEOUT_SECONDS constant)
- Status: fixed and validated on Pi5 with Qt6 WebEngine; offline splash now completes within timeout window without warnings.

## 2026-05-13 (Bugfix Workflow Validation)

### ISSUE-029: Settings backup/system-controls region could be obscured by footer overlap
- Symptoms:
  - Settings page backup/system-controls area could appear truncated at the bottom.
  - Users reported inability to reliably scroll to all controls.
- Impact:
  - Backup and recovery actions were harder to access during recovery workflows.
- Debug evidence:
  - live browser geometry checks showed footer overlap against settings bottom content before fix.
  - post-fix checks verified no overlap and full section visibility.
- Fix:
  - add settings-route footer flow override and spacing guard in `static/sass/_styles.scss`.
  - keep global footer behavior unchanged for non-settings routes.
- Files:
  - static/sass/_styles.scss
  - static/src/components/settings/index.tsx
- Status:
  - fixed in code and validated in live Pi browser checks.

### ISSUE-030: Fresh-install simulation restore phase initially failed due missing restore script in remote clone
- Symptoms:
  - fresh-install simulation completed upgrade/clone/startup phases but restore phase aborted with missing restore script path.
- Impact:
  - automated corruption-recovery validation could not finish in one pass.
- Debug evidence:
  - simulation run failed at phase 4 with missing `/opt/bellforge/bin/restore_bellforge_state.sh`.
- Fix:
  - sync backup/restore scripts to Pi runtime path and rerun backup+corruption+restore validation.
  - confirm service recovery, DB restore, and endpoint health checks.
- Files:
  - bin/backup_bellforge_state.sh
  - bin/restore_bellforge_state.sh
  - bin/run_pi_fresh_install_simulation.sh
- Status:
  - validated on Pi runtime: corruption simulation and restore recovery succeeded.
