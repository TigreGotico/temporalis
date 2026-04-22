# Changelog

## 0.5.0 — 2026-04-23

### Added
- **Ensemble provider** — queries all applicable free sources in parallel and
  merges field-by-field; inter-provider spread exposed via `DataPoint.min_val`/`max_val`
- **OpenMeteoMarine provider** — wave height, period, direction; swell; wind-wave;
  ocean current velocity and direction; metric and US units
- **Marine fields on `WeatherData`** — `waveHeight`, `wavePeriod`, `waveDirection`,
  `swellHeight`, `swellPeriod`, `swellDirection`, `windWaveHeight`, `windWavePeriod`,
  `windWaveDirection`, `currentVelocity`, `currentDirection`
- **Derived fields** — automatically filled when provider doesn't supply them:
  - Dew point (August-Roche-Magnus)
  - Apparent temperature (Environment Canada wind chill / Rothfuss-Jakobs heat index)
  - Snow (precipitation when T ≤ 2°C)
  - UV index (NOAA solar position + Josefsson–Landelius cloud attenuation)
- **Minutely precipitation** — OWM One Call 3.0; `MinutelyData`, `MinutelyForecast`
- **OpenMeteo historical archive** — `start=`/`end=` parameters on `OpenMeteo`
  (replaces the removed `OpenMeteoHistorical` class)
- **OpenMeteoAirQuality provider** — PM2.5, PM10, ozone, NO₂, SO₂, CO, pollen, UV
- **Provider registry** — `WeatherProvider.register/get/available/from_address`
- **`py.typed` marker** — package is now recognised as typed by mypy and pyright
- `/docs/` folder — six reference documents covering data model, providers,
  derived fields, units, examples, and custom provider API
- `/examples/` folder — 14 runnable scripts

### Changed
- **`apparentTemperature` fallback removed** — `WeatherData.from_dict` no longer
  silently copies `temperature` into `apparentTemperature`; derived wind chill and
  heat index now apply correctly for all providers
- **Session is now per-instance** — each `WeatherProvider` gets its own
  `requests.Session`; thread-safe for parallel use in Ensemble
- **OWM unit normalisation fixed** — wind speed (always m/s from API) and
  precipitation (always mm) now convert correctly for `units="us"`
- **IPMA daily precipitation** — stored as probability fraction in `DataPoint.prob`,
  not as a value; `DataPoint.value` is `None` for probability-only fields
- **NWS dew point** — correctly converts C→F for `units="us"` mode
- `requests-cache` dependency removed; callers may inject their own session

### Removed
- `OpenMeteoHistorical` — use `OpenMeteo(lat, lon, start=..., end=...)` instead

## 0.4.0 — 2026-04-22

- Initial public release with OWM, OpenMeteo, MetNo, IPMA, NWS providers
