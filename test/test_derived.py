"""Unit tests for temporalis/derived.py — formula correctness and unit handling."""
import math
import pytest
from temporalis import DataPoint
import pendulum
from temporalis.derived import (
    _to_celsius, _to_kmh, _from_celsius,
    approx_dew_point, approx_apparent_temp, approx_snow, approx_uv_index,
    fill_derived,
)
from temporalis import WeatherData


# ── unit normalisers ──────────────────────────────────────────────────────────

def _dp(value, units):
    return DataPoint("T", value, units)


def test_to_celsius_already_celsius():
    assert _to_celsius(_dp(20.0, "°C")) == pytest.approx(20.0)


def test_to_celsius_fahrenheit():
    assert _to_celsius(_dp(32.0, "°F")) == pytest.approx(0.0)
    assert _to_celsius(_dp(212.0, "ºF")) == pytest.approx(100.0)


def test_to_celsius_kelvin():
    assert _to_celsius(_dp(273.15, "K")) == pytest.approx(0.0)


def test_to_celsius_none_dp():
    assert _to_celsius(None) is None


def test_to_celsius_none_value():
    assert _to_celsius(_dp(None, "°C")) is None


def test_to_kmh_already_kmh():
    assert _to_kmh(_dp(36.0, "km/h")) == pytest.approx(36.0)


def test_to_kmh_ms():
    assert _to_kmh(_dp(10.0, "m/s")) == pytest.approx(36.0)


def test_to_kmh_mph():
    assert _to_kmh(_dp(1.0, "mph")) == pytest.approx(1.60934)


def test_from_celsius_to_fahrenheit():
    assert _from_celsius(0.0, "°F") == pytest.approx(32.0, abs=0.1)
    assert _from_celsius(100.0, "ºF") == pytest.approx(212.0, abs=0.1)


def test_from_celsius_to_kelvin():
    assert _from_celsius(0.0, "K") == pytest.approx(273.15, abs=0.01)


def test_from_celsius_passthrough():
    assert _from_celsius(20.0, "°C") == pytest.approx(20.0, abs=0.1)


# ── dew point ────────────────────────────────────────────────────────────────

def test_dew_point_reference():
    # At T=20°C, RH=50% → Td ≈ 9.3°C (standard reference value)
    temp = _dp(20.0, "°C")
    hum = _dp(50.0, "%")
    result = approx_dew_point(temp, hum)
    assert result is not None
    assert result.value == pytest.approx(9.3, abs=0.2)
    assert result.units == "°C"


def test_dew_point_high_humidity():
    # At RH=100%, dew point equals temperature
    temp = _dp(15.0, "°C")
    hum = _dp(100.0, "%")
    result = approx_dew_point(temp, hum)
    assert result.value == pytest.approx(15.0, abs=0.1)


def test_dew_point_unit_propagation_fahrenheit():
    # Result must be in Fahrenheit if temp is in Fahrenheit
    temp = _dp(68.0, "°F")  # 20°C
    hum = _dp(50.0, "%")
    result = approx_dew_point(temp, hum)
    assert result.units == "°F"
    assert result.value == pytest.approx(48.8, abs=0.5)  # 9.3°C → ~48.7°F


def test_dew_point_missing_humidity():
    assert approx_dew_point(_dp(20.0, "°C"), None) is None


def test_dew_point_missing_temp():
    assert approx_dew_point(None, _dp(50.0, "%")) is None


# ── apparent temperature: wind chill ─────────────────────────────────────────

def test_wind_chill_applied():
    # T=−5°C, V=30 km/h → wind chill well below −5°C
    temp = _dp(-5.0, "°C")
    wind = _dp(30.0, "km/h")
    result = approx_apparent_temp(temp, wind_dp=wind)
    assert result is not None
    assert result.value < -5.0


def test_wind_chill_reference():
    # Environment Canada reference: T=0°C, V=40 km/h → WC ≈ −7 to −10°C range
    temp = _dp(0.0, "°C")
    wind = _dp(40.0, "km/h")
    result = approx_apparent_temp(temp, wind_dp=wind)
    assert result.value == pytest.approx(-9.3, abs=2.0)


def test_wind_chill_ms_input():
    # 10 m/s = 36 km/h; should still apply wind chill below 10°C
    temp = _dp(-5.0, "°C")
    wind = _dp(10.0, "m/s")
    result = approx_apparent_temp(temp, wind_dp=wind)
    assert result is not None
    assert result.value < -5.0


