"""Unit conversion correctness tests across all providers.

Each test verifies that DataPoint.value holds the correct converted number
and DataPoint.units holds the correct unit string for both metric and US modes.
"""
import responses as resp
import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

def _approx(a, b, tol=0.2):
    """Loose tolerance for floating-point converted values."""
    return abs(a - b) <= tol


# ── DataPoint / WeatherData as_dict zero-value preservation ──────────────────

from temporalis import DataPoint, WeatherData


def test_datapoint_as_dict_keeps_zero_value():
    dp = DataPoint("Precipitation", 0.0, "mm")
    d = dp.as_dict()
    assert "value" in d
    assert d["value"] == 0.0


def test_datapoint_as_dict_keeps_zero_min_max():
    dp = DataPoint("Temperature", 0.0, "ºC", min_val=0.0, max_val=0.0)
    d = dp.as_dict()
    assert d["min_val"] == 0.0
    assert d["max_val"] == 0.0


def test_weatherdata_as_dict_keeps_zero_precipitation():
    w = WeatherData()
    w.precipitation = DataPoint("Precipitation", 0.0, "mm")
    d = w.as_dict()
    assert "precipitation" in d
    assert d["precipitation"]["value"] == 0.0


def test_datapoint_from_dict_round_trip():
    """from_dict must restore value/min/max/prob correctly."""
    original = DataPoint("Temperature", 15.5, "ºC", min_val=10.0, max_val=20.0,
                         prob=0.8, prob_min=0.6, prob_max=0.9)
    d = original.as_dict()
    restored = DataPoint.from_dict(d)
    assert restored.value == 15.5
    assert restored.min_val == 10.0
    assert restored.max_val == 20.0
    assert restored.prob == 0.8


# ── Open-Meteo unit params ────────────────────────────────────────────────────

_OM_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _om_response(temp_c=18.0, windspeed_kmh=12.0, precip_mm=2.5):
    return {
        "latitude": 38.72, "longitude": -9.14, "timezone": "Europe/Lisbon",
        "current_weather": {
            "time": "2026-04-22T12:00", "temperature": temp_c,
            "windspeed": windspeed_kmh, "winddirection": 270, "weathercode": 1,
        },
        "hourly": {
            "time": ["2026-04-22T12:00"],
            "temperature_2m": [temp_c], "apparent_temperature": [temp_c - 2],
            "relativehumidity_2m": [65], "dewpoint_2m": [10.0],
            "cloudcover": [20], "pressure_msl": [1015.0],
            "windspeed_10m": [windspeed_kmh], "winddirection_10m": [270],
            "windgusts_10m": [20.0], "precipitation": [precip_mm],
            "snowfall": [0.0], "visibility": [10000], "weathercode": [1],
            "precipitation_probability": [30], "is_day": [1],
        },
        "daily": {
            "time": ["2026-04-22"],
            "temperature_2m_max": [22.0], "temperature_2m_min": [14.0],
            "apparent_temperature_max": [20.0], "apparent_temperature_min": [12.0],
            "precipitation_sum": [precip_mm],
            "precipitation_hours": [2], "precipitation_probability_max": [40],
            "precipitation_probability_min": [10], "precipitation_probability_mean": [25],
            "weathercode": [1], "windspeed_10m_max": [windspeed_kmh],
            "windgusts_10m_max": [25.0], "winddirection_10m_dominant": [270],
            "uv_index_max": [5.0], "sunrise": ["2026-04-22T06:22"],
            "sunset": ["2026-04-22T20:15"],
        },
    }


@resp.activate
def test_openmeteo_metric_units():
    from temporalis.providers.openmeteo import OpenMeteo
    resp.add(resp.GET, _OM_FORECAST_URL, json=_om_response(temp_c=18.0, windspeed_kmh=12.0, precip_mm=2.5))
    p = OpenMeteo(38.72, -9.14, units="metric")
    w = p.weather
    assert w.temperature.units == "ºC"
    assert w.temperature.value == 18.0
    h = p.hours[0]
    assert h.windSpeed.units == "km/h"
    assert h.precipitation.units == "mm"
    assert h.precipitation.value == 2.5


@resp.activate
def test_openmeteo_us_units():
    from temporalis.providers.openmeteo import OpenMeteo
    # Open-Meteo natively converts when we pass temperature_unit=fahrenheit etc.
    # The mock simulates what the API would return after conversion.
    resp.add(resp.GET, _OM_FORECAST_URL, json=_om_response(temp_c=64.4, windspeed_kmh=7.46, precip_mm=0.098))
    p = OpenMeteo(38.72, -9.14, units="us")
    w = p.weather
    assert w.temperature.units == "ºF"
    h = p.hours[0]
    assert h.windSpeed.units == "mph"
    assert h.precipitation.units == "inch"


