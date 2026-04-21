import pytest
import responses as resp
from temporalis.providers.nws import NWS
from temporalis import WeatherData

_POINTS_URL = "https://api.weather.gov/points/40.71,-74.0"
_FORECAST_URL = "https://api.weather.gov/gridpoints/OKX/33,42/forecast"
_HOURLY_URL = "https://api.weather.gov/gridpoints/OKX/33,42/forecast/hourly"

_POINTS = {
    "properties": {
        "forecast": _FORECAST_URL,
        "forecastHourly": _HOURLY_URL,
        "timeZone": "America/New_York",
    }
}

_HOURLY_PERIOD = {
    "number": 1, "name": "", "startTime": "2026-04-22T10:00:00-04:00",
    "endTime": "2026-04-22T11:00:00-04:00", "isDaytime": True,
    "temperature": 55, "temperatureUnit": "F",
    "probabilityOfPrecipitation": {"unitCode": "wmoUnit:percent", "value": 10},
    "dewpoint": {"unitCode": "wmoUnit:degC", "value": 5.0},
    "relativeHumidity": {"unitCode": "wmoUnit:percent", "value": 45},
    "windSpeed": "12 mph", "windDirection": "SW",
    "shortForecast": "Partly Cloudy", "detailedForecast": "",
}

_FORECAST_DAY = {
    "number": 1, "name": "Today", "startTime": "2026-04-22T06:00:00-04:00",
    "endTime": "2026-04-22T18:00:00-04:00", "isDaytime": True,
    "temperature": 62, "temperatureUnit": "F",
    "windSpeed": "10 to 15 mph", "windDirection": "S",
    "shortForecast": "Mostly Sunny", "detailedForecast": "Mostly sunny.",
}

_FORECAST_NIGHT = {
    "number": 2, "name": "Tonight", "startTime": "2026-04-22T18:00:00-04:00",
    "endTime": "2026-04-23T06:00:00-04:00", "isDaytime": False,
    "temperature": 45, "temperatureUnit": "F",
    "windSpeed": "5 mph", "windDirection": "N",
    "shortForecast": "Clear", "detailedForecast": "Clear skies.",
}

_HOURLY = {"properties": {"periods": [_HOURLY_PERIOD]}}
_FORECAST = {"properties": {"periods": [_FORECAST_DAY, _FORECAST_NIGHT]}}


def _mock_all():
    resp.add(resp.GET, "https://api.weather.gov/points/40.71,-74.0", json=_POINTS)
    resp.add(resp.GET, _HOURLY_URL, json=_HOURLY)
    resp.add(resp.GET, _FORECAST_URL, json=_FORECAST)


@resp.activate
def test_nws_weather_returns_weatherdata():
    _mock_all()
    p = NWS(40.71, -74.0)
    assert isinstance(p.weather, WeatherData)
    assert p.weather.temperature is not None


@resp.activate
def test_nws_hours_non_empty():
    _mock_all()
    p = NWS(40.71, -74.0)
    assert len(p.hours) >= 1
    assert p.hours[0].temperature is not None


@resp.activate
def test_nws_days_non_empty():
    _mock_all()
    p = NWS(40.71, -74.0)
    assert len(p.days) >= 1
    assert p.days[0].temperature is not None


def test_nws_rejects_non_us():
    with pytest.raises(ValueError, match="NWS only covers the United States"):
        NWS(51.5, -0.1)


@resp.activate
def test_nws_sun_moon():
    _mock_all()
    p = NWS(40.71, -74.0)
    assert p.dawn is not None
    assert p.moon_phase_name is not None
