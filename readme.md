# [Temporalis](https://en.wiktionary.org/wiki/temporalis#Adjective)

Temporalis is a weather library for Python. It queries several weather
services through one consistent API. It derives missing fields
automatically, supports marine forecasts, and offers an ensemble mode that
merges all free sources in parallel.

## Why another weather library?

Most Python weather packages wrap a single API. If you switch providers, you
rewrite your application. Temporalis keeps the provider as an implementation
detail.

Every provider (a global model, a national government API, or a free
open-data feed) returns the same objects: `WeatherData`, `DataPoint`,
`HourlyForecast`, `DailyForecast`. Your code never touches raw JSON.

### The data model

A temperature reading is not a plain float. It has a value, a unit, a
minimum, a maximum, a probability, and a timestamp. `DataPoint` holds all of
that in one object. It serializes cleanly and degrades gracefully when a
provider does not supply a field:

```python
temp = wx.weather.temperature
print(temp.value, temp.units)       # 18.5 ºC
print(temp.min_val, temp.max_val)   # daily range, if the provider supplies it
```

When a provider does not return dew point, apparent temperature, snow, or
UV index, Temporalis derives these fields from the data it has, using
standard meteorological formulas:

```python
wx = MetNo(lat, lon)
print(wx.weather.dewPoint)          # derived via August-Roche-Magnus
print(wx.weather.uvIndex)           # derived from solar position + cloud cover
print(wx.weather.snow)              # derived when T ≤ 2°C and precipitation > 0
```

Every provider also exposes `dawn`, `dusk`, `sunrise`, `sunset`, `noon`,
`moon_phase`, and `moon_phase_name`, computed from coordinates with `astral`.
No extra API call is needed.

You can swap providers without changing the rest of your code:

```python
# works identically for OWM, OpenMeteo, MetNo, IPMA, NWS, Ensemble
for day in wx.days:
    print(day.weekday, day.temperature, day.precipitation)
```

## Install

```bash
pip install temporalis
```

## Providers

| Provider | Coverage | API key | Notes |
|---|---|---|---|
| `Ensemble` | Global | None (OWM optional) | Merges all applicable sources in parallel |
| `OpenMeteo` | Global | None | Forecast + historical archive |
| `MetNo` | Global | None | Norwegian Met Institute |
| `OWM` | Global | Required | OpenWeatherMap, default key bundled |
| `NWS` | USA only | None | Raises `ValueError` outside US |
| `IPMA` | Portugal only | None | Raises `ValueError` outside PT |
| `OpenMeteoMarine` | Ocean | None | Wave, swell, current, raises `ValueError` for landlocked coords |
| `OpenMeteoAirQuality` | Global | None | PM2.5, ozone, pollen, NO₂ |

## Quick Start

### Single provider

```python
from temporalis.providers.openmeteo import OpenMeteo

lat, lon = 38.7223, -9.1393   # Lisbon
wx = OpenMeteo(lat, lon)

print(wx.weather.summary)
print(wx.weather.temperature)        # DataPoint: value + units
print(wx.weather.dewPoint)           # derived if provider doesn't supply it

for day in wx.days:
    print(day.weekday, day.datetime.date(), day.temperature)

for hour in wx.hours:
    print(hour.datetime.time(), hour.temperature, hour.precipitation)

# Sun times (astral, timezone-aware)
print(wx.dawn, wx.sunrise, wx.noon, wx.sunset, wx.dusk)

# Moon
print(wx.moon_symbol, wx.moon_phase_name)
```

### Ensemble: combine all free sources

```python
from temporalis.providers.ensemble import Ensemble

wx = Ensemble(lat, lon, units="metric")

print(wx.providers)          # ['openmeteo', 'metno', 'ipma', 'openmeteo_marine', ...]

w = wx.weather
print(w.temperature)         # mean across all providers
# min_val / max_val reflect inter-provider spread: wide means low confidence
print(w.temperature.min_val, w.temperature.max_val)

print(w.waveHeight)          # from OpenMeteoMarine when coastal
```

### Historical data

```python
from temporalis.providers.openmeteo import OpenMeteo
import pendulum

wx = OpenMeteo(lat, lon,
               start=pendulum.date(2024, 1, 1),
               end=pendulum.date(2024, 1, 31))
for day in wx.days:
    print(day.datetime.date(), day.temperature)
```

### Marine forecast

```python
from temporalis.providers.openmeteo_marine import OpenMeteoMarine

wx = OpenMeteoMarine(38.7, -9.5)   # must be over ocean
w = wx.weather
print(w.waveHeight, w.swellHeight, w.wavePeriod)
print(w.currentVelocity, w.currentDirection)
```

### Provider registry

```python
import temporalis.providers.registry   # auto-registers all built-ins
from temporalis.providers import WeatherProvider

print(WeatherProvider.available())
# ['ensemble', 'ipma', 'metno', 'nws', 'openmeteo', 'openmeteo_airquality',
#  'openmeteo_marine', 'owm']

wx = WeatherProvider.get("metno", lat, lon)
wx = WeatherProvider.from_address("Paris, France", name="openmeteo")
```

### Geocode from address

```python
wx = OpenMeteo.from_address("Berlin, Germany")
wx = Ensemble.from_address("Oslo, Norway")
```

## Units

Pass `units="metric"` (default) or `units="us"` to any provider constructor.
Each provider converts units locally. The API never exposes raw native units.

```python
wx_us = OpenMeteo(lat, lon, units="us")
print(wx_us.weather.temperature)   # ºF
print(wx_us.weather.windSpeed)     # mph
```

## Caching

Each provider instance owns its own `requests.Session`. To add caching, wrap
the session after construction:

```python
import requests_cache
wx = OpenMeteo(lat, lon)
wx.session = requests_cache.CachedSession("weather_cache", expire_after=600)
```

## Derived fields

Temporalis fills these fields automatically when a provider does not supply
them:

| Field | Formula | Inputs |
|---|---|---|
| `dewPoint` | August-Roche-Magnus | temp + humidity |
| `apparentTemperature` | Wind chill (T<10°C) or heat index (T>27°C) | temp + wind or humidity |
| `snow` | precipitation when T ≤ 2°C | temp + precipitation |
| `uvIndex` | NOAA solar position + Josefsson cloud attenuation | lat/lon + datetime + cloud cover |

See [docs/derived-fields.md](docs/derived-fields.md) for the formulas,
their valid ranges, and their accuracy limits.

## License

Apache 2.0
