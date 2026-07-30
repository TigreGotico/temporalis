#!/usr/bin/env python3
"""Hit real APIs once and save responses to test/fixtures/.

Run from the repo root:
    python test/record_fixtures.py

Requires network access.  Safe to run repeatedly — overwrites existing fixtures.
The resulting JSON files are committed and used by test_e2e.py without network access.
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
import requests

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_DIR.mkdir(exist_ok=True)

# Lisbon, Portugal — chosen because it's covered by all providers
LAT, LON = 38.7169, -9.1399

OWM_KEY = os.environ.get("OWM_KEY", "28fed22898afd4717ce5a1535da1f78c")


def save(name: str, data: dict):
    path = FIXTURES_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  saved {path.name}")


def record_owm():
    print("OWM...")
    s = requests.Session()
    current = s.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"lat": LAT, "lon": LON, "appid": OWM_KEY, "units": "metric"},
        timeout=10,
    ).json()
    save("owm_current_metric", current)

    forecast = s.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={"lat": LAT, "lon": LON, "appid": OWM_KEY, "units": "metric"},
        timeout=10,
    ).json()
    save("owm_forecast_metric", forecast)

    current_us = s.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params={"lat": LAT, "lon": LON, "appid": OWM_KEY, "units": "imperial"},
        timeout=10,
    ).json()
    save("owm_current_imperial", current_us)

    forecast_us = s.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        params={"lat": LAT, "lon": LON, "appid": OWM_KEY, "units": "imperial"},
        timeout=10,
    ).json()
    save("owm_forecast_imperial", forecast_us)


def record_openmeteo():
    print("OpenMeteo...")
    s = requests.Session()
    params = {
        "latitude": LAT, "longitude": LON,
        "hourly": "temperature_2m,relativehumidity_2m,precipitation_probability,precipitation,windspeed_10m,winddirection_10m,cloudcover,dewpoint_2m,apparent_temperature,surface_pressure,visibility,is_day",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,windspeed_10m_max,winddirection_10m_dominant,weathercode,uv_index_max",
        "temperature_unit": "celsius",
        "windspeed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto",
        "forecast_days": 3,
        "current_weather": "true",
    }
    data = s.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10).json()
    save("openmeteo_forecast_metric", data)


def record_metno():
    print("MetNo...")
    s = requests.Session()
    s.headers["User-Agent"] = "temporalis-test/1.0 (openvoiceos@gmail.com)"
    data = s.get(
        "https://api.met.no/weatherapi/locationforecast/2.0/complete",
        params={"lat": LAT, "lon": LON},
        timeout=15,
    ).json()
    save("metno_forecast", data)


def record_ipma():
    print("IPMA...")
    s = requests.Session()

    stations = s.get(
        "https://api.ipma.pt/open-data/observation/meteorology/stations/stations.json",
        timeout=10,
    ).json()
    save("ipma_stations", stations)

    obs = s.get(
        "https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json",
        timeout=10,
    ).json()
    save("ipma_observations", obs)

    days = {}
    for i in range(3):
        r = s.get(
            f"https://api.ipma.pt/open-data/forecast/meteorology/cities/daily/hp-daily-forecast-day{i}.json",
            timeout=10,
        )
        if r.ok:
            days[i] = r.json()
    save("ipma_daily_forecast", days)

    warnings = s.get(
        "https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json",
        timeout=10,
    ).json()
    save("ipma_warnings", warnings)


def record_nws():
    print("NWS (Washington DC)...")
    # NWS only covers the US; use Washington DC
    us_lat, us_lon = 38.8951, -77.0364
    s = requests.Session()
    s.headers["User-Agent"] = "temporalis-test/1.0 (openvoiceos@gmail.com)"

    points = s.get(
        f"https://api.weather.gov/points/{us_lat},{us_lon}",
        timeout=10,
    ).json()
    save("nws_points", points)

    props = points.get("properties", {})
    forecast_url = props.get("forecast")
    hourly_url = props.get("forecastHourly")
    obs_stations_url = props.get("observationStations")

    if forecast_url:
        save("nws_forecast", s.get(forecast_url, timeout=10).json())
    if hourly_url:
        save("nws_hourly", s.get(hourly_url, timeout=10).json())
    if obs_stations_url:
        stations = s.get(obs_stations_url, timeout=10).json()
        save("nws_obs_stations", stations)
        features = stations.get("features", [])
        if features:
            station_id = features[0]["properties"]["stationIdentifier"]
            obs = s.get(
                f"https://api.weather.gov/stations/{station_id}/observations/latest",
                timeout=10,
            ).json()
            save("nws_latest_obs", obs)


if __name__ == "__main__":
    providers = sys.argv[1:] or ["owm", "openmeteo", "metno", "ipma", "nws"]
    for p in providers:
        try:
            globals()[f"record_{p}"]()
        except Exception as e:
            print(f"  ERROR recording {p}: {e}")
    print("Done.")
