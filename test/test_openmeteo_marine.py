"""Tests for the OpenMeteoMarine provider."""
import json
from pathlib import Path
import responses as resp
from temporalis.providers.openmeteo_marine import OpenMeteoMarine

_MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
_FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "openmeteo_marine.json").read_text())

LAT, LON = 38.7169, -9.1399  # Lisbon coast


@resp.activate
def test_marine_metric_wave_height():
    resp.add(resp.GET, _MARINE_URL, json=_FIXTURE)
    p = OpenMeteoMarine(LAT, LON, units="metric")
    w = p.weather
    assert w.waveHeight is not None
    assert w.waveHeight.units == "m"
    assert w.waveHeight.value >= 0.0


@resp.activate
def test_marine_metric_wave_period_and_direction():
    resp.add(resp.GET, _MARINE_URL, json=_FIXTURE)
    p = OpenMeteoMarine(LAT, LON, units="metric")
    w = p.weather
    assert w.wavePeriod is not None
    assert w.wavePeriod.units == "s"
    assert w.waveDirection is not None
    assert w.waveDirection.units == "°"
    assert 0 <= w.waveDirection.value <= 360


@resp.activate
def test_marine_metric_swell():
    resp.add(resp.GET, _MARINE_URL, json=_FIXTURE)
    p = OpenMeteoMarine(LAT, LON, units="metric")
    w = p.weather
    assert w.swellHeight is not None
    assert w.swellHeight.units == "m"
    assert w.swellPeriod is not None
    assert w.swellDirection is not None


@resp.activate
def test_marine_metric_wind_wave():
    resp.add(resp.GET, _MARINE_URL, json=_FIXTURE)
    p = OpenMeteoMarine(LAT, LON, units="metric")
    w = p.weather
    assert w.windWaveHeight is not None
    assert w.windWaveHeight.units == "m"
    assert w.windWaveDirection is not None
    assert w.windWavePeriod is not None


@resp.activate
def test_marine_metric_current():
    resp.add(resp.GET, _MARINE_URL, json=_FIXTURE)
    p = OpenMeteoMarine(LAT, LON, units="metric")
    w = p.weather
    assert w.currentVelocity is not None
    assert w.currentVelocity.units == "km/h"
    assert w.currentDirection is not None
    assert w.currentDirection.units == "°"


@resp.activate
def test_marine_us_wave_height_in_feet():
    resp.add(resp.GET, _MARINE_URL, json=_FIXTURE)
    p = OpenMeteoMarine(LAT, LON, units="us")
    w = p.weather
    assert w.waveHeight.units == "ft"
    # 1 m ≈ 3.28 ft; Lisbon waves are typically 0.5–4 m → 1.6–13 ft
    assert w.waveHeight.value > 0.0


@resp.activate
def test_marine_us_current_in_mph():
    resp.add(resp.GET, _MARINE_URL, json=_FIXTURE)
    p = OpenMeteoMarine(LAT, LON, units="us")
    w = p.weather
    assert w.currentVelocity.units == "mph"


@resp.activate
def test_marine_us_height_converted_correctly():
    """Conversion factor: 1 m = 3.28084 ft."""
    resp.add(resp.GET, _MARINE_URL, json=_FIXTURE)
    p_metric = OpenMeteoMarine(LAT, LON, units="metric")

    resp.add(resp.GET, _MARINE_URL, json=_FIXTURE)
    p_us = OpenMeteoMarine(LAT, LON, units="us")

    wm = p_metric.weather
    wu = p_us.weather
    if wm.waveHeight is not None and wu.waveHeight is not None:
        ratio = wu.waveHeight.value / wm.waveHeight.value
        assert abs(ratio - 3.28084) < 0.01


@resp.activate
def test_marine_hourly_multiple_entries():
    resp.add(resp.GET, _MARINE_URL, json=_FIXTURE)
    p = OpenMeteoMarine(LAT, LON, units="metric")
    assert len(p.hours) > 1
    for h in p.hours:
        assert h.waveHeight is not None


@resp.activate
def test_marine_daily_forecast():
    resp.add(resp.GET, _MARINE_URL, json=_FIXTURE)
    p = OpenMeteoMarine(LAT, LON, units="metric")
    days = p.days
    assert len(days) > 0
    for d in days:
        assert d.waveHeight is not None
        assert d.waveHeight.units == "m"


@resp.activate
def test_marine_error_on_landlocked():
    """API returns error JSON for landlocked coordinates; provider must raise."""
    resp.add(resp.GET, _MARINE_URL,
             json={"error": True, "reason": "No data for this location"})
    import pytest
    with pytest.raises((ValueError, RuntimeError)):
        OpenMeteoMarine(48.8566, 2.3522)  # Paris


def test_marine_registered():
    """Provider must appear in the WeatherProvider registry."""
    import temporalis.providers.registry  # triggers auto-registration
    from temporalis.providers import WeatherProvider
    assert "openmeteo_marine" in WeatherProvider.available()
