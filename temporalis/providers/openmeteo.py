import pendulum
from temporalis.providers import WeatherProvider
from temporalis import WeatherData, DataPoint

_API_URL = "https://api.open-meteo.com/v1/forecast"

_WMO_ICON = {
    0: "clear",
    1: "mostly-clear", 2: "partly-cloudy", 3: "clouds",
    45: "fog", 48: "fog",
    51: "drizzle", 53: "drizzle", 55: "drizzle",
    56: "freezing-drizzle", 57: "freezing-drizzle",
    61: "rain", 63: "rain", 65: "heavy-rain",
    66: "freezing-rain", 67: "freezing-rain",
    71: "snow", 73: "snow", 75: "heavy-snow",
    77: "snow-grains",
    80: "showers", 81: "showers", 82: "heavy-showers",
    85: "snow-showers", 86: "snow-showers",
    95: "thunderstorm",
    96: "thunderstorm-hail", 99: "thunderstorm-hail",
}

_HOURLY_PARAMS = [
    "temperature_2m", "apparent_temperature", "relativehumidity_2m",
    "dewpoint_2m", "cloudcover", "pressure_msl", "windspeed_10m",
    "winddirection_10m", "windgusts_10m", "precipitation",
    "snowfall", "visibility", "weathercode", "precipitation_probability",
    "is_day",
]

_DAILY_PARAMS = [
    "temperature_2m_max", "temperature_2m_min",
    "apparent_temperature_max", "apparent_temperature_min",
    "precipitation_sum", "precipitation_hours",
    "precipitation_probability_max", "precipitation_probability_min",
    "precipitation_probability_mean",
    "weathercode", "windspeed_10m_max", "windgusts_10m_max",
    "winddirection_10m_dominant", "uv_index_max", "sunrise", "sunset",
]


