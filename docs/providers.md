# Providers

All providers subclass `WeatherProvider` and share the same accessor interface
(`.weather`, `.hourly`, `.daily`, `.days`, `.hours`, `.alerts`, etc.).
Data is fetched from the upstream API on construction.

---

## OWM — OpenWeatherMap

`temporalis/providers/owm.py:17`

**Coverage:** Global.
**API key:** Required. A default bundled key is included for testing; supply your own
for production use.

```python
OWM(lat, lon, key=None, date=None, units="metric")
OWM.from_address(address, key=None)
```

| Parameter | Default | Description |
|---|---|---|
| `key` | bundled default | OpenWeatherMap API key |
| `units` | `"metric"` | `"metric"`, `"si"`, or `"us"` / `"imperial"` |

**What it fetches:**

- Current conditions via `/data/2.5/weather` — temperature, apparent temperature, humidity,
  pressure, cloud cover, visibility, wind speed, wind bearing, precipitation.
- 5-day / 3-hourly forecast via `/data/2.5/forecast` — same fields. Daily summaries are
  synthesised by averaging over the 3-hour slots that fall on the same calendar day.
- Per-minute precipitation via One Call 3.0 `/data/3.0/onecall` (requires a paid key).
  Silently skipped on 401/402 or missing radar coverage. `temporalis/providers/owm.py:314`

**Unit quirks:**

The OWM API's `units` parameter only affects temperature. Wind speed is always returned
in m/s and precipitation always in mm regardless of the `units` parameter. The provider
converts both locally when `units="us"` is requested. `temporalis/providers/owm.py:7`

| Field | API native | Converted for `units="us"` |
|---|---|---|
| Temperature | °C (metric), °F (imperial), K (si) | Already °F from API |
| Wind speed | always m/s | converted to mph locally |
| Precipitation | always mm | converted to inches locally |

**Alerts:** Not supported; `alerts` returns `[]`.

**Minutely:** Returns populated `MinutelyForecast` when a One Call 3.0 key is used and
radar coverage is available for the location. Each `MinutelyData` has `precipitation`
(mm/h or in/h). `temporalis/providers/owm.py:345`

---

## OpenMeteo — Open-Meteo

`temporalis/providers/openmeteo.py:59`

**Coverage:** Global.
**API key:** None required.

```python
OpenMeteo(lat, lon, date=None, units="metric", lang="en",
          start=None, end=None)
OpenMeteo.from_address(address, **kwargs)
```

| Parameter | Default | Description |
|---|---|---|
| `start` | `None` — forecast mode | Start date `"YYYY-MM-DD"` for archive mode |
| `end` | same as `start` | End date `"YYYY-MM-DD"`; single day when omitted |

When `start` is omitted the provider queries the live forecast API. When `start` is
supplied it queries the archive API (`https://archive-api.open-meteo.com/v1/archive`).
`temporalis/providers/openmeteo.py:110`

**What it fetches (forecast mode):**

- Current weather from `current_weather` block: temperature, wind speed/direction, icon.
- Hourly: temperature, apparent temperature, humidity, dew point, cloud cover, pressure,
  wind speed/direction/gust, precipitation (with probability), snowfall, visibility, weather code.
- Daily: temperature min/max, apparent temperature min/max, precipitation sum (with
  probability min/mean/max), wind speed max, wind gust max, dominant wind direction,
  UV index max.
- Current conditions are enriched from the nearest hourly entry after parsing (humidity,
  dew point, pressure, cloud cover, visibility, precipitation, UV index).
  `temporalis/providers/openmeteo.py:185`

**What it fetches (archive mode):**

- Historical hourly and daily data. `precipitation_probability`, `is_day`, and `uv_index_max`
  are not available from the archive API and are omitted. `currently` is set from the
  first daily entry.

**Unit handling:** The Open-Meteo API natively supports full unit control via request
parameters (`temperature_unit`, `windspeed_unit`, `precipitation_unit`). No local
conversion is needed. `temporalis/providers/openmeteo.py:90`

| Field | `units="metric"` | `units="us"` |
|---|---|---|
| Temperature | °C | °F |
| Wind speed | km/h | mph |
| Precipitation | mm | inch |

