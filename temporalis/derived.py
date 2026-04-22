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


# ── public entry point ────────────────────────────────────────────────────────

def fill_derived(wd) -> "WeatherData":
    """Fill missing fields on a WeatherData object using meteorological approximations.

    Mutates *wd* in-place and returns it for chaining. Safe to call when
    fields are already populated — existing non-None values are never overwritten.
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

    return wd