class OpenMeteo(WeatherProvider):

    def __init__(self, lat, lon, date=None, units="metric", lang="en"):
        super().__init__(lat, lon, date, units, lang)
        self._request()

    @staticmethod
    def from_address(address, **kwargs):
        from temporalis.location import geolocate
        lat, lon = geolocate(address)
        return OpenMeteo(lat, lon, **kwargs)

    def _unit_params(self):
        if self._units in ("us", "imperial"):
            return {"temperature_unit": "fahrenheit",
                    "windspeed_unit": "mph",
                    "precipitation_unit": "inch"}
        return {"temperature_unit": "celsius",
                "windspeed_unit": "kmh",
                "precipitation_unit": "mm"}

    def _temp_unit(self):
        return "ºF" if self._units in ("us", "imperial") else "ºC"

    def _speed_unit(self):
        return "mph" if self._units in ("us", "imperial") else "km/h"

    def _precip_unit(self):
        return "inch" if self._units in ("us", "imperial") else "mm"

    def _request(self):
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly": ",".join(_HOURLY_PARAMS),
            "daily": ",".join(_DAILY_PARAMS),
            "current_weather": "true",
            "timezone": self.timezone or "UTC",
            **self._unit_params(),
        }
        raw = self.session.get(_API_URL, params=params).json()

        self._parse_current(raw.get("current_weather", {}))
        self._parse_hourly(raw.get("hourly", {}))
        self._parse_daily(raw.get("daily", {}))

    def _parse_current(self, cw):
        temp = cw.get("temperature")
        wind_speed = cw.get("windspeed")
        wind_dir = cw.get("winddirection")
        code = cw.get("weathercode", 0)
        icon = _WMO_ICON.get(code, "clouds")
        time_str = cw.get("time")

        t_unit = self._temp_unit()
        s_unit = self._speed_unit()

        temperature = DataPoint("Temperature", temp, t_unit) if temp is not None else None
        wspeed = DataPoint("WindSpeed", wind_speed, s_unit) if wind_speed is not None else None
        wbearing = DataPoint("WindBearing", wind_dir, "°") if wind_dir is not None else None

        dt = pendulum.parse(time_str, tz=self.timezone) if time_str else self.datetime

        w = {
            "datetime": dt,
            "temperature": temperature,
            "apparentTemperature": temperature,
            "windSpeed": wspeed,
            "windBearing": wbearing,
            "summary": icon,
            "icon": icon,
        }
        self.data["currently"] = w

    def _parse_hourly(self, hourly):
        times = hourly.get("time", [])
        if not times:
            self.data["hourly"] = {"summary": "", "icon": "", "data": []}
            return

        t_unit = self._temp_unit()
        s_unit = self._speed_unit()
        p_unit = self._precip_unit()
        tz = self.timezone or "UTC"

        hours = []
        for i, time_str in enumerate(times):
            def _get(key):
                arr = hourly.get(key, [])
                return arr[i] if i < len(arr) else None

            temp = _get("temperature_2m")
            ap_temp = _get("apparent_temperature")
            humidity = _get("relativehumidity_2m")
            dewpoint = _get("dewpoint_2m")
            cloud = _get("cloudcover")
            pressure = _get("pressure_msl")
            wspeed = _get("windspeed_10m")
            wdir = _get("winddirection_10m")
            wgust = _get("windgusts_10m")
            precip = _get("precipitation")
            snow = _get("snowfall")
            vis = _get("visibility")
            code = _get("weathercode") or 0
            precip_prob = _get("precipitation_probability")
            icon = _WMO_ICON.get(code, "clouds")

            w = {
                "datetime": pendulum.parse(time_str, tz=tz),
                "temperature": DataPoint("Temperature", temp, t_unit) if temp is not None else None,
                "apparentTemperature": DataPoint("ApparentTemperature", ap_temp, t_unit) if ap_temp is not None else None,
                "humidity": DataPoint("Humidity", humidity, "%") if humidity is not None else None,
                "dewPoint": DataPoint("DewPoint", dewpoint, t_unit) if dewpoint is not None else None,
                "cloudCover": DataPoint("CloudCover", cloud, "%") if cloud is not None else None,
                "pressure": DataPoint("Pressure", pressure, "hPa") if pressure is not None else None,
                "windSpeed": DataPoint("WindSpeed", wspeed, s_unit) if wspeed is not None else None,
                "windBearing": DataPoint("WindBearing", wdir, "°") if wdir is not None else None,
                "windGust": DataPoint("WindGust", wgust, s_unit) if wgust is not None else None,
                "precipitation": DataPoint("Precipitation", precip, p_unit,
                                           prob=precip_prob / 100 if precip_prob is not None else None) if precip is not None else None,
                "snow": DataPoint("Snow", snow, p_unit) if snow is not None else None,
                "visibility": DataPoint("Visibility", vis, "m") if vis is not None else None,
                "summary": icon,
                "icon": icon,
            }
            hours.append(WeatherData.from_dict(w))

        first_icon = hours[0].icon if hours else ""
        self.data["hourly"] = {"summary": first_icon, "icon": first_icon, "data": hours}

    def _parse_daily(self, daily):
        times = daily.get("time", [])
        if not times:
            self.data["daily"] = {"summary": "", "icon": "", "data": []}
            return

        t_unit = self._temp_unit()
        s_unit = self._speed_unit()
        p_unit = self._precip_unit()
        tz = self.timezone or "UTC"

        days = []
        for i, time_str in enumerate(times):
            def _get(key):
                arr = daily.get(key, [])
                return arr[i] if i < len(arr) else None

            t_max = _get("temperature_2m_max")
            t_min = _get("temperature_2m_min")
            ap_max = _get("apparent_temperature_max")
            ap_min = _get("apparent_temperature_min")
            precip_sum = _get("precipitation_sum")
            precip_prob = _get("precipitation_probability_max")
            precip_prob_min = _get("precipitation_probability_min")
            precip_prob_mean = _get("precipitation_probability_mean")
            code = _get("weathercode") or 0
            wspeed_max = _get("windspeed_10m_max")
            wgust_max = _get("windgusts_10m_max")
            wdir = _get("winddirection_10m_dominant")
            uv = _get("uv_index_max")
            icon = _WMO_ICON.get(code, "clouds")

            avg_temp = None
            if t_max is not None and t_min is not None:
                avg_temp = (t_max + t_min) / 2

            w = {
                "datetime": pendulum.parse(time_str, tz=tz),
                "temperature": DataPoint("Temperature", avg_temp, t_unit,
                                         min_val=t_min, max_val=t_max) if avg_temp is not None else None,
                "apparentTemperature": DataPoint("ApparentTemperature",
                                                  (ap_max + ap_min) / 2 if (ap_max is not None and ap_min is not None) else ap_max,
                                                  t_unit, min_val=ap_min, max_val=ap_max) if (ap_max is not None) else None,
                "precipitation": DataPoint("Precipitation", precip_sum, p_unit,
                                           prob=precip_prob_mean / 100 if precip_prob_mean is not None else None,
                                           prob_min=precip_prob_min / 100 if precip_prob_min is not None else None,
                                           prob_max=precip_prob / 100 if precip_prob is not None else None) if precip_sum is not None else None,
                "windSpeed": DataPoint("WindSpeed", wspeed_max, s_unit) if wspeed_max is not None else None,
                "windGust": DataPoint("WindGust", wgust_max, s_unit) if wgust_max is not None else None,
                "windBearing": DataPoint("WindBearing", wdir, "°") if wdir is not None else None,
                "uvIndex": DataPoint("UVIndex", uv, "") if uv is not None else None,
                "summary": icon,
                "icon": icon,
            }
            days.append(WeatherData.from_dict(w))

        first_icon = days[0].icon if days else ""
        self.data["daily"] = {"summary": first_icon, "icon": first_icon, "data": days}
