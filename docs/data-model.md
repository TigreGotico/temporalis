# Data Model Reference

All providers normalise their upstream API responses into these four classes.

---

## DataPoint

`temporalis/__init__.py:6`

A single measured or forecasted quantity.

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
| `value` | `float` | Central/current value |
| `units` | `str` | Unit string, e.g. `"ºC"`, `"hPa"`, `"%"` |
| `min_val` | `float` | Minimum value (defaults to `value`) |
| `max_val` | `float` | Maximum value (defaults to `value`) |
| `low_val` | `float` | Low value (defaults to `min_val`) |
| `high_val` | `float` | High value (defaults to `max_val`) |
| `time` | `datetime` | Timestamp of observation/prediction |
| `min_time` | `datetime` | Predicted time of minimum |
| `max_time` | `datetime` | Predicted time of maximum |
| `prob` | `float` | Probability of `value` (0–1) |
| `prob_min` | `float` | Probability at minimum |
| `prob_max` | `float` | Probability at maximum |

`__repr__` returns `"<value> <units>"`.

**Serialisation:**
- `DataPoint.as_dict()` — returns a dict, omitting `None` fields.
- `DataPoint.from_dict(data)` — reconstructs from a dict or returns `None` if input is falsy. Accepts keys `value`, `min_val`/`min_value`, `max_val`/`max_value`, `prob`, `prob_min`/`min_prob`, `prob_max`/`max_prob`, `time`/`datetime`, `units`/`unit`. `temporalis/__init__.py:41`

---

## WeatherData

`temporalis/__init__.py:80`

A timestamped snapshot of weather conditions. Used for both current
observations and individual hourly or daily slots.

| Attribute | Type | Description |
|---|---|---|
| `datetime` | `pendulum.DateTime` | Observation or forecast timestamp |
| `temperature` | `DataPoint` or `None` | Temperature |
| `apparentTemperature` | `DataPoint` or `None` | Feels-like temperature |
| `humidity` | `DataPoint` or `None` | Relative humidity (%) |
| `cloudCover` | `DataPoint` or `None` | Cloud cover (%) |
| `dewPoint` | `DataPoint` or `None` | Dew point temperature |
| `pressure` | `DataPoint` or `None` | Atmospheric pressure (hPa) |
| `windSpeed` | `DataPoint` or `None` | Wind speed |
| `windBearing` | `DataPoint` or `None` | Wind direction (degrees or compass) |
| `windGust` | `DataPoint` or `None` | Wind gust speed |
| `precipitation` | `DataPoint` or `None` | Precipitation (mm or probability %) |
| `snow` | `DataPoint` or `None` | Snowfall |
| `visibility` | `DataPoint` or `None` | Visibility |
| `uvIndex` | `DataPoint` or `None` | UV index |
| `ozone` | `DataPoint` or `None` | Ozone |
| `summary` | `str` or `None` | Short text description |
| `icon` | `str` or `None` | Normalised icon slug (e.g. `"rain"`, `"clear"`) |

**Computed properties:**
- `WeatherData.timezone` — timezone name string from `datetime`, or `"UTC"` if unset.
- `WeatherData.weekday` — weekday name string, or `-1` if `datetime` is unset.

**Serialisation:**
- `WeatherData.as_dict()` — dict representation, omitting `None` fields.
- `WeatherData.from_dict(data)` — constructs from a dict. `temporalis/__init__.py:143`

**Printing:**
- `WeatherData.print()` — single-line summary to stdout.
- `WeatherData.pprint()` — pretty-printed dict to stdout.

---

## HourlyForecast

`temporalis/__init__.py:179`

Container for an ordered sequence of hourly `WeatherData` objects plus a
representative `WeatherData` for the period as a whole.

```python
HourlyForecast(date, hours, weather)
```

| Attribute | Type | Description |
|---|---|---|
| `datetime` | `pendulum.DateTime` | Start of the forecast period |
| `hours` | `list[WeatherData]` | Hourly slots, ordered by time |
| `weather` | `WeatherData` | Representative conditions for the period |

- `HourlyForecast.summary` — delegates to `weather.summary`.
- `HourlyForecast.icon` — delegates to `weather.icon`.
- Supports iteration (`for hour in forecast`) and indexing (`forecast[n]`).

---

## DailyForecast

`temporalis/__init__.py:212`

Container for an ordered sequence of daily `WeatherData` objects.

```python
DailyForecast(date, days, weather)
```

| Attribute | Type | Description |
|---|---|---|
| `datetime` | `pendulum.DateTime` | Start of the forecast period |
| `days` | `list[WeatherData]` | Daily slots, ordered by date |
| `weather` | `WeatherData` | Representative conditions for the period |

- `DailyForecast.summary` — delegates to `weather.summary`.
- `DailyForecast.icon` — delegates to `weather.icon`.
- Supports iteration and indexing.

---

## Icon Slugs

The `icon` field on `WeatherData` is a normalised string produced by each
provider. Common values across all providers:

`clear`, `mostly-clear`, `partly-cloudy`, `clouds`, `fog`, `drizzle`,
`rain`, `heavy-rain`, `showers`, `heavy-showers`, `freezing-rain`,
`freezing-drizzle`, `sleet`, `snow`, `heavy-snow`, `snow-grains`,
`snow-showers`, `thunderstorm`, `thunderstorm-hail`
