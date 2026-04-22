import responses as resp
from temporalis.providers.openmeteo import OpenMeteo
from temporalis import WeatherData

_URL = "https://archive-api.open-meteo.com/v1/archive"

_RESPONSE = {
    "latitude": 38.72,
    "longitude": -9.14,
    "timezone": "Europe/Lisbon",
    "daily": {
        "time": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "temperature_2m_max": [14.0, 15.0, 13.0],
        "temperature_2m_min": [8.0, 9.0, 7.0],
        "apparent_temperature_max": [12.0, 13.0, 11.0],
        "apparent_temperature_min": [6.0, 7.0, 5.0],
        "precipitation_sum": [0.0, 1.5, 3.2],
        "precipitation_hours": [0, 3, 5],
        "weathercode": [1, 63, 61],
        "windspeed_10m_max": [10.0, 20.0, 18.0],
        "windgusts_10m_max": [18.0, 35.0, 30.0],
        "winddirection_10m_dominant": [270, 280, 260],
        "shortwave_radiation_sum": [8.5, 3.2, 2.1],
    },
    "hourly": {
        "time": ["2024-01-01T00:00", "2024-01-01T01:00", "2024-01-01T02:00"],
        "temperature_2m": [9.0, 8.5, 8.0],
        "apparent_temperature": [7.0, 6.5, 6.0],
        "relativehumidity_2m": [82, 84, 86],
        "dewpoint_2m": [6.5, 6.0, 5.8],
        "cloudcover": [30, 35, 40],
        "pressure_msl": [1018.0, 1017.5, 1017.0],
        "windspeed_10m": [8.0, 9.0, 10.0],
        "winddirection_10m": [265, 270, 275],
        "windgusts_10m": [15.0, 16.0, 18.0],
        "precipitation": [0.0, 0.0, 0.2],
        "snowfall": [0.0, 0.0, 0.0],
        "visibility": [10000, 10000, 9000],
        "weathercode": [1, 1, 61],
    },
}


@resp.activate
def test_historical_days():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = OpenMeteo(38.72, -9.14, start="2024-01-01", end="2024-01-03")
    assert p.historical is True
    assert len(p.days) == 3
    assert p.days[0].temperature is not None
    assert p.days[0].temperature.value == 11.0  # avg of 14+8


@resp.activate
def test_historical_hours():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = OpenMeteo(38.72, -9.14, start="2024-01-01", end="2024-01-03")
    assert len(p.hours) == 3
    assert p.hours[0].temperature is not None
    assert p.hours[0].humidity is not None


@resp.activate
def test_historical_weather():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = OpenMeteo(38.72, -9.14, start="2024-01-01", end="2024-01-03")
    assert isinstance(p.weather, WeatherData)
    assert p.weather.temperature is not None


@resp.activate
def test_historical_sun_moon():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    p = OpenMeteo(38.72, -9.14, start="2024-01-01", end="2024-01-03")
    assert p.dawn is not None
    assert p.moon_phase_name is not None