# ── Met.no unit conversions ───────────────────────────────────────────────────

_METNO_URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"


def _metno_response(temp_c=15.0, wind_ms=5.0, precip_mm=1.2):
    return {
        "properties": {
            "timeseries": [{
                "time": "2026-04-22T12:00:00Z",
                "data": {
                    "instant": {"details": {
                        "air_temperature": temp_c,
                        "dew_point_temperature": temp_c - 5,
                        "relative_humidity": 70.0,
                        "cloud_area_fraction": 30.0,
                        "air_pressure_at_sea_level": 1015.0,
                        "wind_speed": wind_ms,
                        "wind_from_direction": 270.0,
                    }},
                    "next_1_hours": {
                        "summary": {"symbol_code": "clearsky_day"},
                        "details": {"precipitation_amount": precip_mm},
                    },
                },
            }],
        },
    }


@resp.activate
def test_metno_metric_units():
    from temporalis.providers.metno import MetNo
    resp.add(resp.GET, _METNO_URL, json=_metno_response(temp_c=15.0, wind_ms=5.0, precip_mm=1.2))
    p = MetNo(38.72, -9.14, units="metric")
    h = p.hours[0]
    assert h.temperature.units == "ºC"
    assert h.temperature.value == 15.0
    assert h.windSpeed.units == "m/s"
    assert h.windSpeed.value == 5.0
    assert h.precipitation.units == "mm"
    assert h.precipitation.value == 1.2


@resp.activate
def test_metno_us_units_temperature():
    from temporalis.providers.metno import MetNo
    resp.add(resp.GET, _METNO_URL, json=_metno_response(temp_c=0.0))
    p = MetNo(38.72, -9.14, units="us")
    h = p.hours[0]
    assert h.temperature.units == "ºF"
    assert h.temperature.value == 32.0  # 0°C = 32°F


@resp.activate
def test_metno_us_units_wind():
    from temporalis.providers.metno import MetNo
    resp.add(resp.GET, _METNO_URL, json=_metno_response(wind_ms=10.0))
    p = MetNo(38.72, -9.14, units="us")
    h = p.hours[0]
    assert h.windSpeed.units == "mph"
    assert _approx(h.windSpeed.value, 22.4)  # 10 m/s ≈ 22.4 mph


@resp.activate
def test_metno_us_units_precipitation():
    from temporalis.providers.metno import MetNo
    resp.add(resp.GET, _METNO_URL, json=_metno_response(precip_mm=25.4))
    p = MetNo(38.72, -9.14, units="us")
    h = p.hours[0]
    assert h.precipitation.units == "inch"
    assert _approx(h.precipitation.value, 1.0)  # 25.4 mm = 1 inch


@resp.activate
def test_metno_zero_precipitation_preserved():
    from temporalis.providers.metno import MetNo
    resp.add(resp.GET, _METNO_URL, json=_metno_response(precip_mm=0.0))
    p = MetNo(38.72, -9.14, units="metric")
    h = p.hours[0]
    assert h.precipitation is not None
    assert h.precipitation.value == 0.0


# ── NWS unit conversions ──────────────────────────────────────────────────────

_NWS_POINTS_URL = "https://api.weather.gov/points/40.71,-74.01"
_NWS_HOURLY_URL = "https://api.weather.gov/gridpoints/OKX/32,35/forecast/hourly"
_NWS_FORECAST_URL = "https://api.weather.gov/gridpoints/OKX/32,35/forecast"
_NWS_ALERTS_URL = "https://api.weather.gov/alerts/active"

_NWS_POINTS = {
    "properties": {
        "forecast": _NWS_FORECAST_URL,
        "forecastHourly": _NWS_HOURLY_URL,
        "timeZone": "America/New_York",
    }
}

_NWS_ALERTS_EMPTY = {"features": []}


def _nws_hourly(temp_f=68.0, dew_c=10.0, wind_mph=15.0):
    return {
        "properties": {"periods": [{
            "startTime": "2026-04-22T12:00:00-05:00",
            "temperature": temp_f, "temperatureUnit": "F",
            "relativeHumidity": {"value": 60},
            "dewpoint": {"value": dew_c, "unitCode": "wmoUnit:degC"},
            "probabilityOfPrecipitation": {"value": 30},
            "windSpeed": f"{wind_mph} mph",
            "windDirection": "W",
            "shortForecast": "Sunny",
            "isDaytime": True,
        }]}
    }


