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

## Class-level Cache

`WeatherProvider.session` — `temporalis/providers/__init__.py:15`

A `requests_cache.CachedSession` with a 1-hour in-memory TTL, shared across
all provider instances. Providers call `self.session.get(url)` to benefit
from caching automatically.

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

Geocodes `address` via Nominatim (falling back to the astral city database)
and returns a `WeatherProvider` instance. Each concrete provider overrides
this to return an instance of its own class.

Geocoding is implemented in `temporalis/location.py:6`:
1. Tries the astral built-in city database (`astral.geocoder.lookup`).
2. Falls back to Nominatim (OpenStreetMap). Raises `ValueError` if neither
   resolves.

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
