# Sprint: Revive temporalis — core fixes + IPMA + Open-Meteo providers

## Sprint Goal
A working, installable temporalis library with all critical bugs fixed, two new keyless providers (IPMA and Open-Meteo), and a test suite that validates each provider's data model without network access.

## In Scope
- Fix `as_dict()` mutation bug in `DataPoint` and `WeatherData`
- Remove all hardcoded API keys and personal geocoding credentials
- Delete `darksky.py` and `xml.py` (dead code)
- Fix `Nominatim(user_agent="temporalis")`
- Replace bare `except:` clauses with typed exception handling
- Add `IPMA` provider (Portugal's national weather service, no key required)
- Add `OpenMeteo` provider (global, no key required) — port from ovos-weather-skill
- Keep and fix `OWM` provider (require explicit key injection)
- Migrate packaging to `pyproject.toml`; pin major dependency versions
- Add HTTP-mocked tests for `DataPoint`, `WeatherData`, OWM, IPMA, Open-Meteo
- Upgrade GitHub Actions to current versions
- Simplify geocoding: single Nominatim backend, optional dep

## Out of Scope
- OVOS / voice assistant integration
- Async support
- CLI tool
- Weatherbit, Pirate Weather, Weather.gov, or other providers (future sprints)
- Historical weather data
- Weather alerts / warnings beyond what providers return in forecast
- PyPI release (can follow after sprint)

## Success Criteria
- [ ] `DataPoint.as_dict()` and `WeatherData.as_dict()` can be called multiple times without corrupting the object
- [ ] No API keys or personal credentials appear anywhere in source
- [ ] `OWM(lat, lon)` raises a clear error when no key is provided (no silent fallback key)
- [ ] `IPMA(lat, lon)` returns a `WeatherData` object with current conditions for a Portuguese coordinate
- [ ] `OpenMeteo(lat, lon)` returns a `WeatherData` object with current + daily + hourly forecasts for any coordinate
- [ ] All three providers pass tests using mocked HTTP responses (no real network calls in CI)
- [ ] `pip install temporalis` succeeds on Python 3.10+ from the revised `pyproject.toml`
- [ ] GitHub Actions CI runs the test suite and passes