_NWS_FORECAST_EMPTY = {"properties": {"periods": []}}


@resp.activate
def test_nws_metric_temperature():
    from temporalis.providers.nws import NWS
    resp.add(resp.GET, _NWS_POINTS_URL, json=_NWS_POINTS)
    resp.add(resp.GET, _NWS_HOURLY_URL, json=_nws_hourly(temp_f=32.0))
    resp.add(resp.GET, _NWS_FORECAST_URL, json=_NWS_FORECAST_EMPTY)
    resp.add(resp.GET, _NWS_ALERTS_URL, json=_NWS_ALERTS_EMPTY)
    p = NWS(40.71, -74.01, units="metric")
    h = p.hours[0]
    assert h.temperature.units == "ºC"
    assert h.temperature.value == 0.0  # 32°F = 0°C


@resp.activate
def test_nws_us_temperature():
    from temporalis.providers.nws import NWS
    resp.add(resp.GET, _NWS_POINTS_URL, json=_NWS_POINTS)
    resp.add(resp.GET, _NWS_HOURLY_URL, json=_nws_hourly(temp_f=68.0))
    resp.add(resp.GET, _NWS_FORECAST_URL, json=_NWS_FORECAST_EMPTY)
    resp.add(resp.GET, _NWS_ALERTS_URL, json=_NWS_ALERTS_EMPTY)
    p = NWS(40.71, -74.01, units="us")
    h = p.hours[0]
    assert h.temperature.units == "ºF"
    assert h.temperature.value == 68.0


@resp.activate
def test_nws_metric_wind():
    from temporalis.providers.nws import NWS
    resp.add(resp.GET, _NWS_POINTS_URL, json=_NWS_POINTS)
    resp.add(resp.GET, _NWS_HOURLY_URL, json=_nws_hourly(wind_mph=22.37))
    resp.add(resp.GET, _NWS_FORECAST_URL, json=_NWS_FORECAST_EMPTY)
    resp.add(resp.GET, _NWS_ALERTS_URL, json=_NWS_ALERTS_EMPTY)
    p = NWS(40.71, -74.01, units="metric")
    h = p.hours[0]
    assert h.windSpeed.units == "m/s"
    assert _approx(h.windSpeed.value, 10.0)  # 22.37 mph ≈ 10 m/s


@resp.activate
def test_nws_dewpoint_metric():
    """Dew point comes from API in Celsius; must stay Celsius in metric mode."""
    from temporalis.providers.nws import NWS
    resp.add(resp.GET, _NWS_POINTS_URL, json=_NWS_POINTS)
    resp.add(resp.GET, _NWS_HOURLY_URL, json=_nws_hourly(dew_c=10.0))
    resp.add(resp.GET, _NWS_FORECAST_URL, json=_NWS_FORECAST_EMPTY)
    resp.add(resp.GET, _NWS_ALERTS_URL, json=_NWS_ALERTS_EMPTY)
    p = NWS(40.71, -74.01, units="metric")
    h = p.hours[0]
    assert h.dewPoint.units == "ºC"
    assert h.dewPoint.value == 10.0


@resp.activate
def test_nws_dewpoint_us():
    """Dew point comes from API in Celsius; must be converted to °F in US mode."""
    from temporalis.providers.nws import NWS
    resp.add(resp.GET, _NWS_POINTS_URL, json=_NWS_POINTS)
    resp.add(resp.GET, _NWS_HOURLY_URL, json=_nws_hourly(dew_c=0.0))
    resp.add(resp.GET, _NWS_FORECAST_URL, json=_NWS_FORECAST_EMPTY)
    resp.add(resp.GET, _NWS_ALERTS_URL, json=_NWS_ALERTS_EMPTY)
    p = NWS(40.71, -74.01, units="us")
    h = p.hours[0]
    assert h.dewPoint.units == "ºF"
    assert h.dewPoint.value == 32.0  # 0°C = 32°F


