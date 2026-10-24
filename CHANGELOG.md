# Changelog

All notable changes to Flight Sim Overlay are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Security

- Updated Pillow from 12.3.0 to 13.0.0 to resolve published security advisories.

## [2.0.2] - 2026-07-25

### Security

- Updated Pillow from 11.1.0 to 12.3.0 to include the latest supported security
  fixes.

## [2.0.1] - 2026-07-25

### Fixed

- Live overlay settings now refresh without duplicating animation or polling loops.
- Demo mode is enabled before telemetry services start, including when using the
  legacy mock-server launcher.
- Arrival taxi detection honors the configured taxi-speed threshold.
- SimBrief plans with missing airline or flight-number fields no longer fail to
  parse.
- Fully transparent panels no longer retain a faint gradient.

## [2.0.0] - 2026-07-25

### Added

- A native system-tray controller with connection status, overlay/settings
  shortcuts, all theme and aircraft choices, transparency presets, random theme,
  SimBrief refresh, reset-to-defaults, and quit actions.
- A responsive graphical settings studio with persistent JSON configuration and
  a live overlay preview.
- Fifteen curated theme sets and six selectable aircraft silhouettes.
- Adjustable transparency with synchronized slider and numeric input, scale,
  width, edge anchoring, offsets, motion smoothing, metric placement, visibility,
  polling, reconnection, and flight-phase thresholds.
- A ten-stage gate-to-gate flight-phase state machine with configurable
  hysteresis: at gate, departure taxi, departure, climb, cruise, descent,
  approach, arrival, arrival taxi, and final gate.
- SimBrief flight-plan integration, including a force-refresh action and parsing
  for route geometry, distance, cruise altitude, airports, aircraft, and callsign.
- Route-aware progress tracking that maps current SimConnect latitude/longitude
  onto the imported flight-plan polyline and prevents backward marker jumps.
- SayIntentions.AI `flightJSON` discovery through its supported local HTTP
  endpoint with local-file fallback. Credentials remain server-side.
- VATSIM public-feed callsign tracking.
- SimConnect, SimBrief, SayIntentions, and VATSIM status indicators.
- A built-in animated demo flight (`python server.py --demo`) for testing without
  starting Microsoft Flight Simulator.
- Health, telemetry, settings, catalog, random-theme, reset, and SimBrief-refresh
  JSON APIs.
- An anatomical overlay diagram and component reference in the README.
- Environment templates and workstation-local configuration through `.env`.

### Changed

- Rebuilt the overlay as a modern glass instrument strip with responsive metric
  banks, a corrected heading tape, route identity, phase timeline, and status rail.
- Separated application, configuration, telemetry, integrations, phase inference,
  progress tracking, and tray behavior into testable modules.
- Made all progress-bar aircraft glyphs intrinsically point right. The orientation
  is consistent across every aircraft type, the settings picker, and live preview.
- Replaced observed-maximum ETE progress with position-based route progress.
- Updated refresh behavior from one-second chained browser work to configurable,
  cached service polling and smoothly interpolated presentation.
- Reduced runtime dependencies to the packages the application actually uses.
- Refreshed setup, OBS/browser-source, customization, troubleshooting, privacy,
  and integration documentation.

### Fixed

- Distance overwriting the altitude element.
- The malformed `:middle-row` class and progress-bar alignment.
- The unexplained −10° magnetic-heading offset.
- Heading animation taking the long way around when crossing north.
- Crashes at startup when SimConnect or Microsoft Flight Simulator is unavailable.
- Null telemetry values throwing browser formatting exceptions.
- Aircraft marker drift caused by separate progress calculations.
- Phase flicker caused by single-sample altitude and ground-state changes.

### Security

- `.env`, persisted user settings, caches, and logs are excluded from version control.
- SayIntentions API credentials discovered in `flightJSON` are never exposed through
  the settings or telemetry APIs.