def test_wind_chill_not_applied_warm():
    # T=15°C — neither wind chill (T must be <10) nor heat index (T must be >27)
    temp = _dp(15.0, "°C")
    wind = _dp(30.0, "km/h")
    result = approx_apparent_temp(temp, wind_dp=wind)
    assert result is None


def test_wind_chill_not_applied_low_speed():
    # V ≤ 3 km/h → no wind chill
    temp = _dp(-5.0, "°C")
    wind = _dp(2.0, "km/h")
    result = approx_apparent_temp(temp, wind_dp=wind)
    assert result is None


def test_wind_chill_unit_propagation_fahrenheit():
    temp = _dp(14.0, "°F")  # −10°C
    wind = _dp(30.0, "km/h")
    result = approx_apparent_temp(temp, wind_dp=wind)
    assert result is not None
    assert result.units == "°F"
    assert result.value < 14.0


# ── apparent temperature: heat index ─────────────────────────────────────────

def test_heat_index_applied():
    temp = _dp(35.0, "°C")
    hum = _dp(60.0, "%")
    result = approx_apparent_temp(temp, humidity_dp=hum)
    assert result is not None
    assert result.value > 35.0  # feels hotter


def test_heat_index_reference():
    # Rothfuss-Jakobs polynomial at T=35°C, RH=70% — feels significantly hotter
    temp = _dp(35.0, "°C")
    hum = _dp(70.0, "%")
    result = approx_apparent_temp(temp, humidity_dp=hum)
    assert result.value > 40.0  # always well above ambient


def test_heat_index_not_applied_low_humidity():
    temp = _dp(35.0, "°C")
    hum = _dp(30.0, "%")  # below threshold of 40%
    result = approx_apparent_temp(temp, humidity_dp=hum)
    assert result is None


def test_heat_index_unit_propagation_fahrenheit():
    temp = _dp(95.0, "°F")  # 35°C
    hum = _dp(60.0, "%")
    result = approx_apparent_temp(temp, humidity_dp=hum)
    assert result is not None
    assert result.units == "°F"
    assert result.value > 95.0


# ── fill_derived ─────────────────────────────────────────────────────────────

def _make_wd(**kwargs):
    wd = WeatherData()
    for k, v in kwargs.items():
        setattr(wd, k, v)
    return wd


def test_fill_derived_adds_dew_point():
    wd = _make_wd(
        temperature=_dp(20.0, "°C"),
        humidity=_dp(50.0, "%"),
    )
    result = fill_derived(wd)
    assert result.dewPoint is not None
    assert result.dewPoint.value == pytest.approx(9.3, abs=0.2)


def test_fill_derived_does_not_overwrite_existing_dew_point():
    sentinel = _dp(5.0, "°C")
    wd = _make_wd(
        temperature=_dp(20.0, "°C"),
        humidity=_dp(50.0, "%"),
        dewPoint=sentinel,
    )
    fill_derived(wd)
    assert wd.dewPoint is sentinel


def test_fill_derived_adds_apparent_temp_wind_chill():
    wd = _make_wd(
        temperature=_dp(-5.0, "°C"),
        windSpeed=_dp(30.0, "km/h"),
    )
    fill_derived(wd)
    assert wd.apparentTemperature is not None
    assert wd.apparentTemperature.value < -5.0


def test_fill_derived_replaces_echo_apparent_temp():
    # Provider echoed temperature as apparentTemperature
    temp = _dp(35.0, "°C")
    echo = _dp(35.0, "°C")
    echo.label = "ApparentTemperature"
    wd = _make_wd(
        temperature=temp,
        apparentTemperature=echo,
        humidity=_dp(70.0, "%"),
    )
    fill_derived(wd)
    assert wd.apparentTemperature.value != 35.0  # replaced by heat index


def test_fill_derived_none_is_safe():
    assert fill_derived(None) is None


def test_fill_derived_no_inputs_no_crash():
    wd = WeatherData()
    result = fill_derived(wd)
    assert result.dewPoint is None
    assert result.apparentTemperature is None


# ── snow ──────────────────────────────────────────────────────────────────────

def test_snow_below_threshold():
    temp = _dp(0.0, "°C")
    precip = _dp(3.0, "mm")
    result = approx_snow(temp, precip)
    assert result is not None
    assert result.value == 3.0
    assert result.units == "mm"


def test_snow_at_threshold():
    # Exactly 2°C is still snow
    temp = _dp(2.0, "°C")
    precip = _dp(1.5, "mm")
    assert approx_snow(temp, precip) is not None