---

## MetNo — Norwegian Met Institute

`temporalis/providers/metno.py:43`

**Coverage:** Global.
**API key:** None required. A `User-Agent` header is mandatory and is sent automatically.
`temporalis/providers/metno.py:7`

```python
MetNo(lat, lon, date=None, units="metric", lang="en")
MetNo.from_address(address, **kwargs)
```

**What it fetches:**

- Hourly timeseries from `https://api.met.no/weatherapi/locationforecast/2.0/complete`.
  Each entry provides: temperature, dew point, humidity, cloud cover, pressure, wind
  speed/direction, precipitation (from the 1-hour or 6-hour block), UV index (clear-sky).
  `temporalis/providers/metno.py:86`
- Current conditions are set from the first timeseries entry.
- Daily summaries are synthesised from hourly entries grouped by calendar day: temperature
  min/max/average is computed; icon and summary come from the first entry of each day.

**Unit quirks:**

The Met.no API always returns temperatures in °C, wind in m/s, and precipitation in mm.
The provider converts locally. `temporalis/providers/metno.py:56`

| Field | API native | Converted for `units="us"` |
|---|---|---|
| Temperature | °C | °F (locally) |
| Wind speed | m/s | mph (locally) |
| Precipitation | mm | inches (locally) |

**Alerts:** Not supported; `alerts` returns `[]`.

**Note:** The UV index field from Met.no is `ultraviolet_index_clear_sky` — it represents
clear-sky conditions and does not account for cloud cover. The derived-field engine may
override it with a cloud-attenuated estimate if the provider value is absent.

---

## NWS — NOAA National Weather Service

`temporalis/providers/nws.py:48`

**Coverage:** United States only (contiguous US, Alaska, Hawaii approximate bounding box:
lat 15°–72°, lon -180° to -60°). Raises `ValueError` for coordinates outside this range.
`temporalis/providers/nws.py:50`

**API key:** None required. A `User-Agent` header is mandatory and is sent automatically.

```python
NWS(lat, lon, date=None, units="metric", lang="en")
NWS.from_address(address, **kwargs)
```

**What it fetches:**

1. `/points/{lat},{lon}` — resolves the grid office and forecast URLs for the location.
2. Hourly forecast (forecastHourly URL): temperature, humidity, dew point, wind speed/direction,
   precipitation probability.
3. Daily forecast (forecast URL): temperature high/low (day/night pairs merged into a
   single daily entry), wind speed/direction.
4. Active alerts from `/alerts/active?point={lat},{lon}`. `temporalis/providers/nws.py:248`

Alerts are dicts with keys: `event`, `severity`, `headline`, `description`, `onset`, `expires`.

**Unit quirks:**

The NWS API always returns temperatures in °F and wind speeds in mph. Dew point is an
exception — it is returned in °C from the API (`dewpoint.value`). The provider handles
each field's native unit independently. `temporalis/providers/nws.py:75`

| Field | API native | Converted for `units="metric"` |
|---|---|---|
| Temperature | °F | °C (locally) |
| Wind speed | mph | m/s (locally) |
| Dew point | °C | kept as °C; converted to °F for `units="us"` |
| Precipitation | probability only | no amount |

NWS does not provide precipitation amounts; the `precipitation` DataPoint on each hourly
entry has `value=None` and carries probability in `prob`. `temporalis/providers/nws.py:151`

Wind speed strings such as `"10 to 15 mph"` are parsed as the average of the range.
`temporalis/providers/nws.py:21`

**Limitations:** Cloud cover, pressure, visibility, and snow fields are not available from
the NWS API and will always be `None` (or filled by the derived-field engine where possible).

---

## IPMA — Portuguese Met Authority

`temporalis/providers/ipma.py:45`

**Coverage:** Portugal only (mainland + islands bounding box: lat 30°–43°, lon -32° to -6°).
Raises `ValueError` for coordinates outside this range. `temporalis/providers/ipma.py:86`

**API key:** None required.

```python
IPMA(lat, lon, date=None, units="metric", lang="en")
IPMA.from_address(address, **kwargs)
```

