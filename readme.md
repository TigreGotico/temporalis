# [Temporalis](https://en.wiktionary.org/wiki/temporalis#Adjective)

Unified weather abstraction library for Python. Query five different weather
services through one consistent API, with built-in sun and moon data.

## Install

```bash
pip install temporalis
```

## Providers

| Provider | Coverage | API key | Notes |
|---|---|---|---|
| `OWM` | Global | Required (default bundled) | OpenWeatherMap |
| `OpenMeteo` | Global | None | Open-Meteo |
| `MetNo` | Global | None | Norwegian Met Institute |
| `IPMA` | Portugal only | None | Raises `ValueError` outside PT |
| `NWS` | USA only | None | Raises `ValueError` outside US |

## Quick Start

All providers share the same interface. Swap the class to change the source.

```python
from temporalis.providers.openmeteo import OpenMeteo

lat, lon = 38.7223, -9.1393   # Lisbon
wx = OpenMeteo(lat, lon)

# Current conditions
print(wx.weather.summary)
print(wx.weather.temperature)   # DataPoint: value + units

# Daily and hourly forecasts
for day in wx.days:
    print(day.weekday, day.datetime.date(), day.summary)

for hour in wx.hours:
    print(hour.datetime.time(), hour.temperature)

# Sun times (astral, timezone-aware)
print(wx.dawn, wx.sunrise, wx.noon, wx.sunset, wx.dusk)

# Moon
print(wx.moon_symbol, wx.moon_phase_name)   # e.g. "🌔 Waxing gibbous"
```

### Geocode from address

```python
wx = OpenMeteo.from_address("Berlin, Germany")
```

### OpenWeatherMap (API key)

```python
from temporalis.providers.owm import OWM

wx = OWM(lat, lon)             # uses bundled default key
wx = OWM(lat, lon, key="...")  # supply your own
```

### Portugal — IPMA

```python
from temporalis.providers.ipma import IPMA

wx = IPMA(38.7223, -9.1393)
# raises ValueError if coordinates are outside Portugal's bounding box
```

### USA — NWS / Weather.gov

```python
from temporalis.providers.nws import NWS

wx = NWS(40.7128, -74.0060)   # New York
# raises ValueError if coordinates are outside the USA
```

### Met.no

```python
from temporalis.providers.metno import MetNo

wx = MetNo(lat, lon)
```

## Units

Pass `units="metric"` (default) or `units="us"` / `units="imperial"` to any
provider constructor. Met.no always returns SI from the API; unit conversion is
applied locally.

## Configuration

Responses are cached in memory for 1 hour via `requests-cache`. The cache is a
class-level `CachedSession` shared across all provider instances
(`WeatherProvider.session` — `temporalis/providers/__init__.py:15`).

## License

Apache 2.0
