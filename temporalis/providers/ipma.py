import math
import pendulum
from temporalis.providers import WeatherProvider
from temporalis import WeatherData, DataPoint

# Portugal mainland + islands bounding box (generous)
_PT_LAT_MIN, _PT_LAT_MAX = 30.0, 43.0
_PT_LON_MIN, _PT_LON_MAX = -32.0, -6.0

_BASE = "https://api.ipma.pt/open-data"

_WIND_CLASS_SPEED = {1: 5.0, 2: 15.0, 3: 35.0, 4: 55.0, 5: 75.0}

# IPMA idDireccVento codes → degrees (1=N, clockwise in 16 steps of 22.5°)
_WIND_DIR_DEG = {i: (i - 1) * 22.5 for i in range(1, 17)}

_WEATHER_TYPE_ICON = {
    1: "clear", 2: "partly-cloudy", 3: "clouds", 4: "clouds",
    5: "clouds", 6: "fog", 7: "clouds", 8: "clouds", 9: "rain",
    10: "rain", 11: "rain", 12: "rain", 13: "rain", 14: "rain",
    15: "rain", 16: "thunderstorm", 17: "thunderstorm", 18: "thunderstorm",
    19: "snow", 20: "snow", 21: "snow", 22: "snow", 23: "snow",
    24: "rain", 25: "rain", 26: "rain", 27: "rain", 28: "thunderstorm",
    29: "thunderstorm",
}


def _valid(val, sentinel=-50):
    """Return None for IPMA sentinel values (typically -99)."""
    if val is None:
        return None
    try:
        return None if float(val) < sentinel else val
    except (TypeError, ValueError):
        return None


def _nearest(candidates, lat, lon, lat_key, lon_key):
    """Return the item in candidates closest to (lat, lon)."""
    return min(candidates,
               key=lambda x: math.hypot(float(x[lat_key]) - lat,
                                        float(x[lon_key]) - lon))


