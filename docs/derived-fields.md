# Derived Fields

`temporalis/derived.py`

When a provider does not supply a field, temporalis fills it automatically using
meteorological approximations. This happens via `fill_derived()`, which is called by
`WeatherProvider.weather`, `WeatherProvider.hourly`, and `WeatherProvider.daily` before
returning data to the caller. `temporalis/derived.py:226`

**Rules:**

- Existing non-`None` values are never overwritten.
- Apparent temperature is an exception: it is also replaced when the provider echoes the
  plain temperature as the apparent temperature (value equality check). `temporalis/derived.py:243`
- All formulas operate internally in °C and km/h. Unit-aware helpers convert `DataPoint`
  values before computation and convert results back to the original unit before returning.

---

## Dew Point

`temporalis/derived.py:53` (`approx_dew_point(temp_dp, humidity_dp)`)
**Condition:** `WeatherData.dewPoint is None` and both `temperature` and `humidity` are present.

**Formula (August-Roche-Magnus approximation):**

```
alpha = ln(RH / 100) + (17.625 * T) / (243.04 + T)
Td    = (243.04 * alpha) / (17.625 - alpha)
```

where T is temperature in °C and RH is relative humidity in %.

**Inputs:**

- Temperature: any unit (`ºC`, `ºF`, `K`), normalised to °C before computation.
  `temporalis/derived.py:17`
- Humidity: `%`, taken as-is.

**Output:** `DataPoint` in the same temperature units as the input temperature.

**Valid range:** −40 °C < T < 60 °C, 1 % < RH ≤ 100 %.
The implementation clamps RH to [1, 100] before applying the formula. `temporalis/derived.py:65`

**Accuracy:** Error < 0.4 °C within the valid range.

**Limitations:** Accuracy degrades outside the valid temperature range. The formula is an
approximation of the full Magnus equation, it does not account for pressure or altitude.

---

## Apparent Temperature

`temporalis/derived.py:74` (`approx_apparent_temp(temp_dp, humidity_dp, wind_dp)`)
**Condition:** `WeatherData.apparentTemperature is None`, or its value equals the plain
temperature (provider echo detection). `temporalis/derived.py:241`

Two formulas are applied depending on conditions. Neither is applied for the moderate
range (10 °C–27 °C with low wind or low humidity).

### Wind chill (T < 10 °C and V > 3 km/h)

Environment Canada 2001 formula:

```
WC = 13.12 + 0.6215 * T - 11.37 * V^0.16 + 0.3965 * T * V^0.16
```

where T is temperature in °C and V is wind speed in km/h.

`temporalis/derived.py:94`

**Valid range:** T < 10 °C, V > 3 km/h.

### Heat index (T > 27 °C and RH >= 40 %)

Rothfuss-Jakobs polynomial in T (°C) and RH (%):

```
HI = -8.78469475556
     + 1.61139411 * T
     + 2.33854883889 * RH
     - 0.14611605 * T * RH
     - 0.012308094 * T^2
     - 0.0164248277778 * RH^2
     + 0.002211732 * T^2 * RH
     + 0.00072546 * T * RH^2
     - 0.000003582 * T^2 * RH^2
```

`temporalis/derived.py:101`

**Valid range:** T > 27 °C, RH ≥ 40 %.

**Output:** `DataPoint` in the same temperature units as the input temperature, or `None`
when neither formula's conditions are met.

**Limitations:**

- No formula is applied in the moderate range (10 °C–27 °C) or at low wind + low humidity,
  so `apparentTemperature` may remain equal to the plain temperature in those conditions.
- Wind chill does not account for solar radiation.
- Heat index is based on shaded, sea-level conditions, accuracy decreases at altitude or
  in direct sunlight.

---

## Snow

`temporalis/derived.py:208` (`approx_snow(temp_dp, precip_dp)`)
**Condition:** `WeatherData.snow is None` and both `temperature` and `precipitation` are present.

**Rule:** If temperature ≤ 2 °C and `precipitation.value > 0`, then `snow` is set equal to
`precipitation` (water equivalent, same value and units).

**Limitations:**

- The 2 °C threshold is a heuristic. In reality, mixed precipitation (rain and snow) is
  common between 0 °C and 4 °C depending on air mass depth and surface albedo.
- No rain/snow ratio is applied, the full precipitation amount is treated as snow water
  equivalent.
- This field is only filled when the provider does not supply a snow value. Providers that
  return snow directly (e.g. OpenMeteo with `snowfall`) will not be overridden.

---

## UV Index

`temporalis/derived.py:179` (`approx_uv_index(lat, lon, dt, cloud_cover_dp)`)
**Condition:** `WeatherData.uvIndex is None` and `lat`, `lon`, and `datetime` are available.
`temporalis/derived.py:257`

UV index estimation requires coordinates and a timezone-aware datetime. Both are supplied
automatically by `WeatherProvider`.

**Clear-sky UV (WMO simplified model):**

```
UV_clear = 12 * max(cos(SZA), 0)^0.75
```

where SZA is the solar zenith angle in degrees. `temporalis/derived.py:197`

**Cloud attenuation (Josefsson & Landelius 1996):**

```
UV = UV_clear * (1 - 0.75 * (C / 100)^3.4)
```

where C is cloud cover in %. When cloud cover is not available, `cloud_factor = 1.0`
(clear-sky UV is returned unmodified). `temporalis/derived.py:199`

**Solar zenith angle:** Computed using the NOAA simplified solar position algorithm
(accurate to ±0.01° for dates within ±1 century of J2000). `temporalis/derived.py:117`

**Sun below horizon:** Returns `DataPoint("UVIndex", 0, "")` when SZA ≥ 90°.
`temporalis/derived.py:194`

**Accuracy:** ±1–2 UV index units under variable cloud conditions.

**Limitations:**

- Does not account for altitude (UV increases ~5–8 % per 1000 m).
- Does not account for total ozone column variation (±15–20 % seasonal effect).
- Does not account for aerosols or surface albedo (snow can increase UV by 50–80 %).
- Cloud attenuation formula is empirical and calibrated for mid-latitude conditions.
- Accuracy is lower at high solar zenith angles (early morning, late evening, winter).

---

## Entry Point

`temporalis/derived.py:226` (`fill_derived(wd, lat=None, lon=None)`)
Applies all four derivations in sequence to a single `WeatherData` object. Mutates `wd`
in-place and returns it for chaining. Safe to call when fields are already populated.

```python
from temporalis.derived import fill_derived

wd = fill_derived(wd, lat=38.72, lon=-9.14)
```

Call order:

1. Dew point (requires temperature + humidity)
2. Apparent temperature (requires temperature, optionally humidity and wind speed)
3. Snow (requires temperature + precipitation)
4. UV index (requires lat, lon, datetime, optionally cloud cover)

---
[← Providers](providers.md) · [Home](../readme.md) · [Units →](units.md)
