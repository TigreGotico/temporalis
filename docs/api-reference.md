# WeatherProvider API Reference

`temporalis/providers/__init__.py:13`

`WeatherProvider` is the base class for all providers. It holds the shared
in-memory cache, exposes all forecast accessors, and computes sun/moon data
from coordinates and date. Providers do not need to re-implement any of these.

---

## Constructor

```python
WeatherProvider(lat, lon, date=None, units="metric", lang="en")
```

| Parameter | Type | Description |
|---|---|---|
| `lat` | `float` | Latitude |
| `lon` | `float` | Longitude |
| `date` | `pendulum.DateTime` or `None` | Reference datetime (defaults to current UTC time) |
| `units` | `str` | `"metric"` (default), `"us"` / `"imperial"` / `"english"` → normalised to `"us"` |
| `lang` | `str` | Language code for moon phase names (see moon section) |

Providers normalise `units` further: OWM maps `"us"` to `"imperial"`;
OpenMeteo and MetNo apply conversion locally.

---

## Shared Session

`WeatherProvider.session` — `temporalis/providers/__init__.py`

A plain `requests.Session` shared across all provider instances. Providers
call `self.session.get(url)`. To add caching, replace the session before
instantiating any provider:

```python
import requests_cache
from temporalis.providers import WeatherProvider
WeatherProvider.session = requests_cache.CachedSession(backend="memory", expire_after=3600)
```

---

## Location Properties

| Property | Returns | Source |
|---|---|---|
| `latitude` | `float` | `temporalis/providers/__init__.py:104` |
| `longitude` | `float` | `temporalis/providers/__init__.py:108` |
| `timezone` | `str` | IANA timezone name via `timezonefinder` — `temporalis/providers/__init__.py:117` |
| `units` | `str` | Normalised unit mode — `temporalis/providers/__init__.py:100` |

---

## Static Factory

`WeatherProvider.from_address(address, key=None)` — `temporalis/providers/__init__.py:111`

Geocodes `address` and returns a base `WeatherProvider`. Each concrete
provider overrides this to return an instance of its own class, accepting the
same extra keyword arguments as its constructor.

Geocoding is implemented in `temporalis/location.py:6`:
1. Tries the astral built-in city database (`astral.geocoder.lookup`).
2. Falls back to Nominatim (OpenStreetMap). Raises `ValueError` if neither
   resolves.

Providers with `from_address()`: `OWM`, `OpenMeteo`, `OpenMeteoHistorical`,
`MetNo`, `IPMA`, `NWS` — all in their respective files under
`temporalis/providers/`.

---

## Provider Registry

`temporalis/providers/registry.py`

Importing `temporalis.providers.registry` auto-registers all six built-in
providers. The registry is stored as `WeatherProvider._registry`
(`temporalis/providers/__init__.py:238`).

### `WeatherProvider.register(name, cls)` — `temporalis/providers/__init__.py:241`

Adds `cls` to the registry under the lower-cased key `name`. Call this to
make a custom provider available via `get()`.

### `WeatherProvider.get(name, lat, lon, **kwargs)` — `temporalis/providers/__init__.py:244`

Instantiates the named provider with `(lat, lon, **kwargs)`. Raises
`ValueError` if `name` is not in the registry.

```python
wx = WeatherProvider.get("metno", 38.72, -9.14)
wx = WeatherProvider.get("openmeteo_historical", 48.85, 2.35,
                         start="2024-06-01", end="2024-06-30")
```

### `WeatherProvider.available()` — `temporalis/providers/__init__.py:265`

Returns a sorted list of registered provider names.

```python
WeatherProvider.available()
# ['ipma', 'metno', 'nws', 'openmeteo', 'openmeteo_historical', 'owm']
```

### `WeatherProvider.from_address(address, name, **kwargs)` — `temporalis/providers/__init__.py:252`

Registry-level geocoding factory. Delegates to the named provider's own
`from_address()` if it has one; otherwise geocodes and calls the constructor.

```python
wx = WeatherProvider.from_address("Oslo, Norway", name="metno")
```

---

## OpenMeteoHistorical

`temporalis/providers/openmeteo_historical.py:24`

Historical weather archive via the Open-Meteo archive API
(`https://archive-api.open-meteo.com/v1/archive`). Global coverage, no API
key required. Data is fetched on construction.

```python
OpenMeteoHistorical(lat, lon, start=None, end=None,
                    date=None, units="metric", lang="en")
```

| Parameter | Default | Description |
|---|---|---|
| `start` | yesterday | Start date as `"YYYY-MM-DD"` string |
| `end` | same as `start` | End date as `"YYYY-MM-DD"` string |

When `start` is omitted, it defaults to `pendulum.yesterday()` formatted as
`"YYYY-MM-DD"` (`temporalis/providers/openmeteo_historical.py:38`). When
`end` is omitted it equals `start`, so a single date is fetched.

Populates `daily` (temperature min/max, precipitation, wind, weather code)
and `hourly` (temperature, humidity, dew point, cloud cover, pressure, wind,
precipitation, snowfall, visibility). `currently` is set to the first daily
entry.

---

## Forecast Accessors

All accessors read from `self.data`, which providers populate in `_request()`.

| Property / Method | Returns | Description |
|---|---|---|
| `weather` | `WeatherData` | Current conditions — `temporalis/providers/__init__.py:122` |
| `weather_tomorrow` | `WeatherData` | Shortcut for `weather_in_n_days(1)` |
| `weather_in_n_days(n)` | `WeatherData` | Day-N forecast from the daily list; raises `OverflowError` if `n >= len(days)` |
| `hourly` | `HourlyForecast` | Full hourly forecast object — `temporalis/providers/__init__.py:135` |
| `hours` | `list[WeatherData]` | Flat list of hourly `WeatherData` slots |
| `daily` | `DailyForecast` | Full daily forecast object — `temporalis/providers/__init__.py:153` |
| `days` | `list[WeatherData]` | Flat list of daily `WeatherData` slots |

---

## Sun Properties

Computed via `astral` for the provider's coordinates and `self.datetime`.
All return timezone-aware `pendulum.DateTime` objects.

`temporalis/sun.py`

| Property | Description |
|---|---|
| `dawn` | Civil dawn |
| `sunrise` | Sunrise |
| `noon` | Solar noon |
| `sunset` | Sunset |
| `dusk` | Civil dusk |

---

## Moon Properties

Computed via `astral.moon` for `self.datetime`. `temporalis/moon.py`

| Property | Returns | Description |
|---|---|---|
| `moon_phase` | `float` | Raw astral phase value (0–28) |
| `moon_code` | `int` | Discrete phase code 0–7 (new → waning crescent) |
| `moon_symbol` | `str` | Unicode emoji for the phase (e.g. `"🌕"`) |
| `moon_phase_name` | `str` | Localised phase name in `self.lang` |

Supported languages for `moon_phase_name`: `en`, `nl`, `de`, `fr`, `es`,
`pt`, `it`, `af`. `temporalis/moon.py:5`

---

## Debug Printing

| Method | Description |
|---|---|
| `print()` | Prints current weather to stdout |
| `print_daily()` | Prints weekday, date, and summary for each day |
| `print_hourly()` | Prints weekday, time, and summary for each hour |
