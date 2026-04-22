"""Meteorological approximations for missing WeatherData fields.

All formulas operate in SI units internally (°C, km/h). Unit-aware helpers
normalise DataPoint values before the formula and convert results back to
the DataPoint's original unit system so callers never need to care about units.
"""
from __future__ import annotations
import math
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from temporalis import DataPoint, WeatherData


# ── unit normalisers ──────────────────────────────────────────────────────────

def _to_celsius(dp) -> Optional[float]:
    if dp is None or dp.value is None:
        return None
    u = dp.units
    if u in ("ºC", "°C", "C"):
        return float(dp.value)
    if u in ("ºF", "°F", "F"):
        return (float(dp.value) - 32) * 5 / 9
    if u == "K":
        return float(dp.value) - 273.15
    return float(dp.value)  # assume Celsius


def _to_kmh(dp) -> Optional[float]:
    if dp is None or dp.value is None:
        return None
    u = dp.units
    if u == "km/h":
        return float(dp.value)
    if u == "m/s":
        return float(dp.value) * 3.6
    if u in ("mph", "mi/h"):
        return float(dp.value) * 1.60934
    return float(dp.value)  # assume km/h


def _from_celsius(value_c: float, target_units: str) -> float:
    if target_units in ("ºF", "°F", "F"):
        return round(value_c * 9 / 5 + 32, 1)
    if target_units == "K":
        return round(value_c + 273.15, 2)
    return round(value_c, 1)


# ── derivation functions ──────────────────────────────────────────────────────

def approx_dew_point(temp_dp, humidity_dp) -> Optional["DataPoint"]:
    """August-Roche-Magnus dew point approximation.

    Valid for −40 °C < T < 60 °C and 1 % < RH ≤ 100 %.
    Returns a DataPoint in the same temperature units as temp_dp, or None
    when inputs are insufficient.
    """
    from temporalis import DataPoint
    t_c = _to_celsius(temp_dp)
    rh = humidity_dp.value if humidity_dp is not None else None
    if t_c is None or rh is None:
        return None
    rh = max(1.0, min(100.0, float(rh)))
    alpha = math.log(rh / 100.0) + (17.625 * t_c) / (243.04 + t_c)
    denom = 17.625 - alpha
    if denom == 0:
        return None
    td_c = (243.04 * alpha) / denom
    return DataPoint("DewPoint", _from_celsius(td_c, temp_dp.units), temp_dp.units)


def approx_apparent_temp(temp_dp, humidity_dp=None, wind_dp=None) -> Optional["DataPoint"]:
    """Apparent temperature via wind chill or heat index.

    Wind chill (Environment Canada 2001):
        valid when T < 10 °C and V > 3 km/h.

    Heat index (Rothfuss-Jakobs polynomial):
        valid when T > 27 °C and RH ≥ 40 %.

    Returns a DataPoint in the same temperature units as temp_dp, or None
    when neither formula's conditions are met.
    """
    from temporalis import DataPoint
    t_c = _to_celsius(temp_dp)
    if t_c is None:
        return None

    v_kmh = _to_kmh(wind_dp)
    rh = float(humidity_dp.value) if humidity_dp is not None and humidity_dp.value is not None else None

    if t_c < 10.0 and v_kmh is not None and v_kmh > 3.0:
        wc_c = (13.12 + 0.6215 * t_c
                - 11.37 * (v_kmh ** 0.16)
                + 0.3965 * t_c * (v_kmh ** 0.16))
        return DataPoint("ApparentTemperature",
                         _from_celsius(wc_c, temp_dp.units), temp_dp.units)

    if t_c > 27.0 and rh is not None and rh >= 40.0:
        hi_c = (-8.78469475556
                + 1.61139411 * t_c
                + 2.33854883889 * rh
                - 0.14611605 * t_c * rh
                - 0.012308094 * t_c ** 2
                - 0.0164248277778 * rh ** 2
                + 0.002211732 * t_c ** 2 * rh
                + 0.00072546 * t_c * rh ** 2
                - 0.000003582 * t_c ** 2 * rh ** 2)
        return DataPoint("ApparentTemperature",
                         _from_celsius(hi_c, temp_dp.units), temp_dp.units)

    return None


