# temporalis

Unified Python weather API that wraps multiple providers behind one consistent interface.

## Overview

temporalis lets you query OpenWeatherMap, Open-Meteo, Met.no, IPMA, and NOAA NWS through
the same objects: `WeatherData`, `DataPoint`, `HourlyForecast`, `DailyForecast`. Swap the
provider class and nothing else in your code needs to change.

Fields missing from a provider's response are filled automatically by meteorological
approximations (dew point, apparent temperature, snow, UV index). Sun and moon data are
computed from coordinates on every provider with no extra API call.

All built-in providers are accessed by name via the provider registry. No
provider-specific imports are needed at runtime.

## Key Classes

| Class | Purpose | Source |
|---|---|---|
| `WeatherProvider` | Base class: shared session, geocoding, sun/moon, forecast accessors | `temporalis/providers/__init__.py:14` |
| `WeatherData` | Timestamped snapshot of all weather fields | `temporalis/__init__.py:87` |
| `DataPoint` | Single measurement with value, units, min/max, probability | `temporalis/__init__.py:9` |
| `HourlyForecast` | Ordered collection of hourly `WeatherData` | `temporalis/__init__.py:186` |
| `DailyForecast` | Ordered collection of daily `WeatherData` | `temporalis/__init__.py:219` |
| `MinutelyForecast` | Per-minute precipitation for the next ~60 minutes | `temporalis/__init__.py:277` |
| `OWM` | OpenWeatherMap provider | `temporalis/providers/owm.py:17` |
| `OpenMeteo` | Open-Meteo forecast + historical archive provider | `temporalis/providers/openmeteo.py:59` |
| `MetNo` | Norwegian Met Institute provider | `temporalis/providers/metno.py:43` |
| `NWS` | NOAA National Weather Service (USA only) | `temporalis/providers/nws.py:48` |
| `IPMA` | Portuguese Met Authority (Portugal only) | `temporalis/providers/ipma.py:45` |
| `OpenMeteoAirQuality` | Open-Meteo air quality API | `temporalis/providers/openmeteo_airquality.py:66` |

## Contents

- [Installation and quick start](../readme.md)
- [Data model](data-model.md): WeatherProvider, WeatherData, DataPoint, forecast collections
- [Providers](providers.md): coverage, constructor args, quirks, and unit handling per provider
- [Derived fields](derived-fields.md): automatic field estimation for dew point, apparent temperature, snow, UV index
- [Units](units.md): unit system design and per-provider native units
- [Examples](examples.md): common usage patterns with code
- [Adding a custom provider](api-reference.md)
