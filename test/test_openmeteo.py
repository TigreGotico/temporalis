import responses as resp
from temporalis.providers.openmeteo import OpenMeteo
from temporalis import WeatherData

_URL = "https://api.open-meteo.com/v1/forecast"

_RESPONSE = {
    "latitude": 38.72,
    "longitude": -9.14,
    "timezone": "Europe/Lisbon",
    "current_weather": {
        "time": "2026-04-22T12:00",
        "temperature": 18.5,
        "windspeed": 12.0,
        "winddirection": 270,
        "weathercode": 2,
        "is_day": 1,
    },
    "hourly": {
        "time": ["2026-04-22T00:00", "2026-04-22T01:00", "2026-04-22T02:00"],
        "temperature_2m": [14.0, 13.5, 13.0],
        "apparent_temperature": [12.0, 11.5, 11.0],
        "relativehumidity_2m": [80, 82, 84],
        "dewpoint_2m": [10.0, 10.5, 11.0],
        "cloudcover": [20, 25, 30],
        "pressure_msl": [1015.0, 1014.5, 1014.0],
        "windspeed_10m": [8.0, 7.5, 7.0],
        "winddirection_10m": [260, 265, 270],
        "windgusts_10m": [15.0, 14.0, 13.0],
        "precipitation": [0.0, 0.0, 0.1],
        "snowfall": [0.0, 0.0, 0.0],
        "visibility": [10000, 10000, 9500],
        "weathercode": [1, 1, 2],
        "precipitation_probability": [5, 5, 10],
        "is_day": [0, 0, 0],
    },
    "daily": {
        "time": ["2026-04-22", "2026-04-23", "2026-04-24",
                 "2026-04-25", "2026-04-26", "2026-04-27", "2026-04-28"],
        "temperature_2m_max": [22.0, 21.0, 20.0, 19.0, 18.0, 17.0, 16.0],
        "temperature_2m_min": [12.0, 11.0, 10.0, 9.0, 8.0, 7.0, 6.0],
        "apparent_temperature_max": [20.0, 19.0, 18.0, 17.0, 16.0, 15.0, 14.0],
        "apparent_temperature_min": [10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0],
        "precipitation_sum": [0.0, 1.5, 0.5, 0.0, 2.0, 0.0, 0.0],
        "precipitation_hours": [0, 2, 1, 0, 3, 0, 0],
        "precipitation_probability_max": [10, 60, 30, 5, 70, 10, 5],
        "precipitation_probability_min": [5, 40, 20, 2, 50, 5, 2],
        "precipitation_probability_mean": [7, 50, 25, 3, 60, 7, 3],
        "weathercode": [1, 63, 61, 0, 65, 1, 0],
        "windspeed_10m_max": [15.0, 20.0, 18.0, 12.0, 22.0, 10.0, 8.0],
        "windgusts_10m_max": [25.0, 35.0, 30.0, 20.0, 40.0, 18.0, 15.0],
        "winddirection_10m_dominant": [270, 280, 260, 250, 290, 240, 230],
        "uv_index_max": [5.0, 3.0, 4.0, 6.0, 2.0, 5.0, 6.0],
        "sunrise": ["2026-04-22T06:22", "2026-04-23T06:21", "2026-04-24T06:19",
                    "2026-04-25T06:18", "2026-04-26T06:16", "2026-04-27T06:15", "2026-04-28T06:13"],
        "sunset": ["2026-04-22T20:15", "2026-04-23T20:16", "2026-04-24T20:17",
                   "2026-04-25T20:19", "2026-04-26T20:20", "2026-04-27T20:21", "2026-04-28T20:23"],
    },
}


@resp.activate
def test_openmeteo_weather_returns_weatherdata():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = OpenMeteo(38.72, -9.14)
    assert isinstance(p.weather, WeatherData)
    assert p.weather.temperature is not None
    assert p.weather.temperature.value == 18.5


@resp.activate
def test_openmeteo_hours_non_empty():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = OpenMeteo(38.72, -9.14)
    assert len(p.hours) == 3
    assert p.hours[0].temperature is not None
    assert p.hours[0].humidity is not None


@resp.activate
def test_openmeteo_days_non_empty():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = OpenMeteo(38.72, -9.14)
    assert len(p.days) >= 5
    assert p.days[0].temperature is not None


@resp.activate
def test_openmeteo_sun_moon():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = OpenMeteo(38.72, -9.14)
    assert p.dawn is not None
    assert p.moon_phase_name is not None
