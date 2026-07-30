"""Ensemble weather provider — merges all available free sources.

Queries multiple providers in parallel, then merges field-by-field:
- Averaged fields (temp, humidity, wind, pressure, cloud): mean value,
  min/max set to inter-provider spread so callers can read uncertainty.
- Single-source fields (precipitation, snow): highest-priority regional source.
- Native-preferred fields (apparentTemperature, uvIndex): best native source.
- Marine and air quality: exclusively from their dedicated providers.
- Alerts: union of all provider alerts, deduplicated by (event, onset, expires).

Provider auto-selection:
  Always:   OpenMeteo, MetNo
  US bbox:  NWS
  PT bbox:  IPMA
  Key set:  OWM (env OWM_KEY or key= param)
  Ocean:    OpenMeteoMarine (silently skipped if landlocked)
  Always:   OpenMeteoAirQuality
"""
from __future__ import annotations
import logging
import os
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from temporalis.providers import WeatherProvider
from temporalis import WeatherData, DataPoint, HourlyForecast, DailyForecast, MinutelyForecast

log = logging.getLogger(__name__)

# Bounding boxes for region-specific providers
_US_LAT = (24.0, 50.0)
_US_LON = (-125.0, -66.0)
_PT_LAT = (36.0, 42.5)
_PT_LON = (-9.5, -6.0)

# Merge priority: first provider in list with a non-None value wins for
# native-preferred fields.
_PRIORITY = ["nws", "ipma", "owm", "metno", "openmeteo"]

# Fields that are averaged across all providers
_AVG_FIELDS = [
    "temperature", "humidity", "cloudCover", "pressure",
    "windSpeed", "windBearing", "windGust", "dewPoint", "visibility",
]

# Fields taken from the highest-priority provider that has them natively
_PREFER_FIELDS = ["apparentTemperature", "uvIndex"]

# Single-source precipitation fields (prefer regional source)
_PRECIP_FIELDS = ["precipitation", "snow"]

# Fields exclusive to specific providers — never merged
_MARINE_FIELDS = [
    "waveHeight", "waveDirection", "wavePeriod",
    "windWaveHeight", "windWaveDirection", "windWavePeriod",
    "swellHeight", "swellDirection", "swellPeriod",
    "currentVelocity", "currentDirection",
]
_AQ_FIELDS = ["ozone"]  # openmeteo_airquality also adds extra attrs; ozone maps to WeatherData


def _in_us(lat, lon):
    return _US_LAT[0] <= lat <= _US_LAT[1] and _US_LON[0] <= lon <= _US_LON[1]


def _in_pt(lat, lon):
    return _PT_LAT[0] <= lat <= _PT_LAT[1] and _PT_LON[0] <= lon <= _PT_LON[1]


def _hour_key(dt) -> Optional[int]:
    """UTC epoch rounded to the nearest hour."""
    try:
        import pendulum
        utc = dt.in_tz("UTC") if hasattr(dt, "in_tz") else dt
        return int(utc.timestamp()) // 3600 * 3600
    except Exception:
        return None


def _date_key(dt) -> Optional[str]:
    try:
        return dt.date().isoformat()
    except Exception:
        return None


def _avg_dp(field: str, snapshots: list[WeatherData]) -> Optional[DataPoint]:
    """Average a numeric DataPoint field across snapshots; spread → min/max."""
    values = []
    units = None
    label = None
    for s in snapshots:
        dp = getattr(s, field, None)
        if dp is not None and dp.value is not None:
            try:
                values.append(float(dp.value))
                if units is None:
                    units = dp.units
                    label = dp.name if hasattr(dp, "name") else field
            except (TypeError, ValueError):
                pass
    if not values:
        return None
    mean = round(statistics.mean(values), 2)
    spread = len(values) > 1
    return DataPoint(
        label or field, mean, units or "",
        min_val=round(min(values), 2) if spread else None,
        max_val=round(max(values), 2) if spread else None,
    )


def _prefer_dp(field: str, snapshots: list[WeatherData],
               provider_names: list[str]) -> Optional[DataPoint]:
    """Return the DataPoint from the highest-priority provider that has it."""
    by_name = {name: snap for name, snap in zip(provider_names, snapshots)}
    for name in _PRIORITY:
        snap = by_name.get(name)
        if snap is not None:
            dp = getattr(snap, field, None)
            if dp is not None and dp.value is not None:
                return dp
    # Fall back to any non-None value
    for snap in snapshots:
        dp = getattr(snap, field, None)
        if dp is not None and dp.value is not None:
            return dp
    return None


