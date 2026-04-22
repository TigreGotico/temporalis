import pytest
import responses as resp
import temporalis.providers.registry  # triggers registration
from temporalis.providers import WeatherProvider

_OM_URL = "https://api.open-meteo.com/v1/forecast"
_OM_RESPONSE = {
    "latitude": 38.72, "longitude": -9.14, "timezone": "Europe/Lisbon",
    "current_weather": {"time": "2026-04-22T12:00", "temperature": 18.5,
                        "windspeed": 12.0, "winddirection": 270, "weathercode": 2, "is_day": 1},
    "hourly": {"time": ["2026-04-22T00:00"], "temperature_2m": [14.0],
               "apparent_temperature": [12.0], "relativehumidity_2m": [80],
               "dewpoint_2m": [10.0], "cloudcover": [20], "pressure_msl": [1015.0],
               "windspeed_10m": [8.0], "winddirection_10m": [260], "windgusts_10m": [15.0],
               "precipitation": [0.0], "snowfall": [0.0], "visibility": [10000],
               "weathercode": [1], "precipitation_probability": [5], "is_day": [0]},
    "daily": {"time": ["2026-04-22", "2026-04-23", "2026-04-24", "2026-04-25", "2026-04-26"],
              "temperature_2m_max": [22.0]*5, "temperature_2m_min": [12.0]*5,
              "apparent_temperature_max": [20.0]*5, "apparent_temperature_min": [10.0]*5,
              "precipitation_sum": [0.0]*5, "precipitation_hours": [0]*5,
              "precipitation_probability_max": [10]*5, "precipitation_probability_min": [5]*5,
              "precipitation_probability_mean": [7]*5, "weathercode": [1]*5,
              "windspeed_10m_max": [15.0]*5, "windgusts_10m_max": [25.0]*5,
              "winddirection_10m_dominant": [270]*5, "uv_index_max": [5.0]*5,
              "sunrise": ["2026-04-22T06:22"]*5, "sunset": ["2026-04-22T20:15"]*5},
}


def test_available_providers():
    providers = WeatherProvider.available()
    assert "openmeteo" in providers
    assert "ipma" in providers
    assert "metno" in providers
    assert "nws" in providers
    assert "owm" in providers
    assert "openmeteo_airquality" in providers


@resp.activate
def test_get_by_name():
    resp.add(resp.GET, _OM_URL, json=_OM_RESPONSE)
    p = WeatherProvider.get("openmeteo", 38.72, -9.14)
    assert p.weather.temperature is not None
    assert p.weather.temperature.value == 18.5


def test_get_unknown_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        WeatherProvider.get("fakeweather", 38.72, -9.14)