class IPMA(WeatherProvider):

    def __init__(self, lat, lon, date=None, units="metric", lang="en"):
        if not (_PT_LAT_MIN <= lat <= _PT_LAT_MAX and
                _PT_LON_MIN <= lon <= _PT_LON_MAX):
            raise ValueError(
                f"IPMA only covers Portugal. Coordinates ({lat}, {lon}) are outside the supported region."
            )
        super().__init__(lat, lon, date, units, lang)
        self._request()

    @staticmethod
    def from_address(address, **kwargs):
        from temporalis.location import geolocate
        lat, lon = geolocate(address)
        return IPMA(lat, lon, **kwargs)

    def _request_current(self):
        stations_url = f"{_BASE}/observation/meteorology/stations/stations.json"
        obs_url = f"{_BASE}/observation/meteorology/stations/observations.json"

        stations_raw = self.session.get(stations_url).json()
        obs_raw = self.session.get(obs_url).json()

        # Observations: {timestamp: {stationId: {fields}}}
        latest_ts = max(obs_raw.keys())
        obs_at_ts = obs_raw[latest_ts]

        # Stations: GeoJSON features, coordinates=[lon, lat]
        station_lookup = {}
        for feat in stations_raw:
            sid = str(feat["properties"]["idEstacao"])
            coords = feat["geometry"]["coordinates"]
            station_lookup[sid] = {"lon": coords[0], "lat": coords[1]}

        # Find nearest station that has observation data
        candidates = [
            {"id": sid, "lat": station_lookup[sid]["lat"], "lon": station_lookup[sid]["lon"]}
            for sid in obs_at_ts
            if sid in station_lookup
        ]
        if not candidates:
            self.data["currently"] = {}
            return

        nearest = _nearest(candidates, self.latitude, self.longitude, "lat", "lon")
        obs = obs_at_ts[nearest["id"]]

        temp = _valid(obs.get("temperatura"))
        humidity = _valid(obs.get("humidade"))
        pressure = _valid(obs.get("pressao"))
        wind_speed = _valid(obs.get("intensidadeVento"))
        wind_dir = _WIND_DIR_DEG.get(obs.get("idDireccVento"))
        precip = _valid(obs.get("precAcumulada"))

        unit = "ºF" if self._units == "us" else "ºC"
        speed_unit = "mph" if self._units == "us" else "m/s"

        temperature = DataPoint("Temperature", temp, unit) if temp is not None else None
        hum = DataPoint("Humidity", humidity, "%") if humidity is not None else None
        pres = DataPoint("Pressure", pressure, "hPa") if pressure is not None else None
        wspeed = DataPoint("WindSpeed", wind_speed, speed_unit) if wind_speed is not None else None
        wbearing = DataPoint("WindBearing", wind_dir, "°") if wind_dir is not None else None
        prec = DataPoint("Precipitation", precip, "mm") if precip is not None else None

        dt = pendulum.parse(latest_ts, tz=self.timezone)

        w = {
            "datetime": dt,
            "temperature": temperature,
            "apparentTemperature": temperature,
            "humidity": hum,
            "pressure": pres,
            "windSpeed": wspeed,
            "windBearing": wbearing,
            "precipitation": prec,
            "summary": "observation",
            "icon": "observation",
        }
        self.data["currently"] = w
        self.data["hourly"] = {"summary": "observation", "icon": "observation", "data": [WeatherData.from_dict(w)]}

    def _request_daily(self):
        unit = "ºF" if self._units == "us" else "ºC"
        speed_unit = "mph" if self._units == "us" else "km/h"

        days = []
        for day_idx in range(10):
            url = f"{_BASE}/forecast/meteorology/cities/daily/hp-daily-forecast-day{day_idx}.json"
            resp = self.session.get(url)
            if not resp.ok:
                break
            raw = resp.json()
            data_pts = raw.get("data", [])
            if not data_pts:
                continue

            nearest = _nearest(data_pts, self.latitude, self.longitude, "latitude", "longitude")

            t_min = _valid(nearest.get("tMin"))
            t_max = _valid(nearest.get("tMax"))
            precip_prob = nearest.get("precipitaProb")
            if precip_prob is not None:
                try:
                    precip_prob = float(precip_prob)
                except (TypeError, ValueError):
                    precip_prob = None
            wind_class = nearest.get("classWindSpeed")
            wind_speed_val = _WIND_CLASS_SPEED.get(wind_class)
            weather_type = nearest.get("idWeatherType")
            icon = _WEATHER_TYPE_ICON.get(weather_type, "clouds")

            temperature = None
            if t_min is not None and t_max is not None:
                avg = (float(t_min) + float(t_max)) / 2
                temperature = DataPoint("Temperature", avg, unit,
                                        min_val=float(t_min), max_val=float(t_max))
            elif t_max is not None:
                temperature = DataPoint("Temperature", float(t_max), unit)

            wspeed = DataPoint("WindSpeed", wind_speed_val, speed_unit) if wind_speed_val else None
            prec = DataPoint("Precipitation", precip_prob, "%",
                             prob=precip_prob / 100 if precip_prob is not None else None) if precip_prob is not None else None

            dt = pendulum.now(self.timezone).add(days=day_idx).start_of("day")

            w = {
                "datetime": dt,
                "temperature": temperature,
                "apparentTemperature": temperature,
                "windSpeed": wspeed,
                "precipitation": prec,
                "summary": icon,
                "icon": icon,
            }
            days.append(WeatherData.from_dict(w))

        if days:
            summary = days[0].summary or "forecast"
            icon = days[0].icon or "forecast"
            self.data["daily"] = {"summary": summary, "icon": icon, "data": days}
        else:
            self.data["daily"] = {"summary": "forecast", "icon": "forecast", "data": []}

    def _fetch_alerts(self):
        url = f"{_BASE}/forecast/warnings/warnings_www.json"
        try:
            warnings = self.session.get(url).json()
            for w in warnings:
                self._alerts.append({
                    "event": w.get("awarenessTypeName", ""),
                    "severity": w.get("awarenessLevelID", ""),
                    "headline": w.get("text", ""),
                    "description": w.get("text", ""),
                    "onset": w.get("startTime"),
                    "expires": w.get("endTime"),
                })
        except Exception:
            pass

    def _request(self):
        self._request_current()
        self._request_daily()
        self._fetch_alerts()
