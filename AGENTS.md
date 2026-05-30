# AGENTS.md — temporalis

Unified multi-provider weather abstraction library for Python: query OpenWeatherMap, Open-Meteo, MetNo, IPMA, NWS, marine and air-quality feeds through one consistent object model, with automatic field derivation and an ensemble mode that merges all free sources in parallel.

## Setup

```bash
pip install -e .            # runtime deps: requests, timezonefinder, geopy, pendulum>=3, astral>=3,<4
pip install -e ".[test]"    # adds pytest, responses
```

Requires Python >= 3.10.

## Test

```bash
pytest test/
```

Tests are offline: HTTP is mocked with `responses` against recorded JSON in `test/fixtures/`. `pyproject.toml` sets `addopts = "-p no:ovoscope"` so an installed ovoscope plugin does not interfere. Regenerate fixtures with `test/record_fixtures.py` (makes live network calls — not run in CI).

## Lint/Typecheck

Ruff via the gh-automations `lint.yml` workflow (`ruff: true`, `pre_commit: false`). The package ships `py.typed` and uses `from __future__ import annotations`; no type-checker is wired into CI.

## Layout

Plain importable library, not a plugin — no entry points / entry-point group.

- `temporalis/__init__.py` — core data model: `DataPoint` (value + units + min/max/prob/time, serialises via `as_dict`/`from_dict`), `WeatherData`, `HourlyForecast`, `DailyForecast`, `MinutelyData`, `MinutelyForecast`.
- `temporalis/providers/__init__.py` — `WeatherProvider` base class: registry (`register`/`get`/`available`), `from_address`, session handling, units normalisation (`metric`/`us`).
- `temporalis/providers/registry.py` — imports and registers all built-in providers under string keys.
- `temporalis/providers/` — one module per source: `owm`, `openmeteo`, `openmeteo_marine`, `openmeteo_airquality`, `metno`, `ipma`, `nws`, `ensemble`.
- `temporalis/derived.py` — fills missing fields (dewPoint, apparentTemperature, snow, uvIndex) from available data.
- `temporalis/sun.py`, `temporalis/moon.py` — astral-based sun/moon times and phases.
- `temporalis/location.py`, `temporalis/time.py` — geocoding/timezone resolution and time helpers.
- `temporalis/version.py` — managed by gh-automations; do not edit.
- `test/` — pytest suite + `fixtures/` recorded JSON.
- `docs/`, `examples/` — usage docs and runnable examples.

## Conventions (Org hard rules)

- Branch `dev` for work, `master` for stable. NEVER `main`.
- Never edit `temporalis/version.py`; gh-automations bumps semver from conventional-commit prefixes (`feat:`, `fix:`, `feat!:`).
- New repos private by default.
- Commit identity: JarbasAi <jarbasai@mailfence.com>.
- Reference `OpenVoiceOS/gh-automations` reusable workflows at `@dev`.
- No Neon / `neon-*` references.
- No meta-commentary in code/docs/commits (no history, no dates) — describe current state only.
- CI is provided by `OpenVoiceOS/gh-automations`.

## Gotchas

- `pyproject.toml` `Homepage` points at `OpenJarbas/temporalis`; the real remote is `JarbasAl/temporalis`.
- Region providers raise `ValueError` for out-of-coverage coordinates: `NWS` (USA only), `IPMA` (Portugal only), `OpenMeteoMarine` (landlocked coords).
- `Ensemble` merges providers in parallel and returns means; `DataPoint.min_val`/`max_val` then encode inter-provider spread (wide spread = low confidence), not a single provider's daily range.
- Each provider instance owns its own `requests.Session`; caching is opt-in by replacing `wx.session` (e.g. `requests_cache.CachedSession`) after construction.
- `requirements.txt` lists extra packages (`geocoder`, `python-dateutil`, `pytz`, `requests-cache`) not declared in `pyproject.toml` runtime deps; the installed metadata in `pyproject.toml` is authoritative.
- Duplicate/legacy workflows exist (`build_tests.yml`, `license_tests.yml`) alongside the gh-automations standards (`build-tests.yml`, `license_check.yml`); the legacy ones are inline and `license_tests.yml` pulls a Neon-org lichecker fork.
- Several workflows trigger on a `dev` branch that does not yet exist on the remote (only `master` + release branch).
