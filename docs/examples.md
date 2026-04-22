# Examples

---

## Current weather via the registry

```python
import temporalis.providers.registry  # registers all built-in providers
from temporalis.providers import WeatherProvider

lat, lon = 38.72, -9.14  # Lisbon

wx = WeatherProvider.get("openmeteo", lat, lon)
w = wx.weather

print(w.summary)
print(w.temperature)           # e.g. "18.5 ºC"
print(w.temperature.value)     # 18.5
print(w.temperature.units)     # "ºC"
print(w.apparentTemperature)
print(w.humidity)
print(w.windSpeed)
print(w.pressure)
print(w.cloudCover)
print(wx.uv_index)             # float or None
```

`examples/01_basic_forecast.py`

---

## Hourly forecast loop

```python
wx = WeatherProvider.get("openmeteo", lat, lon)

for hour in wx.hours[:24]:
    print(hour.datetime.format("HH:mm"),
          hour.summary,
          hour.temperature,
          hour.precipitation)
```

Access the full `HourlyForecast` object (with `.summary` and `.icon` for the period):

```python
forecast = wx.hourly
print(forecast.summary, forecast.icon)
for hour in forecast:
    print(hour.datetime, hour.temperature)
```

---

## Daily forecast loop

```python
wx = WeatherProvider.get("metno", lat, lon)

for day in wx.days:
    t = day.temperature
    print(
        day.weekday,
        day.datetime.date(),
        day.summary,
        f"{t.min_val:.0f}–{t.max_val:.0f} {t.units}"
    )
```

`min_val` and `max_val` are set by providers that supply a daily temperature range
(OpenMeteo, MetNo, NWS, IPMA). For providers that only return a single value, both
default to `value`.

---

## Sun and moon

```python
wx = WeatherProvider.get("openmeteo", lat, lon)

print(wx.dawn)
print(wx.sunrise)
print(wx.noon)
print(wx.sunset)
print(wx.dusk)

print(wx.moon_symbol, wx.moon_phase_name)   # e.g. "🌔 Waxing gibbous"
print(f"{wx.moon_phase:.0%}")               # e.g. "54%"
```

All sun times are timezone-aware `pendulum.DateTime` objects. Moon phase names
are available in `en`, `nl`, `de`, `fr`, `es`, `pt`, `it`, `af` via the `lang`
constructor parameter.

---

## Geocode from an address

All providers expose `from_address()`:

```python
from temporalis.providers.openmeteo import OpenMeteo
from temporalis.providers.metno import MetNo
from temporalis.providers.ipma import IPMA
from temporalis.providers.nws import NWS

wx = OpenMeteo.from_address("Berlin, Germany")
wx = MetNo.from_address("Oslo, Norway")
wx = IPMA.from_address("Lisbon, Portugal")
wx = NWS.from_address("New York, USA")
```

Via the registry:

```python
wx = WeatherProvider.from_address("Paris, France", name="openmeteo")
```

`examples/03_from_address.py`

---

## Comparing providers

`WeatherProvider.compare()` fetches the same location from multiple providers and
returns a dict keyed by provider name. `temporalis/providers/__init__.py:281`

```python
results = WeatherProvider.compare(["openmeteo", "metno", "owm"], lat, lon)

for name, data in results.items():
    if "error" in data:
        print(name, "ERROR:", data["error"])
    else:
        print(name,
              data["temperature"],
              data["summary"],
              "UV:", data["uv_index"])
```

Each entry contains: `temperature`, `summary`, `humidity`, `wind_speed`,
`precipitation`, `uv_index`, `alerts`, `provider` (the `WeatherProvider` instance).

---

## Checking derived fields

Derived fields are filled automatically. To inspect whether a value was derived:

```python
wx = WeatherProvider.get("nws", 40.71, -74.01)  # NWS does not supply dew point
w = wx.weather

# dewPoint will be derived from temperature + humidity if both are present
if w.dewPoint is not None:
    print("dew point:", w.dewPoint)

# apparentTemperature is replaced when the provider echoes plain temperature
print("apparent:", w.apparentTemperature)
print("temperature:", w.temperature)
```

To run the derivation manually on a `WeatherData` object:

```python
from temporalis.derived import fill_derived
from temporalis import WeatherData, DataPoint

wd = WeatherData()
wd.temperature = DataPoint("Temperature", 25.0, "ºC")
wd.humidity = DataPoint("Humidity", 80.0, "%")
wd.windSpeed = DataPoint("WindSpeed", 10.0, "km/h")

fill_derived(wd, lat=38.72, lon=-9.14)  # also fills uvIndex if datetime is set
print(wd.dewPoint)
print(wd.apparentTemperature)
```

---

## US units

```python
from temporalis.providers.openmeteo import OpenMeteo

wx = OpenMeteo(38.72, -9.14, units="us")
w = wx.weather

print(w.temperature)    # e.g. "65.3 ºF"
print(w.windSpeed)      # e.g. "8.7 mph"
print(w.precipitation)  # e.g. "0.04 inch"
```

---

## OpenWeatherMap with a custom key

```python
from temporalis.providers.owm import OWM

wx = OWM(38.72, -9.14, key="your_api_key_here")
print(wx.weather)
```

---

## Per-minute precipitation (OWM One Call 3.0)

```python
from temporalis.providers.owm import OWM

wx = OWM(38.72, -9.14, key="your_onecall3_key")
for minute in wx.minutely:
    print(minute.datetime.format("HH:mm"), minute.precipitation)
```

An empty `MinutelyForecast` is returned when the key does not include One Call 3.0
or when the location has no radar coverage.

---

## Historical data (Open-Meteo archive)

```python
from temporalis.providers.openmeteo import OpenMeteo

# Single day
wx = OpenMeteo(48.85, 2.35, start="2024-07-04")
for day in wx.days:
    print(day.datetime.date(), day.temperature)

# Date range
wx = OpenMeteo(48.85, 2.35, start="2024-01-01", end="2024-01-31")
for hour in wx.hours:
    print(hour.datetime, hour.temperature, hour.precipitation)
```

`examples/06_historical.py`

---

## Air quality

```python
from temporalis.providers.openmeteo_airquality import OpenMeteoAirQuality

aq = OpenMeteoAirQuality(38.72, -9.14)

current = aq.current
print(current.european_aqi, current.summary)  # e.g. "12 good"
print(current.pm2_5)
print(current.ozone)

for hour in aq.air_quality_hours[:24]:
    print(hour.datetime.format("HH:mm"), hour.european_aqi, hour.summary)
```

`examples/05_air_quality.py`

---

## Weather alerts

```python
wx = WeatherProvider.get("nws", 40.71, -74.01)

for alert in wx.alerts:
    print(alert["event"], alert["severity"])
    print(alert["headline"])
    print("onset:", alert["onset"], "expires:", alert["expires"])
```

Alerts are also supported by IPMA. All other providers return `[]`.

`examples/07_alerts.py`

---

## Custom HTTP session (caching)

```python
import requests_cache
from temporalis.providers import WeatherProvider

WeatherProvider.session = requests_cache.CachedSession(
    backend="memory",
    expire_after=3600,
)

# All subsequent provider instances use the cached session
wx = WeatherProvider.get("openmeteo", 38.72, -9.14)
```
