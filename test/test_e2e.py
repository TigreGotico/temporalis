"""End-to-end tests using real API fixtures captured from live endpoints.

To refresh the fixtures (requires network):
    python test/record_fixtures.py

Tests here exercise the full provider stack — HTTP → parsing → unit conversion
→ derived-field enrichment — without hitting the network.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import responses as resp

FIXTURES = Path(__file__).parent / "fixtures"
LAT, LON = 38.7169, -9.1399   # Lisbon
US_LAT, US_LON = 38.8951, -77.0364  # Washington DC


def _load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


# ── helpers ───────────────────────────────────────────────────────────────────

def _check_weather(wd, *, has_temp=True, has_wind=True, has_humidity=False):
    """Assert the WeatherData object has the expected shape."""
    if has_temp:
        assert wd.temperature is not None
        assert wd.temperature.value is not None
        assert wd.temperature.units != ""
    if has_wind:
        assert wd.windSpeed is not None
        assert wd.windSpeed.value is not None
    if has_humidity:
        assert wd.humidity is not None
        assert wd.humidity.value is not None


# ── OWM ──────────────────────────────────────────────────────────────────────

@resp.activate
def test_owm_metric_current_weather():
    from temporalis.providers.owm import OWM
    resp.add(resp.GET, "https://api.openweathermap.org/data/2.5/weather",
             json=_load("owm_current_metric"))
    resp.add(resp.GET, "https://api.openweathermap.org/data/2.5/forecast",
             json=_load("owm_forecast_metric"))
    resp.add(resp.GET, "https://api.openweathermap.org/data/3.0/onecall", status=401)

    p = OWM(LAT, LON, units="metric", key="testkey")
    w = p.weather
    _check_weather(w, has_humidity=True)
    assert w.temperature.units in ("ºC", "°C")
    assert w.windSpeed.units == "m/s"
    assert w.humidity.units == "%"
    assert -40 < w.temperature.value < 60


@resp.activate
def test_owm_metric_dew_point_derived():
    """OWM doesn't return dewPoint; it must be derived from temp + humidity."""
    from temporalis.providers.owm import OWM
    resp.add(resp.GET, "https://api.openweathermap.org/data/2.5/weather",
             json=_load("owm_current_metric"))
    resp.add(resp.GET, "https://api.openweathermap.org/data/2.5/forecast",
             json=_load("owm_forecast_metric"))
    resp.add(resp.GET, "https://api.openweathermap.org/data/3.0/onecall", status=401)

    p = OWM(LAT, LON, units="metric", key="testkey")
    w = p.weather
    # Both inputs available → derived dew point must be present
    assert w.dewPoint is not None
    assert w.dewPoint.units in ("ºC", "°C")
    assert w.dewPoint.value < w.temperature.value  # always colder than ambient


@resp.activate
def test_owm_imperial_units():
    from temporalis.providers.owm import OWM
    resp.add(resp.GET, "https://api.openweathermap.org/data/2.5/weather",
             json=_load("owm_current_imperial"))
    resp.add(resp.GET, "https://api.openweathermap.org/data/2.5/forecast",
             json=_load("owm_forecast_imperial"))
    resp.add(resp.GET, "https://api.openweathermap.org/data/3.0/onecall", status=401)

    p = OWM(LAT, LON, units="us", key="testkey")
    w = p.weather
    assert w.temperature.units in ("ºF", "°F")
    assert w.windSpeed.units == "mph"
    # Sanity: Lisbon temperature in Fahrenheit should be within normal range
    assert 10 < w.temperature.value < 120


@resp.activate
def test_owm_hourly_forecast_populated():
    from temporalis.providers.owm import OWM
    resp.add(resp.GET, "https://api.openweathermap.org/data/2.5/weather",
             json=_load("owm_current_metric"))
    resp.add(resp.GET, "https://api.openweathermap.org/data/2.5/forecast",
             json=_load("owm_forecast_metric"))
    resp.add(resp.GET, "https://api.openweathermap.org/data/3.0/onecall", status=401)

    p = OWM(LAT, LON, units="metric", key="testkey")
    hours = p.hours
    assert len(hours) > 0
    for h in hours:
        assert h.temperature is not None
        assert h.temperature.units in ("ºC", "°C")


# ── OpenMeteo ─────────────────────────────────────────────────────────────────

@resp.activate
def test_openmeteo_metric_current():
    from temporalis.providers.openmeteo import OpenMeteo
    resp.add(resp.GET, "https://api.open-meteo.com/v1/forecast",
             json=_load("openmeteo_forecast_metric"))

    p = OpenMeteo(LAT, LON, units="metric")
    w = p.weather
    _check_weather(w, has_humidity=True)
    assert w.temperature.units in ("ºC", "°C")
    assert w.windSpeed.units in ("km/h", "m/s", "mph")


