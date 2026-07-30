import pytest
import responses as resp
from temporalis.providers.ipma import IPMA
from temporalis import WeatherData

_BASE = "https://api.ipma.pt/open-data"

STATIONS = [
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-9.139, 38.720]},
     "properties": {"idEstacao": 1210881, "localEstacao": "Lisboa"}},
    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-7.821, 37.033]},
     "properties": {"idEstacao": 1210882, "localEstacao": "Faro"}},
]

OBS = {
    "2026-04-21T22:00": {
        "1210881": {"temperatura": 15.0, "humidade": 72.0, "pressao": 1012.5,
                    "intensidadeVento": 3.2, "precAcumulada": 0.0, "idDireccVento": 4},
        "1210882": {"temperatura": 18.0, "humidade": 60.0, "pressao": 1015.0,
                    "intensidadeVento": 2.0, "precAcumulada": 0.0, "idDireccVento": 2},
    }
}

DAY0 = {
    "owner": "IPMA", "country": "PT", "forecastDate": "2026-04-21",
    "data": [
        {"precipitaProb": "20.0", "tMin": 12, "tMax": 22, "predWindDir": "N",
         "idWeatherType": 1, "classWindSpeed": 2, "longitude": "-9.1286",
         "globalIdLocal": 1110600, "latitude": "38.7660"},
        {"precipitaProb": "10.0", "tMin": 14, "tMax": 24, "predWindDir": "S",
         "idWeatherType": 2, "classWindSpeed": 1, "longitude": "-7.9000",
         "globalIdLocal": 1020500, "latitude": "37.0200"},
    ]
}


@resp.activate
def test_ipma_weather_returns_weatherdata():
    resp.add(resp.GET, f"{_BASE}/observation/meteorology/stations/stations.json",
             json=STATIONS)
    resp.add(resp.GET, f"{_BASE}/observation/meteorology/stations/observations.json",
             json=OBS)
    resp.add(resp.GET, f"{_BASE}/forecast/meteorology/cities/daily/hp-daily-forecast-day0.json",
             json=DAY0)
    resp.add(resp.GET, f"{_BASE}/forecast/meteorology/cities/daily/hp-daily-forecast-day1.json",
             status=404, body=b"Not Found")
    p = IPMA(38.72, -9.14)
    assert isinstance(p.weather, WeatherData)
    assert p.weather.temperature is not None
    assert p.weather.temperature.value == 15.0


@resp.activate
def test_ipma_days_populated():
    resp.add(resp.GET, f"{_BASE}/observation/meteorology/stations/stations.json",
             json=STATIONS)
    resp.add(resp.GET, f"{_BASE}/observation/meteorology/stations/observations.json",
             json=OBS)
    resp.add(resp.GET, f"{_BASE}/forecast/meteorology/cities/daily/hp-daily-forecast-day0.json",
             json=DAY0)
    resp.add(resp.GET, f"{_BASE}/forecast/meteorology/cities/daily/hp-daily-forecast-day1.json",
             status=404, body=b"Not Found")
    p = IPMA(38.72, -9.14)
    assert len(p.days) >= 1
    assert p.days[0].temperature is not None


def test_ipma_rejects_non_portugal():
    with pytest.raises(ValueError, match="IPMA only covers Portugal"):
        IPMA(51.5, -0.1)


def test_ipma_rejects_non_portugal_azores_edge():
    # Azores are within the generous bounding box — should not raise
    @resp.activate
    def _run():
        resp.add(resp.GET, f"{_BASE}/observation/meteorology/stations/stations.json",
                 json=STATIONS)
        resp.add(resp.GET, f"{_BASE}/observation/meteorology/stations/observations.json",
                 json=OBS)
        resp.add(resp.GET, f"{_BASE}/forecast/meteorology/cities/daily/hp-daily-forecast-day0.json",
                 json=DAY0)
        resp.add(resp.GET, f"{_BASE}/forecast/meteorology/cities/daily/hp-daily-forecast-day1.json",
                 status=404, body=b"Not Found")
        p = IPMA(37.74, -25.67)  # Ponta Delgada, Azores
        assert p is not None

    _run()
