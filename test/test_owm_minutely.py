import responses as resp
from temporalis.providers.owm import OWM
from temporalis import MinutelyForecast, MinutelyData

_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
_ONECALL_URL = "https://api.openweathermap.org/data/3.0/onecall"

_CURRENT = {
    "dt": 1714000000, "timezone": 0,
    "coord": {"lat": 38.72, "lon": -9.14},
    "main": {"temp": 18.0, "feels_like": 17.0, "humidity": 70,
             "pressure": 1015, "temp_min": 16.0, "temp_max": 20.0},
    "wind": {"speed": 3.0, "deg": 270},
    "clouds": {"all": 10},
    "weather": [{"main": "Clear", "description": "clear sky", "icon": "01d"}],
    "visibility": 10000,
}
_FORECAST = {
    "list": [{
        "dt": 1714000000,
        "main": {"temp": 18.0, "temp_min": 17.0, "temp_max": 19.0,
                 "feels_like": 17.5, "humidity": 70, "pressure": 1015},
        "weather": [{"main": "Clear", "description": "clear sky"}],
        "wind": {"speed": 3.0, "deg": 270},
        "clouds": {"all": 10},
        "visibility": 10000,
    }],
    "city": {"name": "Lisbon", "coord": {"lat": 38.72, "lon": -9.14}},
}

_ONECALL = {
    "minutely": [
        {"dt": 1714000060, "precipitation": 0.0},
        {"dt": 1714000120, "precipitation": 1.5},
        {"dt": 1714000180, "precipitation": 2.3},
    ]
}

_ONECALL_EMPTY = {}   # no minutely key — e.g. no radar coverage


def _add_base(rsps):
    rsps.add(resp.GET, _CURRENT_URL, json=_CURRENT)
    rsps.add(resp.GET, _FORECAST_URL, json=_FORECAST)


@resp.activate
def test_minutely_returns_forecast():
    _add_base(resp)
    resp.add(resp.GET, _ONECALL_URL, json=_ONECALL)
    p = OWM(38.72, -9.14)
    mf = p.minutely
    assert isinstance(mf, MinutelyForecast)
    assert len(mf) == 3


@resp.activate
def test_minutely_values():
    _add_base(resp)
    resp.add(resp.GET, _ONECALL_URL, json=_ONECALL)
    p = OWM(38.72, -9.14)
    minutes = list(p.minutely)
    assert isinstance(minutes[0], MinutelyData)
    assert minutes[0].precipitation.value == 0.0
    assert minutes[1].precipitation.value == 1.5
    assert minutes[2].precipitation.value == 2.3


@resp.activate
def test_minutely_units():
    _add_base(resp)
    resp.add(resp.GET, _ONECALL_URL, json=_ONECALL)
    p = OWM(38.72, -9.14)
    assert p.minutely[0].precipitation.units == "mm/h"


@resp.activate
def test_minutely_empty_when_no_radar():
    _add_base(resp)
    resp.add(resp.GET, _ONECALL_URL, json=_ONECALL_EMPTY)
    p = OWM(38.72, -9.14)
    assert len(p.minutely) == 0


@resp.activate
def test_minutely_empty_on_auth_failure():
    _add_base(resp)
    resp.add(resp.GET, _ONECALL_URL, status=401)
    p = OWM(38.72, -9.14)
    assert len(p.minutely) == 0