@resp.activate
def test_openmeteo_dew_point_or_derived():
    """OpenMeteo returns dewpoint_2m natively; it must appear on weather."""
    from temporalis.providers.openmeteo import OpenMeteo
    resp.add(resp.GET, "https://api.open-meteo.com/v1/forecast",
             json=_load("openmeteo_forecast_metric"))

    p = OpenMeteo(LAT, LON, units="metric")
    w = p.weather
    assert w.dewPoint is not None
    assert w.dewPoint.value < w.temperature.value


@resp.activate
def test_openmeteo_hourly_has_multiple_entries():
    from temporalis.providers.openmeteo import OpenMeteo
    resp.add(resp.GET, "https://api.open-meteo.com/v1/forecast",
             json=_load("openmeteo_forecast_metric"))

    p = OpenMeteo(LAT, LON, units="metric")
    assert len(p.hours) > 1


@resp.activate
def test_openmeteo_daily_forecast():
    from temporalis.providers.openmeteo import OpenMeteo
    resp.add(resp.GET, "https://api.open-meteo.com/v1/forecast",
             json=_load("openmeteo_forecast_metric"))

    p = OpenMeteo(LAT, LON, units="metric")
    days = p.days
    assert len(days) > 0
    for d in days:
        assert d.temperature is not None


# ── MetNo ─────────────────────────────────────────────────────────────────────

@resp.activate
def test_metno_metric_current():
    from temporalis.providers.metno import MetNo
    resp.add(resp.GET, "https://api.met.no/weatherapi/locationforecast/2.0/complete",
             json=_load("metno_forecast"))

    p = MetNo(LAT, LON, units="metric")
    w = p.weather
    _check_weather(w, has_humidity=True)
    assert w.temperature.units in ("ºC", "°C")
    assert w.windSpeed.units == "m/s"
    assert -30 < w.temperature.value < 50


@resp.activate
def test_metno_dew_point_derived():
    """MetNo doesn't provide dewPoint; must be derived from temp + humidity."""
    from temporalis.providers.metno import MetNo
    resp.add(resp.GET, "https://api.met.no/weatherapi/locationforecast/2.0/complete",
             json=_load("metno_forecast"))

    p = MetNo(LAT, LON, units="metric")
    w = p.weather
    assert w.dewPoint is not None
    assert w.dewPoint.value < w.temperature.value


@resp.activate
def test_metno_us_units():
    from temporalis.providers.metno import MetNo
    resp.add(resp.GET, "https://api.met.no/weatherapi/locationforecast/2.0/complete",
             json=_load("metno_forecast"))

    p = MetNo(LAT, LON, units="us")
    w = p.weather
    assert w.temperature.units in ("ºF", "°F")
    assert w.windSpeed.units == "mph"
    assert 10 < w.temperature.value < 120


@resp.activate
def test_metno_hourly_precipitation_unit():
    from temporalis.providers.metno import MetNo
    resp.add(resp.GET, "https://api.met.no/weatherapi/locationforecast/2.0/complete",
             json=_load("metno_forecast"))

    p = MetNo(LAT, LON, units="metric")
    # Find first hour with precipitation
    for h in p.hours:
        if h.precipitation is not None and h.precipitation.value is not None:
            assert h.precipitation.units == "mm"
            break


# ── IPMA ──────────────────────────────────────────────────────────────────────

def _ipma_stubs():
    resp.add(resp.GET,
             "https://api.ipma.pt/open-data/observation/meteorology/stations/stations.json",
             json=_load("ipma_stations"))
    resp.add(resp.GET,
             "https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json",
             json=_load("ipma_observations"))
    daily = _load("ipma_daily_forecast")
    for i in range(10):
        if str(i) in daily:
            resp.add(resp.GET,
                     f"https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/hp-daily-forecast-day{i}.json",
                     json=daily[str(i)])
        else:
            resp.add(resp.GET,
                     f"https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/hp-daily-forecast-day{i}.json",
                     status=404)
    resp.add(resp.GET,
             "https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json",
             json=_load("ipma_warnings"))


@resp.activate
def test_ipma_metric_current():
    from temporalis.providers.ipma import IPMA
    _ipma_stubs()
    p = IPMA(LAT, LON, units="metric")
    w = p.weather
    _check_weather(w, has_humidity=True)
    assert w.temperature.units in ("ºC", "°C")
    assert w.windSpeed.units == "m/s"


@resp.activate
def test_ipma_dew_point_derived():
    """IPMA doesn't return dewPoint; must be derived from temp + humidity."""
    from temporalis.providers.ipma import IPMA
    _ipma_stubs()
    p = IPMA(LAT, LON, units="metric")
    w = p.weather
    assert w.dewPoint is not None
    assert w.dewPoint.value < w.temperature.value


