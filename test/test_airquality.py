import responses as resp
from temporalis.providers.openmeteo_airquality import OpenMeteoAirQuality, AirQualityData

_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

_RESPONSE = {
    "latitude": 38.72, "longitude": -9.14, "timezone": "Europe/Lisbon",
    "hourly": {
        "time": ["2026-04-22T00:00", "2026-04-22T01:00", "2026-04-22T02:00"],
        "pm10": [15.8, 16.2, 14.9],
        "pm2_5": [5.7, 6.1, 5.4],
        "ozone": [68.0, 70.0, 66.0],
        "nitrogen_dioxide": [12.3, 11.8, 13.0],
        "sulphur_dioxide": [1.2, 1.1, 1.3],
        "carbon_monoxide": [180.0, 175.0, 185.0],
        "european_aqi": [37, 38, 36],
        "us_aqi": [25, 26, 24],
        "uv_index": [0.0, 0.0, 0.0],
        "dust": [5.0, 4.8, 5.2],
        "ammonia": [None, None, None],
    }
}


@resp.activate
def test_aq_current():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    aq = OpenMeteoAirQuality(38.72, -9.14)
    assert isinstance(aq.current, AirQualityData)
    assert aq.current.pm2_5 is not None
    assert aq.current.pm2_5.value == 5.7
    assert aq.current.european_aqi.value == 37
    assert aq.current.summary == "fair"


@resp.activate
def test_aq_hours():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    aq = OpenMeteoAirQuality(38.72, -9.14)
    assert len(aq.air_quality_hours) == 3
    assert aq.air_quality_hours[1].pm10.value == 16.2


@resp.activate
def test_aq_sun_moon():
    resp.add(resp.GET, _URL, json=_RESPONSE)
    aq = OpenMeteoAirQuality(38.72, -9.14)
    assert aq.dawn is not None
    assert aq.moon_phase_name is not None
