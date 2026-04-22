"""Tests for the Ensemble provider."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import responses as resp
import pytest

from temporalis.providers.ensemble import Ensemble, _avg_dp, _merge_snapshots
from temporalis import WeatherData, DataPoint

FIXTURES = Path(__file__).parent / "fixtures"
LAT, LON = 38.7169, -9.1399   # Lisbon (covered by IPMA + all global providers)
US_LAT, US_LON = 38.8951, -77.0364  # Washington DC


# ── helper to load fixtures ───────────────────────────────────────────────────

def _load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def _stub_openmeteo(rsps):
    rsps.add(resp.GET, "https://api.open-meteo.com/v1/forecast",
             json=_load("openmeteo_forecast_metric"))


def _stub_metno(rsps):
    rsps.add(resp.GET,
             "https://api.met.no/weatherapi/locationforecast/2.0/complete",
             json=_load("metno_forecast"))


def _stub_airquality(rsps):
    rsps.add(resp.GET, "https://air-quality-api.open-meteo.com/v1/air-quality",
             json={"hourly": {"time": [], "pm10": [], "pm2_5": [], "carbon_monoxide": [],
                              "nitrogen_dioxide": [], "sulphur_dioxide": [], "ozone": [],
                              "uv_index": [], "dust": [], "alder_pollen": [],
                              "birch_pollen": [], "grass_pollen": []}})


def _stub_marine_landlocked(rsps):
    rsps.add(resp.GET, "https://marine-api.open-meteo.com/v1/marine",
             json={"error": True, "reason": "No data for this location"})


def _stub_marine(rsps):
    rsps.add(resp.GET, "https://marine-api.open-meteo.com/v1/marine",
             json=_load("openmeteo_marine"))


def _stub_ipma(rsps):
    rsps.add(resp.GET,
             "https://api.ipma.pt/open-data/observation/meteorology/stations/stations.json",
             json=_load("ipma_stations"))
    rsps.add(resp.GET,
             "https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json",
             json=_load("ipma_observations"))
    daily = _load("ipma_daily_forecast")
    for i in range(10):
        key = str(i)
        if key in daily:
            rsps.add(resp.GET,
                     f"https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/hp-daily-forecast-day{i}.json",
                     json=daily[key])
        else:
            rsps.add(resp.GET,
                     f"https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/hp-daily-forecast-day{i}.json",
                     status=404)
    rsps.add(resp.GET,
             "https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json",
             json=_load("ipma_warnings"))


# ── unit tests for merge helpers ──────────────────────────────────────────────

def _wd(**kwargs):
    w = WeatherData()
    for k, v in kwargs.items():
        setattr(w, k, v)
    return w


def _dp(val, units="°C", label="T"):
    return DataPoint(label, val, units)


def test_avg_dp_mean():
    snaps = [_wd(temperature=_dp(10.0)), _wd(temperature=_dp(20.0))]
    result = _avg_dp("temperature", snaps)
    assert result.value == pytest.approx(15.0)


def test_avg_dp_spread_into_min_max():
    snaps = [_wd(temperature=_dp(10.0)), _wd(temperature=_dp(20.0))]
    result = _avg_dp("temperature", snaps)
    assert result.min_val == pytest.approx(10.0)
    assert result.max_val == pytest.approx(20.0)


def test_avg_dp_single_provider_no_spread():
    snaps = [_wd(temperature=_dp(15.0))]
    result = _avg_dp("temperature", snaps)
    assert result.value == pytest.approx(15.0)
    # DataPoint defaults min_val/max_val to value when not explicitly set
    assert result.min_val == pytest.approx(15.0)
    assert result.max_val == pytest.approx(15.0)


def test_avg_dp_skips_none():
    snaps = [_wd(temperature=_dp(10.0)), _wd()]  # second has no temperature
    result = _avg_dp("temperature", snaps)
    assert result.value == pytest.approx(10.0)


def test_avg_dp_all_none():
    snaps = [_wd(), _wd()]
    assert _avg_dp("temperature", snaps) is None


def test_merge_snapshots_temperature_averaged():
    s1 = _wd(temperature=_dp(10.0), humidity=_dp(60.0, "%", "H"))
    s2 = _wd(temperature=_dp(14.0), humidity=_dp(80.0, "%", "H"))
    merged = _merge_snapshots([s1, s2], ["openmeteo", "metno"], LAT, LON)
    assert merged.temperature.value == pytest.approx(12.0)
    assert merged.humidity.value == pytest.approx(70.0)


def test_merge_snapshots_marine_exclusive():
    s1 = _wd(temperature=_dp(15.0))
    s2 = _wd(waveHeight=_dp(1.5, "m", "WaveHeight"))
    merged = _merge_snapshots([s1, s2], ["openmeteo", "openmeteo_marine"], LAT, LON)
    assert merged.waveHeight is not None
    assert merged.waveHeight.value == pytest.approx(1.5)
    assert merged.temperature is not None


# ── integration tests (mocked HTTP) ──────────────────────────────────────────

@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_lisbon_loads():
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_airquality(resp)
    _stub_ipma(resp)
    _stub_marine(resp)

    p = Ensemble(LAT, LON, units="metric")
    assert len(p.providers) >= 2
    assert "openmeteo" in p.providers or "metno" in p.providers


@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_weather_has_temperature():
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_airquality(resp)
    _stub_ipma(resp)
    _stub_marine(resp)

    p = Ensemble(LAT, LON, units="metric")
    w = p.weather
    assert w.temperature is not None
    assert w.temperature.value is not None
    assert -40 < w.temperature.value < 60


@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_temperature_spread_in_min_max():
    """When multiple providers disagree, spread appears in min/max."""
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_airquality(resp)
    _stub_ipma(resp)
    _stub_marine(resp)

    p = Ensemble(LAT, LON, units="metric")
    w = p.weather
    if len(p.providers) >= 2 and w.temperature is not None:
        assert w.temperature.min_val <= w.temperature.value <= w.temperature.max_val


@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_dew_point_derived_when_missing():
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_airquality(resp)
    _stub_ipma(resp)
    _stub_marine(resp)

    p = Ensemble(LAT, LON, units="metric")
    w = p.weather
    assert w.dewPoint is not None
    assert w.dewPoint.value < w.temperature.value


@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_hourly_multiple_slots():
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_airquality(resp)
    _stub_ipma(resp)
    _stub_marine(resp)

    p = Ensemble(LAT, LON, units="metric")
    assert len(p.hours) > 1


@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_daily_multiple_days():
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_airquality(resp)
    _stub_ipma(resp)
    _stub_marine(resp)

    p = Ensemble(LAT, LON, units="metric")
    assert len(p.days) > 0


@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_marine_fields_when_coastal():
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_airquality(resp)
    _stub_ipma(resp)
    _stub_marine(resp)

    p = Ensemble(LAT, LON, units="metric")
    if "openmeteo_marine" in p.providers:
        w = p.weather
        assert w.waveHeight is not None


@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_marine_silently_skipped_landlocked():
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_airquality(resp)
    _stub_marine_landlocked(resp)

    # Paris — landlocked, no IPMA, no NWS
    p = Ensemble(48.8566, 2.3522, units="metric")
    assert "openmeteo_marine" not in p.providers
    assert p.weather.temperature is not None


@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_alerts_merged():
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_airquality(resp)
    _stub_ipma(resp)
    _stub_marine(resp)

    p = Ensemble(LAT, LON, units="metric")
    # alerts is a list (may be empty if no active warnings)
    assert isinstance(p.alerts, list)


@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_ipma_included_for_portugal():
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_airquality(resp)
    _stub_ipma(resp)
    _stub_marine(resp)

    p = Ensemble(LAT, LON, units="metric")
    assert "ipma" in p.providers


@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_ipma_excluded_outside_portugal():
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_airquality(resp)
    _stub_marine_landlocked(resp)

    p = Ensemble(51.5074, -0.1278, units="metric")  # London
    assert "ipma" not in p.providers


@resp.activate(assert_all_requests_are_fired=False)
def test_ensemble_custom_providers():
    """Custom provider list bypasses auto-selection."""
    from temporalis.providers.openmeteo import OpenMeteo
    from temporalis.providers.metno import MetNo
    _stub_openmeteo(resp)
    _stub_metno(resp)
    _stub_marine_landlocked(resp)  # marine always tried

    p = Ensemble(LAT, LON, units="metric",
                 providers=[("openmeteo", OpenMeteo), ("metno", MetNo)])
    assert set(p.providers) == {"openmeteo", "metno"}