@resp.activate
def test_ipma_daily_precipitation_is_probability():
    """IPMA daily gives precipitaProb (0–100); stored as prob fraction, not an amount."""
    from temporalis.providers.ipma import IPMA
    _ipma_stubs()
    p = IPMA(LAT, LON, units="metric")
    for d in p.days:
        if d.precipitation is not None:
            assert d.precipitation.value is None
            assert d.precipitation.prob is not None
            assert 0.0 <= d.precipitation.prob <= 1.0
            break
    else:
        pytest.skip("No days with precipitation probability in fixture")


@resp.activate
def test_ipma_us_temperature_in_fahrenheit():
    from temporalis.providers.ipma import IPMA
    _ipma_stubs()
    p = IPMA(LAT, LON, units="us")
    w = p.weather
    assert w.temperature.units in ("ºF", "°F")
    assert 32 < w.temperature.value < 120


# ── NWS ───────────────────────────────────────────────────────────────────────

def _nws_stubs():
    resp.add(resp.GET,
             f"https://api.weather.gov/points/{US_LAT},{US_LON}",
             json=_load("nws_points"))
    props = _load("nws_points").get("properties", {})
    if props.get("forecast"):
        resp.add(resp.GET, props["forecast"], json=_load("nws_forecast"))
    if props.get("forecastHourly"):
        resp.add(resp.GET, props["forecastHourly"], json=_load("nws_hourly"))
    if props.get("observationStations"):
        resp.add(resp.GET, props["observationStations"], json=_load("nws_obs_stations"))
    features = _load("nws_obs_stations").get("features", [])
    if features:
        sid = features[0]["properties"]["stationIdentifier"]
        resp.add(resp.GET,
                 f"https://api.weather.gov/stations/{sid}/observations/latest",
                 json=_load("nws_latest_obs"))


@resp.activate
def test_nws_metric_current():
    from temporalis.providers.nws import NWS
    _nws_stubs()
    p = NWS(US_LAT, US_LON, units="metric")
    w = p.weather
    _check_weather(w)
    assert w.temperature.units in ("ºC", "°C")


@resp.activate
def test_nws_us_temperature_fahrenheit():
    from temporalis.providers.nws import NWS
    _nws_stubs()
    p = NWS(US_LAT, US_LON, units="us")
    w = p.weather
    assert w.temperature.units in ("ºF", "°F")
    assert -30 < w.temperature.value < 130


@resp.activate
def test_nws_dew_point_unit_correct():
    """NWS provides dew point natively in °C regardless of units param."""
    from temporalis.providers.nws import NWS
    _nws_stubs()
    p_metric = NWS(US_LAT, US_LON, units="metric")
    p_us = NWS(US_LAT, US_LON, units="us")

    # Rebuild stubs for the second call
    _nws_stubs()

    w_metric = p_metric.weather
    w_us = p_us.weather

    if w_metric.dewPoint is not None:
        assert w_metric.dewPoint.units in ("ºC", "°C")
    if w_us.dewPoint is not None:
        assert w_us.dewPoint.units in ("ºF", "°F")


@resp.activate
def test_nws_daily_forecast():
    from temporalis.providers.nws import NWS
    _nws_stubs()
    p = NWS(US_LAT, US_LON, units="metric")
    days = p.days
    assert len(days) > 0
    assert days[0].temperature is not None


# ── cross-provider shape invariants ──────────────────────────────────────────

@resp.activate
def test_all_providers_have_weather_property():
    """Every provider must expose a .weather WeatherData with at least temperature."""
    from temporalis.providers.owm import OWM
    from temporalis.providers.openmeteo import OpenMeteo
    from temporalis.providers.metno import MetNo
    from temporalis.providers.ipma import IPMA

    # OWM
    resp.add(resp.GET, "https://api.openweathermap.org/data/2.5/weather",
             json=_load("owm_current_metric"))
    resp.add(resp.GET, "https://api.openweathermap.org/data/2.5/forecast",
             json=_load("owm_forecast_metric"))
    resp.add(resp.GET, "https://api.openweathermap.org/data/3.0/onecall", status=401)

    # OpenMeteo
    resp.add(resp.GET, "https://api.open-meteo.com/v1/forecast",
             json=_load("openmeteo_forecast_metric"))

    # MetNo
    resp.add(resp.GET, "https://api.met.no/weatherapi/locationforecast/2.0/complete",
             json=_load("metno_forecast"))

    # IPMA
    _ipma_stubs()

    providers = [
        OWM(LAT, LON, units="metric", key="testkey"),
        OpenMeteo(LAT, LON, units="metric"),
        MetNo(LAT, LON, units="metric"),
        IPMA(LAT, LON, units="metric"),
    ]
    for p in providers:
        w = p.weather
        assert w is not None, f"{type(p).__name__} returned None for .weather"
        assert w.temperature is not None, f"{type(p).__name__} has no temperature"
        assert w.temperature.value is not None
