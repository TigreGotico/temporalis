# Plan: Revive temporalis — core fixes + IPMA + Open-Meteo providers

## Approach
Work in four logical phases applied sequentially: (1) fix bugs and remove dead code in the existing codebase so subsequent work has a clean foundation, (2) add the IPMA provider, (3) add the Open-Meteo provider, (4) modernise packaging and add the test suite + CI. Each phase produces a discrete commit. No new abstractions are added beyond what the existing `WeatherProvider` base class already provides — both new providers are plain subclasses following the OWM pattern.

## Architecture / Data Flow

```
User code
   │
   ├── OWM(lat, lon, key=...)      ─┐
   ├── IPMA(lat, lon)               ├── WeatherProvider (base)
   └── OpenMeteo(lat, lon)         ─┘
            │
            │  subclass calls self.session.get(url) → raw JSON
            │  maps JSON fields → DataPoint instances
            │  writes self.data["currently"] / ["daily"] / ["hourly"]
            │
            └── inherited properties:
                  .weather        → WeatherData (from self.data["currently"])
                  .daily          → DailyForecast (from self.data["daily"])
                  .hourly         → HourlyForecast (from self.data["hourly"])
                  .days / .hours  → lists of WeatherData
                  .dawn/.dusk/... → astral (computed from lat/lon, no API)
                  .moon_phase/... → astral (computed from datetime, no API)
```

**IPMA data flow:**
1. Fetch all-stations observation JSON (`/observation/meteorology/stations/observations.json`) — timestamped dict keyed by station ID.
2. Fetch station metadata list (`/observation/meteorology/stations/stations.json`) — GeoJSON features with coordinates and `idEstacao`.
3. Find nearest station to `(lat, lon)` by Euclidean distance on lat/lon.
4. Map station observation fields → `self.data["currently"]`.
5. Fetch daily forecast for days 0–4 (`/forecast/meteorology/cities/daily/hp-daily-forecast-day{N}.json`), find nearest city by lat/lon each time → `self.data["daily"]`.
6. IPMA has no public hourly endpoint — `self.data["hourly"]` is populated with the same `WeatherData` as `"currently"` (mirrors OWM fallback pattern).

**Open-Meteo data flow:**
1. Single request to `https://api.open-meteo.com/v1/forecast` with `current_weather=true`, `hourly=...`, `daily=...`.
2. Map `current_weather` dict → `self.data["currently"]`.
3. Map `hourly` parallel arrays (zip by index) → list of `WeatherData` dicts → `self.data["hourly"]["data"]`.
4. Map `daily` parallel arrays → list of `WeatherData` dicts → `self.data["daily"]["data"]`.

## Implementation Steps

1. **Fix `as_dict()` mutation bug** — In `temporalis/__init__.py`: change `data = self.__dict__` to `data = dict(self.__dict__)` in both `DataPoint.as_dict()` and `WeatherData.as_dict()`. Replace all bare `except:` with `except Exception`.

2. **Remove dead code and credentials** — Delete `temporalis/providers/darksky.py` and `temporalis/xml.py`. Remove `OWM.default_key`; make `key` a required arg (raise `ValueError` if absent). Remove `from_address` references to `default_key`.

3. **Clean up geocoding (`location.py`)** — Remove the 8-provider `geocoder` fallback chain; replace with single Nominatim lookup (`user_agent="temporalis"`). Remove `Yandex` import. Remove `geocoder` import entirely. Keep `reverse_geolocate` using `Nominatim(user_agent="temporalis")`.

4. **Add IPMA provider** — Create `temporalis/providers/ipma.py`. Implement coordinate bounding-box validation (lat 36–42°N, lon 6–10°W). Fetch station list and latest observations; find nearest station by Euclidean distance on lat/lon; map Portuguese field names (`temperatura`, `humidade`, `pressao`, `intensidadeVento`, `precAcumulada`) to `DataPoint` instances; populate `self.data["currently"]`. Fetch 5 daily forecast JSONs (day 0–4); find nearest city by lat/lon each day; map fields (`tMin`, `tMax`, `precipitaProb`, `classWindSpeed`, `idWeatherType`) to `WeatherData`-compatible dict; populate `self.data["daily"]`. Set `self.data["hourly"]` to the same structure as `"currently"` (no IPMA hourly endpoint exists).

5. **Add Open-Meteo provider** — Create `temporalis/providers/openmeteo.py`. Map `units` arg to Open-Meteo parameter strings (`celsius`/`fahrenheit`, `kmh`/`mph`, `mm`/`inch`). Make a single request with `current_weather=true` plus hourly and daily param lists (ported from ovos-weather-skill `openmeteo.py`, stripped of OVOS deps). Zip daily parallel arrays into `WeatherData` dicts; zip hourly arrays into `WeatherData` dicts. Populate `self.data["currently"]`, `["daily"]`, `["hourly"]` in the same structure as OWM uses.

6. **Migrate packaging to `pyproject.toml`** — Write `pyproject.toml` with `[project]`, `python_requires=">=3.10"`, pinned deps (`pendulum>=2,<3`, `astral>=3,<4`, `requests-cache>=1,<2`, `timezonefinder`, `geopy`, `requests`). Remove `pytz`, `python-dateutil`, `geocoder` from deps. Delete `setup.py`.

7. **Write tests** — Add `test/test_data_model.py` (mutation bug regression, `DataPoint` and `WeatherData`). Add `test/test_owm.py`, `test/test_ipma.py`, `test/test_openmeteo.py` — each using `responses` to mock HTTP calls, asserting `provider.weather.temperature` is not None and key list properties are non-empty.

8. **Update CI** — Rewrite `.github/workflows/build_tests.yml`: use `actions/checkout@v4`, `actions/setup-python@v5`, Python 3.10+, `pip install .[test]`, `pytest test/`. Remove license test step. Delete `test/license_tests.py`.
