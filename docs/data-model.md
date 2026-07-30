# Data Model

All providers normalise their upstream API responses into the classes documented here.
Derived fields are filled automatically after parsing, see [Derived Fields](derived-fields.md).

---

## DataPoint

`temporalis/__init__.py:9`

A single measured or forecasted quantity. Every weather field on `WeatherData` is a
`DataPoint` or `None`.

```python
DataPoint(name, value, units,
          min_val=None, max_val=None,
          low_val=None, high_val=None,
          time=None, min_time=None, max_time=None,
          low_time=None, high_time=None,
          prob=None, prob_min=None, prob_max=None)
```

| Attribute | Type | Description |
|---|---|---|
| `name` | `str` | Human-readable label, e.g. `"Temperature"` |
| `value` | `float` or `None` | Central/current value |
| `units` | `str` | Unit string, e.g. `"ºC"`, `"hPa"`, `"%"` |
| `min_val` | `float` | Minimum (defaults to `value`) |
| `max_val` | `float` | Maximum (defaults to `value`) |
| `low_val` | `float` | Low value (defaults to `min_val`) |
| `high_val` | `float` | High value (defaults to `max_val`) |
| `time` | `pendulum.DateTime` | Timestamp of this observation |
| `min_time` | `pendulum.DateTime` | Predicted time of minimum |
| `max_time` | `pendulum.DateTime` | Predicted time of maximum |
| `prob` | `float` or `None` | Probability of the event (0–1) |
| `prob_min` | `float` or `None` | Probability at minimum |
| `prob_max` | `float` or `None` | Probability at maximum |

`__repr__` returns `"<value> <units>"`.

**Serialisation:**

- `DataPoint.as_dict()`, returns a dict, omitting `None` fields. `temporalis/__init__.py:39`
- `DataPoint.from_dict(data)`, reconstructs from a dict, returns `None` if input is falsy.
  Accepted dict keys: `value`, `min_val`/`min_value`, `max_val`/`max_value`, `prob`,
  `prob_min`/`min_prob`, `prob_max`/`max_prob`, `time`/`datetime`, `units`/`unit`.
  `temporalis/__init__.py:46`

---

## WeatherData

`temporalis/__init__.py:87`

A timestamped snapshot of weather conditions. Used for current observations and each
individual slot in hourly and daily forecasts.

| Attribute | Type | Description |
|---|---|---|
| `datetime` | `pendulum.DateTime` | Observation or forecast timestamp |
| `temperature` | `DataPoint` or `None` | Air temperature |
| `apparentTemperature` | `DataPoint` or `None` | Feels-like temperature |
| `humidity` | `DataPoint` or `None` | Relative humidity (%) |
| `cloudCover` | `DataPoint` or `None` | Cloud cover (%) |
| `dewPoint` | `DataPoint` or `None` | Dew point temperature |
| `pressure` | `DataPoint` or `None` | Atmospheric pressure (hPa) |
| `windSpeed` | `DataPoint` or `None` | Wind speed |
| `windBearing` | `DataPoint` or `None` | Wind direction (degrees) |
| `windGust` | `DataPoint` or `None` | Wind gust speed |
| `precipitation` | `DataPoint` or `None` | Precipitation amount or probability |
| `snow` | `DataPoint` or `None` | Snowfall |
| `visibility` | `DataPoint` or `None` | Visibility |
| `uvIndex` | `DataPoint` or `None` | UV index |
| `ozone` | `DataPoint` or `None` | Ozone |
| `summary` | `str` or `None` | Short text description |
| `icon` | `str` or `None` | Normalised icon slug (e.g. `"rain"`, `"clear"`) |

**Computed properties:**

- `WeatherData.timezone`, timezone name string from `datetime`, or `"UTC"` if unset.
  `temporalis/__init__.py:123`
- `WeatherData.weekday`, weekday name string (e.g. `"Monday"`), or `-1` if `datetime` is
  unset. `temporalis/__init__.py:129`

**Serialisation:**

- `WeatherData.as_dict()`, dict representation, omitting `None` fields. `temporalis/__init__.py:135`
- `WeatherData.from_dict(data)`, constructs from a dict of raw values and/or `DataPoint`
  instances. `temporalis/__init__.py:151`

**Printing:**

- `WeatherData.print()`, single-line summary to stdout.
- `WeatherData.pprint()`, pretty-printed dict to stdout.

---

## HourlyForecast

`temporalis/__init__.py:186`

Container for an ordered sequence of hourly `WeatherData` objects, plus a representative
`WeatherData` summarising the period.

```python
HourlyForecast(date, hours, weather)
```

| Attribute | Type | Description |
|---|---|---|
| `datetime` | `pendulum.DateTime` | Start of the forecast period |
| `hours` | `list[WeatherData]` | Hourly slots, ordered by time |
| `weather` | `WeatherData` | Representative conditions for the period |

- `HourlyForecast.summary`, delegates to `weather.summary`.
- `HourlyForecast.icon`, delegates to `weather.icon`.
- Supports iteration (`for hour in forecast`) and indexing (`forecast[n]`).

---

## DailyForecast

`temporalis/__init__.py:219`

Container for an ordered sequence of daily `WeatherData` objects.

```python
DailyForecast(date, days, weather)
```

| Attribute | Type | Description |
|---|---|---|
| `datetime` | `pendulum.DateTime` | Start of the forecast period |
| `days` | `list[WeatherData]` | Daily slots, ordered by date |
| `weather` | `WeatherData` | Representative conditions for the period |

