# Temporalis

Unified weather abstraction library for Python. Provides a single consistent
interface over six weather services (including a historical archive), plus sun
and moon data calculated locally via astral.

## Overview

Each provider subclasses `WeatherProvider`, fetches data from its upstream
API on construction, and normalises the result into the shared data model
(`WeatherData`, `DataPoint`, `HourlyForecast`, `DailyForecast`). Sun and
moon properties are computed from coordinates and date — they are independent
of the upstream API.

## Key Classes

| Class | Purpose | Source |
|---|---|---|
| `WeatherProvider` | Base class: caching, geocoding, sun/moon, forecast accessors | `temporalis/providers/__init__.py:13` |
| `OWM` | OpenWeatherMap provider (global, API key) | `temporalis/providers/owm.py:6` |
| `OpenMeteo` | Open-Meteo provider (global, no key) | `temporalis/providers/openmeteo.py:42` |
| `MetNo` | Met.no provider (global, no key, User-Agent required) | `temporalis/providers/metno.py:43` |
| `IPMA` | IPMA provider (Portugal only, no key) | `temporalis/providers/ipma.py:42` |
| `NWS` | NWS/Weather.gov provider (USA only, no key) | `temporalis/providers/nws.py:40` |
| `OpenMeteoHistorical` | Open-Meteo historical archive (global, no key, date range) | `temporalis/providers/openmeteo_historical.py:24` |
| `WeatherData` | Timestamped weather observation or forecast slot | `temporalis/__init__.py:80` |
| `DataPoint` | Single measured quantity with value, units, min/max, probability | `temporalis/__init__.py:6` |
| `HourlyForecast` | Collection of `WeatherData` objects indexed by hour | `temporalis/__init__.py:179` |
| `DailyForecast` | Collection of `WeatherData` objects indexed by day | `temporalis/__init__.py:212` |

## Contents

- [Installation and Quick Start](../readme.md)
- [Data Model Reference](data-model.md)
- [Provider API Reference](api-reference.md)
- [Adding a New Provider](providers.md)