def test_snow_above_threshold():
    # Above 2°C → rain, not snow
    temp = _dp(5.0, "°C")
    precip = _dp(3.0, "mm")
    assert approx_snow(temp, precip) is None


def test_snow_fahrenheit_below_threshold():
    # 30°F = −1.1°C → snow
    temp = _dp(30.0, "°F")
    precip = _dp(0.1, "inch")
    result = approx_snow(temp, precip)
    assert result is not None
    assert result.units == "inch"


def test_snow_no_precip():
    assert approx_snow(_dp(0.0, "°C"), None) is None


def test_snow_no_precip_value():
    assert approx_snow(_dp(0.0, "°C"), _dp(None, "mm")) is None


def test_fill_derived_adds_snow():
    wd = _make_wd(
        temperature=_dp(-3.0, "°C"),
        precipitation=_dp(2.0, "mm"),
    )
    fill_derived(wd)
    assert wd.snow is not None
    assert wd.snow.value == 2.0


def test_fill_derived_no_snow_warm():
    wd = _make_wd(
        temperature=_dp(15.0, "°C"),
        precipitation=_dp(5.0, "mm"),
    )
    fill_derived(wd)
    assert wd.snow is None


# ── UV index ─────────────────────────────────────────────────────────────────

# Solar noon at the equator on the vernal equinox: SZA ≈ 0° → UV ≈ 12
_EQUATOR_LAT = 0.0
_EQUATOR_LON = 0.0
_VERNAL_EQUINOX_NOON_UTC = pendulum.datetime(2024, 3, 20, 12, 0, 0, tz="UTC")

# Midnight anywhere → sun below horizon → UV = 0
_MIDNIGHT_UTC = pendulum.datetime(2024, 6, 21, 0, 0, 0, tz="UTC")


def test_uv_near_zero_at_solar_noon_equinox():
    result = approx_uv_index(_EQUATOR_LAT, _EQUATOR_LON, _VERNAL_EQUINOX_NOON_UTC)
    assert result is not None
    assert result.value > 8.0  # clear-sky near-equatorial noon is high UV


def test_uv_zero_at_night():
    # Sun below horizon at midnight → returns UV 0
    result = approx_uv_index(51.5, -0.1, _MIDNIGHT_UTC)  # London
    assert result is not None
    assert result.value == 0.0


def test_uv_reduced_by_cloud_cover():
    # Full cloud cover should significantly reduce UV
    clear = approx_uv_index(_EQUATOR_LAT, _EQUATOR_LON, _VERNAL_EQUINOX_NOON_UTC)
    cloudy = approx_uv_index(_EQUATOR_LAT, _EQUATOR_LON, _VERNAL_EQUINOX_NOON_UTC,
                             cloud_cover_dp=_dp(100.0, "%"))
    assert cloudy.value < clear.value * 0.5


def test_uv_no_clouds_is_clear_sky():
    # 0% cloud cover should give same as no cloud arg
    no_arg = approx_uv_index(_EQUATOR_LAT, _EQUATOR_LON, _VERNAL_EQUINOX_NOON_UTC)
    zero_cloud = approx_uv_index(_EQUATOR_LAT, _EQUATOR_LON, _VERNAL_EQUINOX_NOON_UTC,
                                 cloud_cover_dp=_dp(0.0, "%"))
    assert abs(no_arg.value - zero_cloud.value) < 0.1


def test_fill_derived_adds_uv_with_latlon():
    wd = _make_wd(datetime=_VERNAL_EQUINOX_NOON_UTC)
    fill_derived(wd, lat=_EQUATOR_LAT, lon=_EQUATOR_LON)
    assert wd.uvIndex is not None
    assert wd.uvIndex.value > 0.0


def test_fill_derived_no_uv_without_latlon():
    wd = _make_wd(datetime=_VERNAL_EQUINOX_NOON_UTC)
    fill_derived(wd)  # no lat/lon
    assert wd.uvIndex is None


def test_fill_derived_uv_uses_cloud_cover():
    cloud = _dp(80.0, "%")
    wd_clear = _make_wd(datetime=_VERNAL_EQUINOX_NOON_UTC)
    wd_cloudy = _make_wd(datetime=_VERNAL_EQUINOX_NOON_UTC, cloudCover=cloud)
    fill_derived(wd_clear, lat=_EQUATOR_LAT, lon=_EQUATOR_LON)
    fill_derived(wd_cloudy, lat=_EQUATOR_LAT, lon=_EQUATOR_LON)
    assert wd_cloudy.uvIndex.value < wd_clear.uvIndex.value
