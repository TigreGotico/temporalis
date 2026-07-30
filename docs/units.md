# Units

## Unit Modes

All providers accept a `units` parameter. The base class normalises aliases before storing
the value. `temporalis/providers/__init__.py:22`

| Accepted value | Stored as | Description |
|---|---|---|
| `"metric"` (default) | `"metric"` | SI-ish: °C, km/h or m/s, mm |
| `"si"` | `"si"` | Strict SI: K, m/s, mm |
| `"us"` | `"us"` | US customary: °F, mph, inches |
| `"imperial"` | `"us"` | Alias for `"us"` |
| `"english"` | `"us"` | Alias for `"us"` |

`"auto"` is accepted by OWM's URL builder but has no special handling in the base class.

---

## Per-Provider Native Units and Conversion Strategy

Each provider's upstream API returns fixed units for some or all fields. When the user
requests a different unit mode, the provider converts locally before placing values into
`DataPoint` objects. The unit string on each `DataPoint` always reflects the actual units
of the stored value.

| Provider | Temperature native | Wind native | Precip native | Conversion |
|---|---|---|---|---|
| OWM | °C (metric), °F (imperial param), K (si param) | always m/s | always mm | wind + precip converted locally for `"us"` |
| OpenMeteo | API param-controlled | API param-controlled | API param-controlled | no local conversion needed |
| MetNo | always °C | always m/s | always mm | all fields converted locally |
| NWS | always °F | always mph | probability only (no amount) | temp + wind converted locally for `"metric"`/`"si"` |
| IPMA obs | always °C | always m/s | always mm | all fields converted locally |
| IPMA forecast | always °C | class → km/h | probability only | temp + wind converted locally |

**OWM detail:** The OWM API `units` parameter only controls temperature. Wind speed is
always m/s and precipitation is always mm from the API, regardless of the `units` param.
`temporalis/providers/owm.py:7`

**NWS dew point detail:** The NWS API returns dew point in °C even though all other
temperatures are in °F. The provider uses a separate conversion path for this field.
`temporalis/providers/nws.py:83`

**IPMA forecast wind detail:** IPMA forecast wind is a class code (1–5), not a measured
value. It is mapped to a representative km/h speed before unit conversion.
`temporalis/providers/ipma.py:12`

---

## Unit Strings on DataPoint

The `units` attribute on each `DataPoint` is the string actually stored with the value.
Common values across providers:

| Field | `"metric"` | `"us"` | `"si"` |
|---|---|---|---|
| Temperature | `"ºC"` | `"ºF"` | `"K"` |
| Apparent temperature | `"ºC"` | `"ºF"` | `"K"` |
| Dew point | same as temperature | same as temperature | same as temperature |
| Wind speed | `"m/s"` (MetNo, OWM) or `"km/h"` (OpenMeteo) | `"mph"` | `"m/s"` |
| Precipitation | `"mm"` | `"inch"` | `"mm"` |
| Pressure | `"hPa"` (all providers) | `"hPa"` | `"hPa"` |
| Humidity | `"%"` | `"%"` | `"%"` |
| Cloud cover | `"%"` | `"%"` | `"%"` |
| UV index | `""` (dimensionless) | `""` | `""` |
| Wind bearing | `"°"` or `"º"` | same | same |
| Visibility | `"m"` (OWM, OpenMeteo) | `"m"` | `"m"` |

Derived fields (dew point, apparent temperature) inherit the temperature unit from the
input `DataPoint`. `temporalis/derived.py:43`

---

## Conversion Helpers

Conversion is done per-provider before creating `DataPoint` objects. The derived-field
engine has its own unit-normalisation helpers that work from the `units` string on each
`DataPoint`, so derived fields are unit-agnostic. `temporalis/derived.py:17`

Internal helpers in `temporalis/derived.py`:

- `_to_celsius(dp)`, converts temperature `DataPoint` to float °C. `temporalis/derived.py:17`
- `_to_kmh(dp)`, converts wind speed `DataPoint` to float km/h. `temporalis/derived.py:30`
- `_from_celsius(value_c, target_units)`, converts float °C back to the target unit string. `temporalis/derived.py:43`

---
[← Derived Fields](derived-fields.md) · [Home](../readme.md) · [Examples →](examples.md)
