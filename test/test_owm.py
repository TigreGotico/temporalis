import responses as resp
from temporalis.providers.owm import OWM
from temporalis import WeatherData

OWM_CURRENT = {
    "base": "stations", "clouds": {"all": 20}, "cod": 200,
    "coord": {"lat": 38.72, "lon": -9.14}, "dt": 1592522239,
    "main": {"feels_like": 15.59, "humidity": 87, "pressure": 1019,
             "temp": 16.67, "temp_max": 17.78, "temp_min": 15.56},
    "name": "Socorro",
    "sys": {"country": "PT", "sunrise": 1592543502, "sunset": 1592597056},
    "timezone": 3600, "visibility": 10000,
    "weather": [{"description": "few clouds", "icon": "02n", "main": "Clouds"}],
    "wind": {"deg": 330, "speed": 3.6},
}

OWM_FORECAST = {
    "list": [{
        "dt": 1592533200,
        "main": {"temp": 15.0, "temp_min": 14.0, "temp_max": 16.0,
                 "feels_like": 14.5, "humidity": 80, "pressure": 1018},
        "weather": [{"main": "Clouds", "description": "few clouds"}],
        "wind": {"speed": 3.0, "deg": 340},
        "clouds": {"all": 15},
        "visibility": 9000,
    }],
    "city": {"name": "Lisbon", "coord": {"lat": 38.72, "lon": -9.14}},
}


_ONECALL_URL = "https://api.openweathermap.org/data/3.0/onecall"


def _add_stubs(rsps, *, onecall_status=401):
    rsps.add(rsps.GET, "https://api.openweathermap.org/data/2.5/weather",
             json=OWM_CURRENT)
    rsps.add(rsps.GET, "https://api.openweathermap.org/data/2.5/forecast",
             json=OWM_FORECAST)
    rsps.add(rsps.GET, _ONECALL_URL, status=onecall_status)


@resp.activate
def test_owm_weather_returns_weatherdata():
    _add_stubs(resp)
    p = OWM(38.72, -9.14, key="testkey")
    assert isinstance(p.weather, WeatherData)
    assert p.weather.temperature is not None
    assert p.weather.temperature.value == 16.67


@resp.activate
def test_owm_days_and_hours():
    _add_stubs(resp)
    p = OWM(38.72, -9.14, key="testkey")
    assert len(p.hours) > 0
    assert len(p.days) > 0


def test_owm_requires_no_key_with_default():
    import responses as resp2

    @resp2.activate
    def _run():
        _add_stubs(resp2)
        p = OWM(38.72, -9.14)
        assert p.key == OWM.default_key

    _run()