def _precip_dp(field: str, snapshots: list[WeatherData],
               provider_names: list[str], lat, lon) -> Optional[DataPoint]:
    """Pick precipitation from the best regional source."""
    by_name = {name: snap for name, snap in zip(provider_names, snapshots)}
    # Regional preference: NWS for US, IPMA for PT, else OpenMeteo
    regional = (["nws"] if _in_us(lat, lon)
                else ["ipma"] if _in_pt(lat, lon)
                else [])
    for name in regional + ["openmeteo", "metno", "owm"]:
        snap = by_name.get(name)
        if snap is not None:
            dp = getattr(snap, field, None)
            if dp is not None and dp.value is not None:
                return dp
    return None


def _exclusive_dp(field: str, snapshots: list[WeatherData],
                  provider_names: list[str], exclusive_provider: str) -> Optional[DataPoint]:
    by_name = {name: snap for name, snap in zip(provider_names, snapshots)}
    snap = by_name.get(exclusive_provider)
    return getattr(snap, field, None) if snap is not None else None


def _merge_snapshots(snapshots: list[WeatherData], provider_names: list[str],
                     lat: float, lon: float) -> WeatherData:
    """Merge a list of WeatherData snapshots into one."""
    wd = WeatherData()

    # Timestamps: use most recent
    dts = [s.datetime for s in snapshots if s.datetime is not None]
    wd.datetime = max(dts) if dts else None

    # Summary/icon: highest priority provider with both
    by_name = {n: s for n, s in zip(provider_names, snapshots)}
    for name in _PRIORITY + list(by_name.keys()):
        snap = by_name.get(name)
        if snap and snap.summary and snap.icon:
            wd.summary = snap.summary
            wd.icon = snap.icon
            break

    # Averaged fields
    for field in _AVG_FIELDS:
        setattr(wd, field, _avg_dp(field, snapshots))

    # Native-preferred fields
    for field in _PREFER_FIELDS:
        setattr(wd, field, _prefer_dp(field, snapshots, provider_names))

    # Precipitation (single-source)
    for field in _PRECIP_FIELDS:
        setattr(wd, field, _precip_dp(field, snapshots, provider_names, lat, lon))

    # Marine fields (exclusive to openmeteo_marine)
    for field in _MARINE_FIELDS:
        setattr(wd, field, _exclusive_dp(field, snapshots, provider_names, "openmeteo_marine"))

    # Ozone (exclusive to openmeteo_airquality)
    for field in _AQ_FIELDS:
        setattr(wd, field, _exclusive_dp(field, snapshots, provider_names, "openmeteo_airquality"))

    return wd