@resp.activate
def test_nws_precipitation_unit_metric():
    from temporalis.providers.nws import NWS
    resp.add(resp.GET, _NWS_POINTS_URL, json=_NWS_POINTS)
    resp.add(resp.GET, _NWS_HOURLY_URL, json=_nws_hourly())
    resp.add(resp.GET, _NWS_FORECAST_URL, json=_NWS_FORECAST_EMPTY)
    resp.add(resp.GET, _NWS_ALERTS_URL, json=_NWS_ALERTS_EMPTY)
    p = NWS(40.71, -74.01, units="metric")
    h = p.hours[0]
    assert h.precipitation.units == "mm"


@resp.activate
def test_nws_precipitation_unit_us():
    from temporalis.providers.nws import NWS
    resp.add(resp.GET, _NWS_POINTS_URL, json=_NWS_POINTS)
    resp.add(resp.GET, _NWS_HOURLY_URL, json=_nws_hourly())
    resp.add(resp.GET, _NWS_FORECAST_URL, json=_NWS_FORECAST_EMPTY)
    resp.add(resp.GET, _NWS_ALERTS_URL, json=_NWS_ALERTS_EMPTY)
    p = NWS(40.71, -74.01, units="us")
    h = p.hours[0]
    assert h.precipitation.units == "inch"


# ── IPMA unit conversions ─────────────────────────────────────────────────────

_IPMA_BASE = "https://api.ipma.pt/open-data"
_IPMA_STATIONS_URL = f"{_IPMA_BASE}/observation/meteorology/stations/stations.json"
_IPMA_OBS_URL = f"{_IPMA_BASE}/observation/meteorology/stations/observations.json"
_IPMA_DAY0_URL = f"{_IPMA_BASE}/forecast/meteorology/cities/daily/hp-daily-forecast-day0.json"
_IPMA_DAY1_URL = f"{_IPMA_BASE}/forecast/meteorology/cities/daily/hp-daily-forecast-day1.json"

_STATIONS = [{
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-9.14, 38.72]},
    "properties": {"idEstacao": 1234, "localEstacao": "Lisbon"},
}]

_OBS = {"2026-04-22T12:00": {"1234": {
    "temperatura": 15.0,
    "humidade": 70.0,
    "pressao": 1015.0,
    "intensidadeVento": 5.0,
    "idDireccVento": 9,
    "precAcumulada": 2.0,
}}}

_DAY0 = {"data": [{"globalIdLocal": 1110600, "latitude": "38.72", "longitude": "-9.14",
                   "tMin": "10.0", "tMax": "20.0",
                   "precipitaProb": "30.0", "classWindSpeed": 2,
                   "idWeatherType": 9}]}


def _add_ipma_base(rsps):
    rsps.add(resp.GET, _IPMA_STATIONS_URL, json=_STATIONS)
    rsps.add(resp.GET, _IPMA_OBS_URL, json=_OBS)
    rsps.add(resp.GET, _IPMA_DAY0_URL, json=_DAY0)
    rsps.add(resp.GET, _IPMA_DAY1_URL, status=404)


@resp.activate
def test_ipma_metric_temperature():
    from temporalis.providers.ipma import IPMA
    _add_ipma_base(resp)
    p = IPMA(38.72, -9.14, units="metric")
    assert p.weather.temperature.units == "ºC"
    assert p.weather.temperature.value == 15.0


@resp.activate
def test_ipma_us_temperature_converted():
    from temporalis.providers.ipma import IPMA
    _add_ipma_base(resp)
    p = IPMA(38.72, -9.14, units="us")
    assert p.weather.temperature.units == "ºF"
    assert _approx(p.weather.temperature.value, 59.0)  # 15°C = 59°F


@resp.activate
def test_ipma_metric_wind_speed():
    from temporalis.providers.ipma import IPMA
    _add_ipma_base(resp)
    p = IPMA(38.72, -9.14, units="metric")
    assert p.weather.windSpeed.units == "m/s"
    assert p.weather.windSpeed.value == 5.0


@resp.activate
def test_ipma_us_wind_speed_converted():
    from temporalis.providers.ipma import IPMA
    _add_ipma_base(resp)
    p = IPMA(38.72, -9.14, units="us")
    assert p.weather.windSpeed.units == "mph"
    assert _approx(p.weather.windSpeed.value, 11.2)  # 5 m/s ≈ 11.2 mph


@resp.activate
def test_ipma_metric_precipitation():
    from temporalis.providers.ipma import IPMA
    _add_ipma_base(resp)
    p = IPMA(38.72, -9.14, units="metric")
    assert p.weather.precipitation.units == "mm"
    assert p.weather.precipitation.value == 2.0


