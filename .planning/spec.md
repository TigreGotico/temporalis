# Spec: Revive temporalis — core fixes + IPMA + Open-Meteo providers

## Objective
Revive the dormant temporalis Python library into a working, installable, multi-provider weather abstraction library. The work covers three areas: (1) fix critical bugs in the existing data model and OWM provider, (2) add two new keyless providers — IPMA (Portugal's national service) and Open-Meteo (global) — each normalising their data into the existing `WeatherData` / `DataPoint` / `HourlyForecast` / `DailyForecast` model, and (3) modernise packaging and add a real test suite. The library is standalone Python — no OVOS or voice assistant integration.

## Functional Requirements

### Data model fixes
1. `DataPoint.as_dict()` MUST return a copy of the instance's data without modifying `self.__dict__`; calling it multiple times on the same instance MUST return identical results.
2. `WeatherData.as_dict()` MUST return a copy of the instance's data without modifying `self.__dict__`; calling it multiple times on the same instance MUST return identical results.
3. All bare `except:` clauses in `__init__.py`, `location.py`, and `providers/__init__.py` MUST be replaced with typed exception handlers (`except Exception` or a specific type).

### Credentials & dead code
4. No API key, personal token, or personal service username (e.g. `key='jarbas'`, `OWM.default_key`) MAY appear anywhere in source or committed files.
5. `OWM.__init__` MUST raise `ValueError` (with a descriptive message) when instantiated without an explicit `key` argument.
6. `temporalis/providers/darksky.py` and `temporalis/xml.py` MUST be deleted.

### Geocoding
7. `location.geolocate()` MUST use only a single geocoding backend (Nominatim via geopy) as the online fallback; the 8-provider sequential fallback chain MUST be removed.
8. `geopy.geocoders.Nominatim` MUST be instantiated with `user_agent="temporalis"` everywhere it is used.
9. `geocoder` and `geopy.geocoders.Yandex` MUST be removed from `location.py`; `geopy` remains as the sole geocoding dependency.

### IPMA provider
10. `temporalis/providers/ipma.py` MUST implement an `IPMA(lat, lon)` class that subclasses `WeatherProvider`.
11. `IPMA` MUST require no API key.
12. `IPMA` MUST populate `self.data["currently"]` with a `WeatherData`-compatible dict from the IPMA current conditions endpoint for the nearest station to the given coordinates.
13. `IPMA` MUST populate `self.data["daily"]` with at least 5 days of `WeatherData`-compatible dicts from the IPMA daily forecast endpoint.
14. `IPMA` MUST raise `ValueError` when instantiated with coordinates outside Portugal's bounding box (approximately lat 36–42°N, lon 6–10°W), since the IPMA API does not cover other regions.
15. `IPMA` MUST expose `weather`, `days`, and `daily` properties via the inherited `WeatherProvider` interface.

### Open-Meteo provider
16. `temporalis/providers/openmeteo.py` MUST implement an `OpenMeteo(lat, lon)` class that subclasses `WeatherProvider`.
17. `OpenMeteo` MUST require no API key.
18. `OpenMeteo` MUST populate `self.data["currently"]` from the `current_weather` field of the Open-Meteo API response.
19. `OpenMeteo` MUST populate `self.data["hourly"]` with per-hour `WeatherData`-compatible dicts, including at minimum: temperature, apparent temperature, humidity, cloud cover, precipitation, wind speed, wind direction, visibility, and weather code.
20. `OpenMeteo` MUST populate `self.data["daily"]` with per-day `WeatherData`-compatible dicts, including at minimum: temperature min/max, apparent temperature min/max, precipitation sum, precipitation probability, wind speed max, wind gust max, wind direction, UV index max, and weather code.
21. `OpenMeteo` MUST accept a `units` argument (`"metric"` / `"imperial"`) and pass the appropriate Open-Meteo unit parameters (`temperature_unit`, `windspeed_unit`, `precipitation_unit`) to the API.
22. `OpenMeteo` MUST expose `weather`, `hours`, `days`, `hourly`, and `daily` properties via the inherited `WeatherProvider` interface.

### Unified API contract
23. All three providers (`OWM`, `IPMA`, `OpenMeteo`) MUST expose the same interface: `weather` (current `WeatherData`), `days` (list of `WeatherData`), `hours` (list of `WeatherData`), `daily` (`DailyForecast`), `hourly` (`HourlyForecast`), `dawn`, `dusk`, `sunrise`, `sunset`, `noon`, `moon_phase`, `moon_symbol`, `moon_phase_name`.
24. A provider subclass MUST be addable to the library without modifying `WeatherProvider`, `WeatherData`, `DataPoint`, `HourlyForecast`, or `DailyForecast`.

### Packaging
25. The project MUST use `pyproject.toml` as its sole build configuration; `setup.py` MUST be deleted.
26. `pyproject.toml` MUST declare `python_requires = ">=3.10"`.
27. `pyproject.toml` MUST pin major versions for `pendulum` (`>=2,<3`), `astral` (`>=3,<4`), and `requests-cache` (`>=1,<2`).
28. `pytz` and `python-dateutil` MUST be removed from the dependency list; datetime handling uses only `pendulum` and stdlib.
29. `geocoder` MUST be removed from the dependency list (replaced by `geopy` only).

### Tests
30. `test/test_data_model.py` MUST contain tests verifying that calling `DataPoint.as_dict()` twice on the same instance returns identical dicts.
31. `test/test_data_model.py` MUST contain tests verifying that calling `WeatherData.as_dict()` twice on the same instance returns identical dicts.
32. `test/test_owm.py` MUST contain at least one test using a mocked HTTP response that verifies `OWM.weather` returns a `WeatherData` instance with a non-None `temperature`.
33. `test/test_ipma.py` MUST contain at least one test using a mocked HTTP response that verifies `IPMA.weather` returns a `WeatherData` instance with a non-None `temperature`.
34. `test/test_openmeteo.py` MUST contain at least one test using a mocked HTTP response that verifies `OpenMeteo.weather` returns a `WeatherData` instance with a non-None `temperature`, and that `OpenMeteo.hours` returns a non-empty list.
35. All tests MUST pass without making real network calls (use the `responses` library for HTTP mocking).

### CI
36. `.github/workflows/build_tests.yml` MUST use `actions/checkout@v4` and `actions/setup-python@v5`.
37. `.github/workflows/build_tests.yml` MUST run `pytest` as part of the CI build.
38. The `lichecker`-based license test step MUST be removed from CI.

## Non-Goals
- OVOS / voice assistant integration of any kind.
- Async (`asyncio`) support.
- CLI interface.
- Any providers beyond IPMA, Open-Meteo, and OWM (Weatherbit, Pirate Weather, Weather.gov, etc. are future work).
- Historical weather data retrieval.
- Weather alerts or warning objects beyond what appears in standard forecast responses.
- PyPI / package release process (manual or automated).
- Type annotations across the whole codebase (may be added incrementally later).

## Interfaces & Contracts

- **`WeatherProvider(lat, lon, date=None, units="metric", lang="en")`** — unchanged base constructor signature; all providers must accept these args.
- **`WeatherData`** — timestamped weather snapshot; fields: `datetime`, `temperature`, `apparentTemperature`, `humidity`, `cloudCover`, `pressure`, `windSpeed`, `windBearing`, `windGust`, `precipitation`, `snow`, `visibility`, `dewPoint`, `uvIndex`, `icon`, `summary`. All fields are `DataPoint` instances or `None`.
- **`DataPoint(name, value, units, ...)`** — scalar or range measurement; `as_dict()` returns a plain dict without mutating the instance.
- **`HourlyForecast(date, hours, weather)`** — iterable of `WeatherData` instances, one per hour.
- **`DailyForecast(date, days, weather)`** — iterable of `WeatherData` instances, one per day.
- **IPMA API** — `https://api.ipma.pt/open-data/` endpoints (no key); nearest-station lookup via `/observation/meteorology/stations/observations/` and daily forecast via `/forecast/meteorology/cities/daily/`.
- **Open-Meteo API** — `https://api.open-meteo.com/v1/forecast` (no key); `current_weather`, `hourly`, and `daily` fields used.
- **OWM API** — `https://api.openweathermap.org/data/2.5/` (key required); existing implementation retained, credential injection fixed.
- **`responses` library** — used exclusively in tests to intercept and mock HTTP calls; no real network access in CI.

## Acceptance Criteria

- [ ] `dp = DataPoint("temp", 20, "C"); dp.as_dict(); dp.as_dict()` does not raise and returns the same dict both times.
- [ ] `wd = WeatherData(); wd.temperature = DataPoint("temp", 20, "C"); wd.as_dict(); wd.as_dict()` does not raise and returns the same dict both times.
- [ ] `OWM(38.7, -9.1)` raises `ValueError` (no key provided).
- [ ] `OWM(38.7, -9.1, key="testkey")` with a mocked HTTP response returns a `WeatherData` with `temperature.value` set.
- [ ] `IPMA(38.7, -9.1)` with mocked HTTP responses returns a `WeatherData` with `temperature.value` set.
- [ ] `IPMA(51.5, -0.1)` raises `ValueError` (coordinates outside Portugal).
- [ ] `OpenMeteo(38.7, -9.1)` with mocked HTTP responses returns a `WeatherData` with `temperature.value` set and `len(provider.hours) > 0`.
- [ ] `OpenMeteo(38.7, -9.1)` with mocked HTTP responses returns `len(provider.days) >= 5`.
- [ ] All providers expose `dawn`, `dusk`, `sunrise`, `sunset`, `noon`, `moon_phase`, `moon_symbol`, `moon_phase_name` without error.
- [ ] `pytest` exits 0 with no network calls in a sandboxed environment.
- [ ] `pip install .` succeeds from the repo root on Python 3.10+.
- [ ] GitHub Actions CI passes on push with the updated workflow file.
- [ ] `grep -r "default_key\|key='jarbas'\|28fed" temporalis/` returns no matches.
