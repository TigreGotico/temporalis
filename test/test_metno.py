import pytest
import responses as resp
from temporalis.providers.metno import MetNo
from temporalis import WeatherData

_URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"

_RESPONSE = {
    "type": "Feature",
    "properties": {
        "timeseries": [
            {
                "time": "2026-04-22T00:00:00Z",
                "data": {
                    "instant": {"details": {
                        "air_temperature": 14.6,
                        "air_pressure_at_sea_level": 1011.1,
                        "cloud_area_fraction": 40.0,
                        "relative_humidity": 78.0,
                        "dew_point_temperature": 10.5,
                        "wind_speed": 4.2,
                        "wind_from_direction": 200.0,
                        "ultraviolet_index_clear_sky": 2.1,
                    }},
                    "next_1_hours": {
                        "summary": {"symbol_code": "partlycloudy_day"},
                        "details": {"precipitation_amount": 0.0},
                    },
                },
            },
            {
                "time": "2026-04-22T01:00:00Z",
                "data": {
                    "instant": {"details": {
                        "air_temperature": 13.8,
                        "air_pressure_at_sea_level": 1011.5,
                        "cloud_area_fraction": 35.0,
                        "relative_humidity": 80.0,
                        "dew_point_temperature": 10.2,
                        "wind_speed": 3.8,
                        "wind_from_direction": 190.0,
                        "ultraviolet_index_clear_sky": 0.0,
                    }},
                    "next_1_hours": {
                        "summary": {"symbol_code": "clearsky_night"},
                        "details": {"precipitation_amount": 0.0},
                    },
                },
            },
            {
                "time": "2026-04-23T00:00:00Z",
                "data": {
                    "instant": {"details": {
                        "air_temperature": 12.0,
                        "air_pressure_at_sea_level": 1013.0,
                        "cloud_area_fraction": 60.0,
                        "relative_humidity": 85.0,
                        "dew_point_temperature": 9.8,
                        "wind_speed": 5.0,
                        "wind_from_direction": 220.0,
                        "ultraviolet_index_clear_sky": 1.5,
                    }},
                    "next_6_hours": {
                        "summary": {"symbol_code": "cloudy"},
                        "details": {"precipitation_amount": 1.2, "air_temperature_max": 18.0, "air_temperature_min": 12.0},
                    },
                },
            },
        ]
    }
}


@resp.activate
def test_metno_weather_returns_weatherdata():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = MetNo(38.72, -9.14)
    assert isinstance(p.weather, WeatherData)
    assert p.weather.temperature is not None
    assert p.weather.temperature.value == 14.6


@resp.activate
def test_metno_hours_non_empty():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = MetNo(38.72, -9.14)
    assert len(p.hours) == 3
    assert p.hours[0].temperature is not None


@resp.activate
def test_metno_days_non_empty():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = MetNo(38.72, -9.14)
    assert len(p.days) >= 1
    assert p.days[0].temperature is not None


@resp.activate
def test_metno_sun_moon():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = MetNo(38.72, -9.14)
    assert p.dawn is not None
    assert p.moon_phase_name is not None