@resp.activate
def test_ipma_us_precipitation_converted():
    from temporalis.providers.ipma import IPMA
    _add_ipma_base(resp)
    p = IPMA(38.72, -9.14, units="us")
    assert p.weather.precipitation.units == "inch"
    assert _approx(p.weather.precipitation.value, 0.079, tol=0.01)  # 2mm ≈ 0.079 in


@resp.activate
def test_ipma_daily_metric_temperature():
    from temporalis.providers.ipma import IPMA
    _add_ipma_base(resp)
    p = IPMA(38.72, -9.14, units="metric")
    day = p.days[0]
    assert day.temperature.units == "ºC"
    assert day.temperature.min_val == 10.0
    assert day.temperature.max_val == 20.0


@resp.activate
def test_ipma_daily_us_temperature_converted():
    from temporalis.providers.ipma import IPMA
    _add_ipma_base(resp)
    p = IPMA(38.72, -9.14, units="us")
    day = p.days[0]
    assert day.temperature.units == "ºF"
    assert _approx(day.temperature.min_val, 50.0)  # 10°C = 50°F
    assert _approx(day.temperature.max_val, 68.0)  # 20°C = 68°F


@resp.activate
def test_ipma_daily_us_wind_converted():
    from temporalis.providers.ipma import IPMA
    _add_ipma_base(resp)
    p = IPMA(38.72, -9.14, units="us")
    day = p.days[0]
    assert day.windSpeed.units == "mph"
    # classWindSpeed=2 → 15.0 km/h → ~9.3 mph
    assert _approx(day.windSpeed.value, 9.3)


# ── OWM unit string consistency ───────────────────────────────────────────────

_OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
_OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
_OWM_ONECALL_URL = "https://api.openweathermap.org/data/3.0/onecall"

_OWM_CURRENT = {
    "dt": 1714000000, "timezone": 0,
    "coord": {"lat": 38.72, "lon": -9.14},
    "main": {"temp": 300.15, "feels_like": 299.0, "humidity": 70,
             "pressure": 1015, "temp_min": 298.0, "temp_max": 302.0},
    "wind": {"speed": 5.0, "deg": 270},
    "clouds": {"all": 20},
    "weather": [{"main": "Clear", "description": "clear sky", "icon": "01d"}],
    "visibility": 10000,
}

_OWM_FORECAST_DATA = {
    "list": [{
        "dt": 1714000000,
        "main": {"temp": 300.15, "temp_min": 298.0, "temp_max": 302.0,
                 "feels_like": 299.0, "humidity": 70, "pressure": 1015},
        "weather": [{"main": "Clear", "description": "clear sky"}],
        "wind": {"speed": 5.0, "deg": 270},
        "clouds": {"all": 20},
        "visibility": 10000,
    }],
    "city": {"name": "Lisbon"},
}


@resp.activate
def test_owm_si_kelvin_unit():
    from temporalis.providers.owm import OWM
    resp.add(resp.GET, _OWM_CURRENT_URL, json=_OWM_CURRENT)
    resp.add(resp.GET, _OWM_FORECAST_URL, json=_OWM_FORECAST_DATA)
    resp.add(resp.GET, _OWM_ONECALL_URL, status=401)
    p = OWM(38.72, -9.14, units="si", key="testkey")
    assert p.weather.temperature.units == "K"
    assert p.hours[0].temperature.units == "K"


_OWM_CURRENT_WITH_RAIN = {
    "dt": 1714000000, "timezone": 0,
    "coord": {"lat": 38.72, "lon": -9.14},
    "main": {"temp": 18.0, "feels_like": 17.0, "humidity": 70,
             "pressure": 1015, "temp_min": 16.0, "temp_max": 20.0},
    "wind": {"speed": 10.0, "deg": 270},  # 10 m/s
    "clouds": {"all": 20},
    "weather": [{"main": "Rain", "description": "light rain", "icon": "10d"}],
    "visibility": 10000,
    "rain": {"1h": 2.54},  # 2.54 mm = exactly 0.1 inch
}

_OWM_FORECAST_WITH_RAIN = {
    "list": [{
        "dt": 1714000000,
        "main": {"temp": 18.0, "temp_min": 16.0, "temp_max": 20.0,
                 "feels_like": 17.0, "humidity": 70, "pressure": 1015},
        "weather": [{"main": "Rain", "description": "light rain"}],
        "wind": {"speed": 10.0, "deg": 270},  # 10 m/s
        "clouds": {"all": 20},
        "visibility": 10000,
        "rain": {"3h": 7.62},  # 7.62 mm / 3 = 2.54 mm/h
    }],
    "city": {"name": "Lisbon"},
}


