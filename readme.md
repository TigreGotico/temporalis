# [Temporalis](https://en.wiktionary.org/wiki/temporalis#Adjective)

Unified weather abstraction library for Python. Query five different weather
services through one consistent API, with built-in sun and moon data.

## Why another weather library?

Most Python weather packages are thin wrappers around a single API. Switch
providers and you rewrite your whole application. Temporalis solves a different
problem: **make the provider an implementation detail**.

Every provider — whether it's a global commercial service, a national government
API, or a free open-data feed — returns the same objects: `WeatherData`,
`DataPoint`, `HourlyForecast`, `DailyForecast`. Your code never touches raw JSON.

### The data model earns its keep

**`DataPoint` is not a float.** A temperature reading has a value, but it also
has a unit, a min, a max, a probability, and a timestamp. A wind speed has a
unit that differs between providers. `DataPoint` captures all of that in one
object that serialises cleanly and degrades gracefully when a provider doesn't
supply a field:

```python
temp = wx.weather.temperature
print(temp.value, temp.units)       # 18.5 ºC
print(temp.min_val, temp.max_val)   # daily range, if the provider supplies it
```

**Sun and moon are first-class, not bolted on.** Every provider exposes `dawn`,
`dusk`, `sunrise`, `sunset`, `noon`, `moon_phase`, and `moon_phase_name` with no
extra API call and no extra key — computed from coordinates via `astral`. Moon
phase names are available in eight languages.

**Swap providers without changing your code:**

```python
# works identically for OWM, OpenMeteo, MetNo, IPMA, NWS
for day in wx.days:
    print(day.weekday, day.temperature, day.precipitation)
```

**Select by name at runtime**, not by import path:

```python
import temporalis.providers.registry   # registers all built-ins
from temporalis.providers import WeatherProvider

wx = WeatherProvider.get("metno", lat, lon)
print(WeatherProvider.available())
# ['ipma', 'metno', 'nws', 'openmeteo', 'openmeteo_historical', 'owm']
```

## Install

```bash
pip install temporalis
```

## Providers

| Provider | Coverage | API key | Notes |
|---|---|---|---|
| `OWM` | Global | Required (default bundled) | OpenWeatherMap |
| `OpenMeteo` | Global | None | Open-Meteo forecast |
| `OpenMeteoHistorical` | Global | None | Open-Meteo archive; date range required |
| `MetNo` | Global | None | Norwegian Met Institute |
| `IPMA` | Portugal only | None | Raises `ValueError` outside PT |
| `NWS` | USA only | None | Raises `ValueError` outside US |

All providers can be instantiated by name through the registry — see
[Provider Registry](docs/api-reference.md#provider-registry) for details.

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

All providers support `from_address()`:

```python
wx = OpenMeteo.from_address("Berlin, Germany")
wx = MetNo.from_address("Oslo, Norway")
wx = IPMA.from_address("Lisbon, Portugal")
wx = NWS.from_address("New York, USA")
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

### Historical data — Open-Meteo archive

```python
from temporalis.providers.openmeteo_historical import OpenMeteoHistorical

# Single day (default: yesterday)
wx = OpenMeteoHistorical(lat, lon)

# Explicit date range
wx = OpenMeteoHistorical(lat, lon, start="2024-01-01", end="2024-01-31")
for day in wx.days:
    print(day.datetime.date(), day.temperature)
```

### Provider registry

```python
from temporalis.providers.registry import *   # auto-registers all built-ins
from temporalis.providers import WeatherProvider

# List available names
print(WeatherProvider.available())
# ['ipma', 'metno', 'nws', 'openmeteo', 'openmeteo_historical', 'owm']

# Instantiate by name
wx = WeatherProvider.get("metno", 38.72, -9.14)

# Geocode by name
wx = WeatherProvider.from_address("Paris, France", name="openmeteo")

# Register a custom provider
WeatherProvider.register("myprovider", MyProvider)
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
