# Implementation Notes: Revive temporalis — core fixes + IPMA + Open-Meteo providers

## Patterns to Use

- **OWM as the template** — Every new provider follows the same shape: `__init__` calls `super().__init__()` then `self._request()`, which calls private methods that populate `self.data["currently"]`, `self.data["daily"]`, `self.data["hourly"]`. Don't deviate.
- **`self.data["daily"]` structure** — Must be `{"summary": str, "icon": str, "data": [WeatherData, ...]}`. The `WeatherProvider.daily` property reads `.data["daily"]["data"]` as a list. Same shape for `"hourly"`.
- **`self.data["currently"]` structure** — Must be a dict passable to `WeatherData.from_dict()`. Keys: `datetime`, `temperature`, `apparentTemperature`, `humidity`, `cloudCover`, `pressure`, `windSpeed`, `windBearing`, `windGust`, `precipitation`, `snow`, `visibility`, `dewPoint`, `uvIndex`, `icon`, `summary`. All values are `DataPoint` instances or `None` (not raw numbers).
- **`DataPoint` construction** — Always `DataPoint(name, value, units, min_val=..., max_val=...)`. Name is a human label (e.g. `"Temperature"`), not a field key.
- **Timestamp conversion** — Use `self._stamp_to_datetime(unix_ts)` (inherited from `WeatherProvider`) for UNIX timestamps. For ISO strings (Open-Meteo returns `"2024-01-01T12:00"`), use `pendulum.parse(iso_str)`.
- **`WeatherData` construction** — Always use `WeatherData.from_dict(dict)` or set attributes directly on a `WeatherData()` instance. Never subclass `WeatherData`.

## Gotchas

- **`as_dict()` mutation** — The original bug: `data = self.__dict__` gets a *reference*, not a copy. Fix is `data = dict(self.__dict__)`. Do NOT use `copy.copy()` on the whole object — just the dict.
- **`DataPoint.as_dict()` filters out falsy values** — `prob=None`, `min_val == value` etc. get dropped. `from_dict()` must handle missing keys gracefully. Don't add new required fields to `DataPoint` without updating `from_dict`.
- **IPMA observations are keyed by timestamp, not station ID** — The observations JSON is `{ "2026-04-21T07:00": { "stationId": {...fields...} } }`. Take the most recent timestamp key (`max(d.keys())`), then look up station IDs within it.
- **IPMA station coordinates are GeoJSON** — `coordinates: [lon, lat]` (longitude first). Don't swap.
- **IPMA `temperatura` can be -99** — IPMA uses `-99.0` as a sentinel for missing data. Treat values `< -50` as `None` for any numeric field.
- **IPMA daily forecast has no `datetime` field** — Add `datetime` from the forecast URL's day offset: `pendulum.now().add(days=N)` where N is the day index (0–4).
- **IPMA `precipitaProb` is a string** — Cast to `float` before constructing `DataPoint`.
- **Open-Meteo parallel arrays** — `hourly` and `daily` are dicts of `{"fieldname": [val, val, ...]}` with matching-length arrays. Zip them by index: `[{k: v[i] for k, v in hourly.items()} for i in range(len(times))]`. The `time` field is an ISO string.
- **Open-Meteo `weathercode`** — Not a human summary. Map it to an icon string using a simple lookup dict. A minimal mapping is enough (e.g. 0→"clear", 1–3→"clouds", 45–48→"fog", 51–67→"rain", 71–77→"snow", 80–82→"showers", 95→"thunderstorm").
- **Open-Meteo wind direction** — degrees (0–360). Store as `DataPoint("WindBearing", val, "°")`.
- **`pendulum.parse()` vs `pendulum.from_timestamp()`** — Open-Meteo ISO strings (e.g. `"2024-01-01T12:00"`) need `pendulum.parse(s)`. UNIX timestamps need `pendulum.from_timestamp(ts, tz=...)`. Don't mix them.
- **`requests-cache` is a class-level session** — `WeatherProvider.session` is shared across all instances. In tests, mock at the `requests` transport level using `responses`, not by patching `session`.
- **OWM `from_address` uses `default_key`** — Must be updated to require explicit key: `OWM.from_address(address, key)` with no default, raising `ValueError` if `key` is None.
- **`pendulum.timezone()` is used in `providers/__init__.py`** — `from pendulum import timezone` then `timezone(tz_name)`. This is pendulum v2 API. Do not upgrade to v3 syntax.

## Key Imports / APIs

- `pendulum.from_timestamp(ts, tz=tz_name)` — convert UNIX timestamp to pendulum datetime
- `pendulum.parse(iso_str)` — parse ISO 8601 string (Open-Meteo times)
- `pendulum.now().add(days=N)` — compute date for IPMA day-N forecast
- `DataPoint(name, value, units, min_val, max_val, prob)` — `temporalis/__init__.py`
- `WeatherData.from_dict(d)` — `temporalis/__init__.py`
- `WeatherProvider._stamp_to_datetime(ts)` — inherited; converts UNIX int to pendulum
- `WeatherProvider._calc_day_average(hours)` — inherited; takes list of WeatherData, returns averaged dict (use for OWM; not needed for IPMA/OpenMeteo which give daily data directly)
- `self.session.get(url).json()` — cached HTTP GET via `requests-cache`
- `responses.add(responses.GET, url, json=payload)` — mock HTTP in tests (`import responses`)
- `@responses.activate` — decorator to intercept all HTTP in a test

## Conventions

- Field names in `self.data["currently"]` dicts use camelCase matching `WeatherData` attribute names (`cloudCover`, `windBearing`, `apparentTemperature`).
- `DataPoint` name strings use TitleCase (`"Temperature"`, `"WindSpeed"`).
- Provider files live in `temporalis/providers/<name>.py`; class name is TitleCase matching the service name (`IPMA`, `OpenMeteo`, `OWM`).
- Unit strings: `"ºC"`, `"ºF"`, `"K"`, `"hPa"`, `"m/s"`, `"km/h"`, `"mph"`, `"%"`, `"mm"`, `"°"`, `"km"`, `"m"`.
- Tests go in `test/test_<provider>.py`. Each test function is named `test_<what_it_checks>`. Use `@responses.activate` decorator, not context manager.
- `pyproject.toml` test extras: `[project.optional-dependencies] test = ["pytest", "responses"]`.