**What it fetches:**

- Current observations from the nearest IPMA weather station (from the stations JSON and
  the latest observation snapshot). Fields: temperature, humidity, pressure, wind speed,
  wind direction, accumulated precipitation. `temporalis/providers/ipma.py:101`
- 10-day daily forecast from city-level daily files, finding the nearest forecast point.
  Fields: temperature min/max, precipitation probability (no amount), wind speed class.
  `temporalis/providers/ipma.py:163`
- Active warnings from the IPMA warnings JSON. `temporalis/providers/ipma.py:227`

Alerts are dicts with keys: `event`, `severity`, `headline`, `description`, `onset`, `expires`.

**Unit quirks:**

IPMA observations use m/s for wind; IPMA forecast wind is given as a class code (1–5)
mapped to representative km/h speeds. The provider converts each independently.
`temporalis/providers/ipma.py:63`

| Field | API native | Converted for `units="us"` |
|---|---|---|
| Temperature | °C | °F (locally) |
| Wind (observations) | m/s | mph (locally) |
| Wind (forecast) | class → km/h | converted to mph (locally) |
| Precipitation (observations) | mm | inches (locally) |
| Precipitation (forecast) | probability only | no amount |

**Limitations:**

- Hourly forecast is not available from the IPMA open-data API. The `hours` property
  returns a list containing only the current observation.
- Forecast wind is a Beaufort-like class (1–5), not an exact measurement. The midpoint
  km/h values used are: `{1: 5, 2: 15, 3: 35, 4: 55, 5: 75}`. `temporalis/providers/ipma.py:12`
- IPMA sentinel values (typically -99) are filtered out and returned as `None`.
  `temporalis/providers/ipma.py:28`

---

## OpenMeteoAirQuality

`temporalis/providers/openmeteo_airquality.py:66`

**Coverage:** Global.
**API key:** None required.

```python
OpenMeteoAirQuality(lat, lon, date=None, units="metric", lang="en")
OpenMeteoAirQuality.from_address(address, **kwargs)
```

This provider queries the Open-Meteo Air Quality API (`https://air-quality-api.open-meteo.com/v1/air-quality`)
and returns `AirQualityData` objects rather than standard `WeatherData`. Standard forecast
accessors (`weather`, `days`, `hours`) are stubs — use the air-quality-specific accessors instead.

**Air-quality-specific accessors:**

| Property | Returns | Description |
|---|---|---|
| `current` | `AirQualityData` | Most recent reading (first hourly entry) |
| `air_quality_hours` | `list[AirQualityData]` | All hourly readings (~120 hours / 5 days) |

**`AirQualityData` fields** (all `DataPoint` or `None`):

| Attribute | Units |
|---|---|
| `pm10` | µg/m³ |
| `pm2_5` | µg/m³ |
| `ozone` | µg/m³ |
| `nitrogen_dioxide` | µg/m³ |
| `sulphur_dioxide` | µg/m³ |
| `carbon_monoxide` | µg/m³ |
| `dust` | µg/m³ |
| `ammonia` | µg/m³ |
| `european_aqi` | dimensionless |
| `us_aqi` | dimensionless |
| `uv_index` | dimensionless |
| `summary` | str — AQI label |

AQI labels (European index): `good` (0–20), `fair` (20–40), `moderate` (40–60),
`poor` (60–80), `very-poor` (80–100), `extremely-poor` (>100). `temporalis/providers/openmeteo_airquality.py:14`

Sun and moon properties are inherited from `WeatherProvider` and work normally.

---

## Provider Registry

`temporalis/providers/registry.py`

Import this module to auto-register all built-in providers:

```python
import temporalis.providers.registry
from temporalis.providers import WeatherProvider

print(WeatherProvider.available())
# ['ipma', 'metno', 'nws', 'openmeteo', 'openmeteo_airquality', 'owm']

wx = WeatherProvider.get("metno", 38.72, -9.14)
wx = WeatherProvider.from_address("Oslo, Norway", name="openmeteo")
```

Register a custom provider:

```python
WeatherProvider.register("myprovider", MyProvider)
```