@resp.activate
def test_owm_metric_wind_speed_unit():
    """OWM API always returns m/s; metric mode must keep m/s."""
    from temporalis.providers.owm import OWM
    resp.add(resp.GET, _OWM_CURRENT_URL, json=_OWM_CURRENT_WITH_RAIN)
    resp.add(resp.GET, _OWM_FORECAST_URL, json=_OWM_FORECAST_WITH_RAIN)
    resp.add(resp.GET, _OWM_ONECALL_URL, status=401)
    p = OWM(38.72, -9.14, units="metric", key="testkey")
    assert p.weather.windSpeed.units == "m/s"
    assert p.weather.windSpeed.value == 10.0
    assert p.hours[0].windSpeed.units == "m/s"
    assert p.hours[0].windSpeed.value == 10.0


@resp.activate
def test_owm_imperial_wind_speed_converted():
    """OWM API always returns m/s; imperial mode must convert to mph."""
    from temporalis.providers.owm import OWM
    resp.add(resp.GET, _OWM_CURRENT_URL, json=_OWM_CURRENT_WITH_RAIN)
    resp.add(resp.GET, _OWM_FORECAST_URL, json=_OWM_FORECAST_WITH_RAIN)
    resp.add(resp.GET, _OWM_ONECALL_URL, status=401)
    p = OWM(38.72, -9.14, units="imperial", key="testkey")
    assert p.weather.windSpeed.units == "mph"
    assert _approx(p.weather.windSpeed.value, 22.4)  # 10 m/s ≈ 22.37 mph


@resp.activate
def test_owm_metric_precipitation_unit():
    """OWM API always returns mm; metric mode must keep mm."""
    from temporalis.providers.owm import OWM
    resp.add(resp.GET, _OWM_CURRENT_URL, json=_OWM_CURRENT_WITH_RAIN)
    resp.add(resp.GET, _OWM_FORECAST_URL, json=_OWM_FORECAST_WITH_RAIN)
    resp.add(resp.GET, _OWM_ONECALL_URL, status=401)
    p = OWM(38.72, -9.14, units="metric", key="testkey")
    assert p.weather.precipitation.units == "mm"
    assert p.weather.precipitation.value == 2.54


@resp.activate
def test_owm_imperial_precipitation_converted():
    """OWM API always returns mm; imperial mode must convert to inches."""
    from temporalis.providers.owm import OWM
    resp.add(resp.GET, _OWM_CURRENT_URL, json=_OWM_CURRENT_WITH_RAIN)
    resp.add(resp.GET, _OWM_FORECAST_URL, json=_OWM_FORECAST_WITH_RAIN)
    resp.add(resp.GET, _OWM_ONECALL_URL, status=401)
    p = OWM(38.72, -9.14, units="imperial", key="testkey")
    assert p.weather.precipitation.units == "inch"
    assert _approx(p.weather.precipitation.value, 0.1, tol=0.01)  # 2.54 mm = 0.1 inch


@resp.activate
def test_owm_forecast_precipitation_from_3h():
    """OWM 5-day forecast returns 3h rain totals; code divides by 3 to get 1h rate."""
    from temporalis.providers.owm import OWM
    resp.add(resp.GET, _OWM_CURRENT_URL, json=_OWM_CURRENT_WITH_RAIN)
    resp.add(resp.GET, _OWM_FORECAST_URL, json=_OWM_FORECAST_WITH_RAIN)
    resp.add(resp.GET, _OWM_ONECALL_URL, status=401)
    p = OWM(38.72, -9.14, units="metric", key="testkey")
    # 7.62 mm / 3 = 2.54 mm/h
    assert p.hours[0].precipitation is not None
    assert p.hours[0].precipitation.units == "mm"
    assert _approx(p.hours[0].precipitation.value, 2.54, tol=0.01)


# ── IPMA daily precipitation is a probability, not an amount ─────────────────

@resp.activate
def test_ipma_daily_precip_is_probability_not_amount():
    """IPMA daily only gives precipitation probability; value must be None, prob set."""
    from temporalis.providers.ipma import IPMA
    _add_ipma_base(resp)
    p = IPMA(38.72, -9.14, units="metric")
    day = p.days[0]
    assert day.precipitation is not None
    assert day.precipitation.value is None          # no measured amount
    assert day.precipitation.prob == pytest.approx(0.30, abs=0.01)  # 30% → 0.30