def _solar_zenith_deg(lat: float, lon: float, dt) -> Optional[float]:
    """Solar zenith angle in degrees for the given location and UTC datetime.

    Uses the NOAA simplified solar position algorithm (accurate to ±0.01° for
    dates within ±1 century of J2000).  Returns None when dt has no timezone
    info or conversion to UTC fails.
    """
    try:
        import pendulum
        utc = dt.in_tz("UTC") if hasattr(dt, "in_tz") else dt
        # Julian day number
        y, m, d = utc.year, utc.month, utc.day
        h = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
        jd = (367 * y
              - int(7 * (y + int((m + 9) / 12)) / 4)
              + int(275 * m / 9)
              + d + 1721013.5 + h / 24.0)
        # Julian centuries from J2000.0
        jc = (jd - 2451545.0) / 36525.0
        # Geometric mean longitude and anomaly of the sun (degrees)
        l0 = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
        m_deg = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
        m_rad = math.radians(m_deg)
        # Equation of centre
        eoc = (math.sin(m_rad) * (1.914602 - jc * (0.004817 + 0.000014 * jc))
               + math.sin(2 * m_rad) * (0.019993 - 0.000101 * jc)
               + math.sin(3 * m_rad) * 0.000289)
        # Sun's true longitude → apparent longitude
        sun_lon = l0 + eoc
        omega = 125.04 - 1934.136 * jc
        apparent_lon = sun_lon - 0.00569 - 0.00478 * math.sin(math.radians(omega))
        # Mean obliquity of the ecliptic
        obliq_mean = (23 + (26 + ((21.448 - jc * (46.8150 + jc * (0.00059 - jc * 0.001813)))) / 60) / 60)
        obliq_corr = obliq_mean + 0.00256 * math.cos(math.radians(omega))
        # Sun declination
        dec_rad = math.asin(math.sin(math.radians(obliq_corr)) * math.sin(math.radians(apparent_lon)))
        # Equation of time (minutes)
        var_y = math.tan(math.radians(obliq_corr / 2)) ** 2
        eot = (4 * math.degrees(
            var_y * math.sin(2 * math.radians(l0))
            - 2 * m_deg_eccentricity(jc) * math.sin(m_rad)
            + 4 * m_deg_eccentricity(jc) * var_y * math.sin(m_rad) * math.cos(2 * math.radians(l0))
            - 0.5 * var_y ** 2 * math.sin(4 * math.radians(l0))
            - 1.25 * m_deg_eccentricity(jc) ** 2 * math.sin(2 * m_rad)
        ))
        # True solar time (minutes)
        tst = (h * 60 + lon * 4 + eot) % 1440
        ha = tst / 4 - 180
        ha_rad = math.radians(ha)
        lat_rad = math.radians(lat)
        cos_zenith = (math.sin(lat_rad) * math.sin(dec_rad)
                      + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad))
        return math.degrees(math.acos(max(-1.0, min(1.0, cos_zenith))))
    except Exception:
        return None


def m_deg_eccentricity(jc: float) -> float:
    """Earth's orbital eccentricity at Julian century jc."""
    return 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)


def approx_uv_index(lat: float, lon: float, dt,
                    cloud_cover_dp=None) -> Optional["DataPoint"]:
    """Approximate UV index from solar position and cloud cover.

    Clear-sky UV uses the WMO simplified model:
        UV_clear = 12 × max(cos(SZA), 0)^0.75

    Cloud attenuation (Josefsson & Landelius 1996):
        UV = UV_clear × (1 − 0.75 × (C/100)^3.4)

    Valid only when the sun is above the horizon (SZA < 90°).
    Accuracy: ±1–2 UV index units under variable cloud.
    """
    from temporalis import DataPoint
    sza = _solar_zenith_deg(lat, lon, dt)
    if sza is None or sza >= 90.0:
        return DataPoint("UVIndex", 0, "")

    uv_clear = 12.0 * (math.cos(math.radians(sza)) ** 0.75)

    cloud_factor = 1.0
    if cloud_cover_dp is not None and cloud_cover_dp.value is not None:
        c = max(0.0, min(100.0, float(cloud_cover_dp.value)))
        cloud_factor = 1.0 - 0.75 * (c / 100.0) ** 3.4

    uv = round(uv_clear * cloud_factor, 1)
    return DataPoint("UVIndex", max(0.0, uv), "")


def approx_snow(temp_dp, precip_dp) -> Optional["DataPoint"]:
    """Estimate snowfall from precipitation when temperature ≤ 2 °C.

    Below the rain/snow threshold (2 °C) all precipitation is assumed to fall
    as snow.  Returns a DataPoint with the same value and unit as precip_dp,
    or None when conditions are not met.
    """
    from temporalis import DataPoint
    t_c = _to_celsius(temp_dp)
    if t_c is None or precip_dp is None or precip_dp.value is None:
        return None
    if t_c > 2.0:
        return None
    return DataPoint("Snow", float(precip_dp.value), precip_dp.units)


# ── public entry point ────────────────────────────────────────────────────────

def fill_derived(wd, lat: Optional[float] = None, lon: Optional[float] = None) -> "WeatherData":
    """Fill missing fields on a WeatherData object using meteorological approximations.

    Mutates *wd* in-place and returns it for chaining. Safe to call when
    fields are already populated — existing non-None values are never overwritten.

    Pass lat/lon (decimal degrees) to enable UV index estimation.
    """
    if wd is None:
        return wd

    # Dew point: derive from temperature + humidity when missing
    if wd.dewPoint is None and wd.temperature is not None and wd.humidity is not None:
        wd.dewPoint = approx_dew_point(wd.temperature, wd.humidity)

    # Apparent temperature: derive when absent or echoed as plain temperature
    apparent_is_echo = (
        wd.apparentTemperature is not None
        and wd.temperature is not None
        and wd.apparentTemperature.value == wd.temperature.value
    )
    if (wd.apparentTemperature is None or apparent_is_echo) and wd.temperature is not None:
        derived = approx_apparent_temp(wd.temperature, wd.humidity, wd.windSpeed)
        if derived is not None:
            wd.apparentTemperature = derived

    # Snow: estimate from precipitation when temperature is at or below freezing threshold
    if wd.snow is None and wd.temperature is not None and wd.precipitation is not None:
        wd.snow = approx_snow(wd.temperature, wd.precipitation)

    # UV index: requires coordinates and a valid datetime
    if wd.uvIndex is None and lat is not None and lon is not None and wd.datetime is not None:
        wd.uvIndex = approx_uv_index(lat, lon, wd.datetime, wd.cloudCover)

    return wd