class Ensemble(WeatherProvider):
    """Merges all applicable free weather sources for a location.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        units: ``"metric"`` (default) or ``"us"``.
        key: OpenWeatherMap API key (optional; also read from ``OWM_KEY`` env var).
        providers: Explicit list of ``(name, provider_class)`` pairs to use
            instead of auto-selection. Each class is instantiated with
            ``(lat, lon, units=units)``.
    """

    def __init__(self, lat, lon, date=None, units="metric",
                 key=None, providers=None):
        super().__init__(lat, lon, date, units)
        self._owm_key = key or os.environ.get("OWM_KEY")
        self._custom_providers = providers
        self._named_providers: list[tuple[str, WeatherProvider]] = []
        self._fetch_all()

    # ── provider selection ────────────────────────────────────────────────────

    def _provider_specs(self):
        if self._custom_providers is not None:
            return self._custom_providers

        from temporalis.providers.openmeteo import OpenMeteo
        from temporalis.providers.metno import MetNo
        from temporalis.providers.openmeteo_airquality import OpenMeteoAirQuality

        specs = [
            ("openmeteo", OpenMeteo),
            ("metno", MetNo),
            ("openmeteo_airquality", OpenMeteoAirQuality),
        ]

        if _in_us(self.latitude, self.longitude):
            from temporalis.providers.nws import NWS
            specs.append(("nws", NWS))

        if _in_pt(self.latitude, self.longitude):
            from temporalis.providers.ipma import IPMA
            specs.append(("ipma", IPMA))

        if self._owm_key:
            from temporalis.providers.owm import OWM
            specs.append(("owm", OWM))

        return specs

    def _fetch_all(self):
        specs = self._provider_specs()
        lat, lon = self.latitude, self.longitude
        units = self.units
        date = self.datetime

        def _init(name, cls):
            try:
                # Try marine separately since it fails on landlocked coords
                if name == "openmeteo_marine":
                    return name, cls(lat, lon, units=units)
                # OWM needs key kwarg
                if name == "owm":
                    return name, cls(lat, lon, units=units, key=self._owm_key, date=date)
                return name, cls(lat, lon, units=units, date=date)
            except Exception as exc:
                log.debug("Ensemble: skipping %s — %s", name, exc)
                return name, None

        # Also try marine opportunistically
        from temporalis.providers.openmeteo_marine import OpenMeteoMarine
        all_specs = specs + [("openmeteo_marine", OpenMeteoMarine)]

        with ThreadPoolExecutor(max_workers=len(all_specs)) as pool:
            futures = {pool.submit(_init, name, cls): name
                       for name, cls in all_specs}
            for future in as_completed(futures):
                name, provider = future.result()
                if provider is not None:
                    self._named_providers.append((name, provider))

        if not self._named_providers:
            raise RuntimeError("Ensemble: all providers failed for this location.")

        log.debug("Ensemble: loaded %s",
                  [n for n, _ in self._named_providers])

    # ── internal helpers ──────────────────────────────────────────────────────

    @property
    def _provider_names(self):
        return [n for n, _ in self._named_providers]

    @property
    def _providers(self):
        return [p for _, p in self._named_providers]

    def _merge_current(self) -> WeatherData:
        snapshots, names = [], []
        for name, p in self._named_providers:
            try:
                snapshots.append(p.weather)
                names.append(name)
            except Exception as exc:
                log.debug("Ensemble: %s.weather failed — %s", name, exc)
        if not snapshots:
            return WeatherData()
        return _merge_snapshots(snapshots, names, self.latitude, self.longitude)

    def _merge_hourly(self) -> list[WeatherData]:
        # Collect {hour_key: {provider_name: WeatherData}}
        buckets: dict[int, dict[str, WeatherData]] = {}
        for name, p in self._named_providers:
            try:
                for h in p.hours:
                    key = _hour_key(h.datetime)
                    if key is None:
                        continue
                    buckets.setdefault(key, {})[name] = h
            except Exception as exc:
                log.debug("Ensemble: %s.hours failed — %s", name, exc)

        merged = []
        for key in sorted(buckets):
            slot = buckets[key]
            snaps = list(slot.values())
            names = list(slot.keys())
            merged.append(_merge_snapshots(snaps, names, self.latitude, self.longitude))
        return merged

    def _merge_daily(self) -> list[WeatherData]:
        buckets: dict[str, dict[str, WeatherData]] = {}
        for name, p in self._named_providers:
            try:
                for d in p.days:
                    key = _date_key(d.datetime)
                    if key is None:
                        continue
                    buckets.setdefault(key, {})[name] = d
            except Exception as exc:
                log.debug("Ensemble: %s.days failed — %s", name, exc)

        merged = []
        for key in sorted(buckets):
            slot = buckets[key]
            snaps = list(slot.values())
            names = list(slot.keys())
            merged.append(_merge_snapshots(snaps, names, self.latitude, self.longitude))
        return merged

    # ── public interface ──────────────────────────────────────────────────────

    @property
    def weather(self):
        from temporalis.derived import fill_derived
        return fill_derived(self._merge_current(),
                            lat=self.latitude, lon=self.longitude)

    @property
    def hourly(self):
        from temporalis.derived import fill_derived
        hours = [fill_derived(h, lat=self.latitude, lon=self.longitude)
                 for h in self._merge_hourly()]
        summary_wd = WeatherData()
        summary_wd.datetime = self.datetime
        return HourlyForecast(self.datetime, hours, summary_wd)

    @property
    def hours(self):
        return self.hourly.hours

    @property
    def daily(self):
        from temporalis.derived import fill_derived
        days = [fill_derived(d, lat=self.latitude, lon=self.longitude)
                for d in self._merge_daily()]
        summary_wd = WeatherData()
        summary_wd.datetime = self.datetime
        return DailyForecast(self.datetime, days, summary_wd)

    @property
    def days(self):
        return self.daily.days

    @property
    def minutely(self) -> MinutelyForecast:
        for name, p in self._named_providers:
            try:
                mf = p.minutely
                if mf and len(mf) > 0:
                    return mf
            except Exception:
                pass
        return MinutelyForecast([])

    @property
    def alerts(self):
        seen = set()
        combined = []
        for _, p in self._named_providers:
            try:
                for alert in p.alerts:
                    key = (alert.get("event"), alert.get("onset"), alert.get("expires"))
                    if key not in seen:
                        seen.add(key)
                        combined.append(alert)
            except Exception:
                pass
        return combined

    @property
    def providers(self) -> list[str]:
        """Names of the providers that successfully loaded."""
        return self._provider_names