- `DailyForecast.summary`, delegates to `weather.summary`.
- `DailyForecast.icon`, delegates to `weather.icon`.
- Supports iteration and indexing.

---

## MinutelyData and MinutelyForecast

`temporalis/__init__.py:252` / `temporalis/__init__.py:277`

`MinutelyData` holds a single one-minute precipitation snapshot.

| Attribute | Type | Description |
|---|---|---|
| `datetime` | `pendulum.DateTime` | Timestamp of this minute |
| `precipitation` | `DataPoint` or `None` | Precipitation intensity (mm/h) |
| `precipitation_probability` | `DataPoint` or `None` | Probability (0–1) |

`MinutelyForecast` is an ordered collection of `MinutelyData` objects. Supports `len()`,
iteration, and indexing. The base class `WeatherProvider.minutely` returns an empty
`MinutelyForecast` by default, `OWM` overrides it when One Call 3.0 data is available.

---

## WeatherProvider

`temporalis/providers/__init__.py:14`

Base class for all providers. Call `super().__init__(lat, lon, date, units, lang)` and then
populate `self.data` in `_request()`.

```python
WeatherProvider(lat, lon, date=None, units="metric", lang="en")
```

| Parameter | Type | Description |
|---|---|---|
| `lat` | `float` | Latitude in decimal degrees |
| `lon` | `float` | Longitude in decimal degrees |
| `date` | `pendulum.DateTime` or `None` | Reference datetime, defaults to current UTC time |
| `units` | `str` | `"metric"` (default), `"us"` / `"imperial"` / `"english"`, the latter three are normalised to `"us"` |
| `lang` | `str` | Language code for moon phase names |

**Forecast accessors** (all read from `self.data`):

| Property / Method | Returns | Source |
|---|---|---|
| `weather` | `WeatherData` | Current conditions after derived-field fill | `temporalis/providers/__init__.py:149` |
| `weather_tomorrow` | `WeatherData` | Shortcut for `weather_in_n_days(1)` | `temporalis/providers/__init__.py:155` |
| `weather_in_n_days(n)` | `WeatherData` | Day-N entry from `days`, raises `OverflowError` if out of range | `temporalis/providers/__init__.py:158` |
| `hourly` | `HourlyForecast` | All hourly slots, with derived fields | `temporalis/providers/__init__.py:164` |
| `hours` | `list[WeatherData]` | Flat list of hourly slots | `temporalis/providers/__init__.py:184` |
| `daily` | `DailyForecast` | All daily slots, with derived fields | `temporalis/providers/__init__.py:197` |
| `days` | `list[WeatherData]` | Flat list of daily slots | `temporalis/providers/__init__.py:215` |
| `minutely` | `MinutelyForecast` | Per-minute precipitation (empty unless overridden) | `temporalis/providers/__init__.py:188` |
| `alerts` | `list[dict]` | Active weather alerts, empty list if unsupported | `temporalis/providers/__init__.py:119` |
| `uv_index` | `float` or `None` | Numeric UV index from current weather | `temporalis/providers/__init__.py:110` |

**Sun properties** (computed via astral, timezone-aware `pendulum.DateTime`):
`dawn`, `sunrise`, `noon`, `sunset`, `dusk` (`temporalis/providers/__init__.py:71`)
**Moon properties** (`temporalis/providers/__init__.py:93`):

| Property | Returns |
|---|---|
| `moon_phase` | `float`, raw astral phase value (0–28) |
| `moon_code` | `int`, discrete phase 0–7 |
| `moon_symbol` | `str`, Unicode symbol |
| `moon_phase_name` | `str`, localised name in `self.lang` |

Moon phase names are available in: `en`, `nl`, `de`, `fr`, `es`, `pt`, `it`, `af`.

**Registry:**

| Class method | Description | Source |
|---|---|---|
| `WeatherProvider.register(name, cls)` | Add a provider to the registry | `temporalis/providers/__init__.py:313` |
| `WeatherProvider.get(name, lat, lon, **kwargs)` | Instantiate by name | `temporalis/providers/__init__.py:317` |
| `WeatherProvider.from_address(address, name, **kwargs)` | Geocode then instantiate by name | `temporalis/providers/__init__.py:325` |
| `WeatherProvider.available()` | Sorted list of registered names | `temporalis/providers/__init__.py:338` |
| `WeatherProvider.compare(names, lat, lon, **kwargs)` | Fetch same location from multiple providers | `temporalis/providers/__init__.py:281` |

**Shared HTTP session:**

`WeatherProvider.session` is a `requests.Session` shared across all instances.
Replace it before instantiating any provider to add caching:

```python
import requests_cache
from temporalis.providers import WeatherProvider
WeatherProvider.session = requests_cache.CachedSession(backend="memory", expire_after=3600)
```

---

## Icon Slugs

The `icon` field on `WeatherData` is a normalised string. Common values across all providers:

`clear`, `mostly-clear`, `partly-cloudy`, `clouds`, `fog`, `drizzle`, `freezing-drizzle`,
`rain`, `heavy-rain`, `showers`, `heavy-showers`, `freezing-rain`, `sleet`, `snow`,
`heavy-snow`, `snow-grains`, `snow-showers`, `thunderstorm`, `thunderstorm-hail`

---
[Home](../readme.md) · [Providers →](providers.md)
