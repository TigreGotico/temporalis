# Workspace Audit — temporalis

Audited: 2026-04-22
Repos surveyed: 1

---

## Summary

| Repo | Last Commit | Stars | Primary | Secondary |
|---|---|---|---|---|
| temporalis | ~2020–2021 (estimated) | unknown | MODERNIZE | needs-tests, needs-packaging, dependency-risk, demo-worthy |

---

## MODERNIZE

### temporalis
> Unified Python abstraction layer for weather service APIs, with built-in sun/moon astronomy data.

**Current state:** The core idea is genuinely useful. `WeatherProvider` is a clean base class that normalises weather data from different upstream APIs (OpenWeatherMap, DarkSky) into a single `WeatherData` / `DataPoint` / `HourlyForecast` / `DailyForecast` object model. Sun times (dawn, dusk, sunrise, sunset, noon) and moon phase — with multilingual phase names in eight languages — are computed from coordinates via `astral` and exposed as first-class properties on every provider instance. The geocoding fallback chain in `location.py` is pragmatic if sprawling. The `DataPoint` class capturing value, min/max, low/high, and probability is a thoughtful data model for probabilistic weather readings. In-memory HTTP caching via `requests-cache` is built in. The OWM provider correctly handles current weather and 3-hour forecast data, reconstructing daily aggregates from the 3-hour buckets.

**What's stale — specific issues:**

- **DarkSky is dead.** The `DarkSky` provider literally prints `"WARNING: darksky is shutting down"` on instantiation. DarkSky shut down its public API in 2023. This provider is completely non-functional and should be deleted or replaced.
- **Hardcoded API key in source.** `OWM.default_key = "28fed22898afd4717ce5a1535da1f78c"` is committed directly in `owm.py`. This is a real OWM key belonging to the author. It will stop working when OWM rotates or revokes it, and it is a credential-in-source violation.
- **`setup.py`-based packaging, version 0.1, no changelog.** No `pyproject.toml`. Pinned to Python 3.8 in CI.
- **CI is cosmetic.** `build_tests.yml` only builds and installs; it runs zero actual tests. The only real test file is `license_tests.py`, which checks dependency licenses using a NeonJarbas-specific tool (`lichecker`) fetched directly from GitHub with no pinned ref.
- **No functional tests whatsoever.** No unit tests for `DataPoint`, `WeatherData`, `WeatherProvider`, `sun`, `moon`, or `location`. No mocking of HTTP calls.
- **`pendulum` version fragility.** The code uses `pendulum.from_timestamp()` and `pendulum.timezone()` patterns that broke in pendulum's v3 major release. No version pins anywhere in `requirements.txt`.
- **Hardcoded personal geonames key.** `geocoder.geonames(address, method='details', key='jarbas')` in `location.geolocate()`. Will silently fail or rate-limit for any other user.
- **`Nominatim` without a `user_agent`.** `geopy.geocoders.Nominatim()` called with no `user_agent` in `reverse_geolocate()` — raises `ConfigurationError` on current geopy and violates Nominatim's ToS.
- **`as_dict()` mutates `self.__dict__` in place.** Both `DataPoint.as_dict()` and `WeatherData.as_dict()` do `data = self.__dict__` and then pop keys from `data`, which permanently destroys the object's own attributes. Calling `as_dict()` once corrupts the instance. This is a silent correctness bug.
- **Bare `except:` clauses throughout.** `__init__.py`, `location.py`, `xml.py`, and `providers/__init__.py` all swallow exceptions silently. Failures are invisible.
- **`xml.py` is dead code.** Provides `xml2dict`/`dict2xml` helpers but nothing in the codebase calls them. Leftover from a scrapped provider.
- **GitHub Actions use end-of-life action versions.** `actions/checkout@v2` and `actions/setup-python@v1` are both deprecated.

**Effort estimate:** Medium — a week of focused work to reach a maintainable state.

**Worth it because:** The OWM provider is functional and the unified data model solves a real problem. The OVOS ecosystem (given the JarbasAl authorship) likely uses or could use this for voice assistant weather skills. The moon multilingual support and integrated sun-times-from-coordinates pattern is a genuinely convenient combination. Modernising packaging, removing DarkSky, fixing the credential leak, and adding real tests with HTTP mocking would produce a solid library.

---

## Cross-cutting observations

**The core abstraction is right, but nearly every implementation detail is wrong.** The `WeatherData` / `DataPoint` / `WeatherProvider` inheritance model is clean and the API surface is ergonomic. The problem is that the surrounding code is full of quiet traps: mutable `as_dict()`, swallowed exceptions, hardcoded credentials, and a dead provider that announces its own death at runtime.

**There is one live, functional provider and one zombie.** OWM works (assuming the embedded key still functions). DarkSky is dead and has been for years. The repository gives the false impression of supporting two backends when it supports one. Anyone using this today either discovered the DarkSky failure immediately or only ever used OWM.

**The geocoding strategy is naive and fragile.** Trying eight different geocoding services in sequence with personal API keys baked into source is not portable or maintainable. Modern practice would be to require the caller to supply coordinates, or use a single configurable backend with a proper key injection mechanism. The `try_all=True` default means every address lookup that fails the first few providers incurs multiple slow sequential HTTP round trips.

**The uncomfortable truth: this library has no real tests and probably never ran in any context other than the author's machine with the author's API keys.** The CI "build test" confirms the package installs. The license test confirms dependency licenses are compatible. Neither validates that any weather data can actually be fetched, parsed, or returned correctly. Given the mutable `as_dict()` bug, any code path that serialises a `WeatherData` or `DataPoint` object more than once silently corrupts the object. It is likely that the `print_daily()` / `print_hourly()` methods in the README example trigger this bug on every run.

**The dependency set is heavier than necessary.** `pendulum`, `python-dateutil`, and `pytz` are all present simultaneously — three different datetime libraries doing overlapping work. A modernised version should standardise on one (probably `pendulum` or stdlib `zoneinfo` depending on the Python floor) and drop the others.

---

## Recommended next actions

1. **Delete immediately:**
   - `temporalis/providers/darksky.py` — dead API, non-functional, actively misleading.
   - `temporalis/xml.py` — unused dead code.

2. **Fix before anything else:**
   - Remove the hardcoded OWM API key; require it as a mandatory constructor argument.
   - Fix `as_dict()` in both `DataPoint` and `WeatherData` to return `dict(self.__dict__)` copy rather than mutating the live instance.
   - Replace `Nominatim()` with `Nominatim(user_agent="temporalis")`.

3. **Modernise (ordered by value/effort):**
   - Migrate to `pyproject.toml`, drop `setup.py`.
   - Pin dependency versions, especially `pendulum` and `astral`.
   - Add functional tests with `responses` or `httpretty` to mock OWM HTTP calls.
   - Upgrade GitHub Actions to current versions; replace the bespoke `lichecker` dependency with standard license tooling.
   - Consolidate datetime handling to one library.

4. **Invest in (if the library is intended to survive long-term):**
   - Add Open-Meteo as a free, no-key-required provider to replace DarkSky — this eliminates the credential problem for a baseline provider entirely.
   - Add type annotations throughout.
   - Expand `exceptions.py` beyond the single `InvalidKey` class; API failures, geocoding failures, and parse errors currently surface as bare Python exceptions or silent `None` returns.

5. **Whitepaper candidates:** None. This is an integration library, not a novel algorithm or architecture.

---

**Repos audited: 1 | MAINTAIN: 0 | MODERNIZE: 1 | NOVEL: 0 | ARCHIVE: 0 | DEAD: 0**
