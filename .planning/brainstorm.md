# Brainstorm: Revive temporalis as a multi-provider standalone weather library

## Problem Statement
temporalis is a dormant Python weather abstraction library with a solid `WeatherProvider` / `WeatherData` / `DataPoint` data model but serious implementation bugs (mutable `as_dict()` corrupts objects, hardcoded credentials, dead DarkSky provider, no tests, unpinned dependencies). The goal is to revive it as a maintained standalone library that exposes a unified API across multiple weather data providers — starting with IPMA (Portugal's national service) as a mandatory addition — and is extensible enough to grow a provider ecosystem over time.

## Ideas & Approaches

### Core fixes (must-do before anything else)
- **Fix `as_dict()` mutation bug** — Change `data = self.__dict__` to `data = dict(self.__dict__)` in both `DataPoint` and `WeatherData`; currently one call permanently destroys the object.
- **Remove hardcoded credentials** — Require API keys as mandatory constructor args; no defaults, no fallback keys in source.
- **Delete dead code** — Remove `darksky.py` and `xml.py`; they add noise and false capability signals.
- **Fix `Nominatim` user_agent** — Pass `user_agent="temporalis"` to avoid `ConfigurationError` on current geopy.

### Provider strategy
- **IPMA (mandatory)** — Portugal's public weather API (`api.ipma.pt`) requires no API key; provides current conditions, daily and hourly forecasts, and warnings. This is the natural keyless default provider for PT users.
- **Open-Meteo (recommended free default)** — Fully open, no key required, global coverage, rich forecast data (hourly, daily, 16-day). Ideal as a keyless fallback for non-PT users and for testing without credentials.
- **Keep OWM** — Functional, widely used, already implemented. Strip the hardcoded key; require explicit key injection.
- **Weatherbit** — Appears in the git log (`6f13a95 weatherbit`) but never shipped; could be revived as a keyed provider with good historical data support.
- **Open-Meteo for historical** — Provides free historical weather data going back decades; complementary to forecast-focused providers.
- **Weather.gov (NWS)** — Free, no key, US-only; good pair to IPMA (country-specific public APIs).
- **Pirate Weather** — Drop-in DarkSky replacement API (same schema); would revive the DarkSky provider with minimal changes if users want that interface.

### Architecture options for multi-provider
- **Keep the current base class pattern** — Each provider subclasses `WeatherProvider`, fetches and normalises its own data. Simple, no added abstractions. Add a `provider_name` class attribute for introspection.
- **Add a `get()` factory / registry** — `WeatherProvider.get("owm", lat, lon, key=...)` for programmatic provider selection without direct imports. Optional, low effort.
- **Provider capability flags** — `supports_historical`, `supports_alerts`, `requires_key` as class-level booleans; lets callers filter providers by capability without instantiating them.
- **Lazy loading** — Only import a provider's optional dependencies when that provider is instantiated, to avoid hard failures when e.g. a keyed provider's SDK isn't installed.

### Packaging & quality
- **Migrate to `pyproject.toml`** — Drop `setup.py`; use `[project.optional-dependencies]` to make heavy geocoding deps (`geocoder`, `geopy`) optional.
- **Pin major versions** — `pendulum>=3,<4` or downgrade to `pendulum<3` depending on which API surface is targeted; `astral>=3`.
- **Consolidate datetime libs** — Drop `pytz` and `python-dateutil`; use only `pendulum` + stdlib `zoneinfo` as fallback.
- **Add real tests with HTTP mocking** — Use `responses` library to mock API calls; test `DataPoint`, `WeatherData`, and each provider's parse logic without network access.
- **Upgrade GitHub Actions** — `checkout@v4`, `setup-python@v5`; replace `lichecker` with standard `pip-licenses`.

### Geocoding
- **Simplify geocoding** — Accept `(lat, lon)` as the primary interface everywhere; make address-based `from_address()` methods use a single configurable backend (default: Nominatim with proper user_agent). Remove the 8-provider fallback chain.
- **Make geocoding optional** — Users who always pass coordinates shouldn't need geocoding deps at all.

## Constraints
- Standalone Python library — no OVOS, no voice assistant integrations.
- IPMA is mandatory in the first sprint.
- Unified API surface: all providers must expose the same `WeatherData` / `DataPoint` / `HourlyForecast` / `DailyForecast` objects.
- No breaking changes to the `WeatherProvider(lat, lon)` constructor signature.
- Provider additions should not require changes to the base class.

## Open Questions
- Should IPMA be the default keyless provider globally or only when coordinates are in Portugal? (IPMA's API is PT-only.)
- Does IPMA's API provide hourly forecasts, or only daily? (Need to verify endpoint coverage before committing to the data model.)
- What Python version floor? (Affects whether `zoneinfo` is available without backport, and pendulum v2 vs v3 choice.)
- Should `from_address()` be kept at all, or deprecated in favour of always requiring coordinates? Geocoding is the biggest source of fragility.
- Versioning: bump to `0.2.0` for the revival or `1.0.0` to signal stability intent?

## Risks
- **IPMA API instability** — `api.ipma.pt` is a public government API with no SLA; endpoints or schemas may change without notice. Mitigation: pin to documented endpoint versions, add integration tests that fail loudly on schema changes.
- **pendulum v2/v3 split** — Significant API changes between versions; pinning is mandatory. Mitigation: test against both if supporting wide install bases, or pick one and document the floor.
- **OWM free tier limits** — The free OWM plan restricts hourly forecast calls. Mitigation: the existing `requests-cache` session handles this; document the limitation.
- **Geocoding ToS** — Nominatim requires a valid user_agent and prohibits high-volume use. Mitigation: always pass `user_agent="temporalis"`, document the limitation, encourage users to pass coordinates directly.
