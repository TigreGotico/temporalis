import pendulum
from temporalis.providers import WeatherProvider
from temporalis import WeatherData, DataPoint

_API_URL = "https://api.met.no/weatherapi/locationforecast/2.0/complete"
_USER_AGENT = "temporalis/0.2.0 github.com/OpenJarbas/temporalis"

# Met.no symbol_code → simple icon string
_SYMBOL_ICON = {
    "clearsky": "clear",
    "fair": "mostly-clear",
    "partlycloudy": "partly-cloudy",
    "cloudy": "clouds",
    "fog": "fog",
    "lightrain": "rain", "rain": "rain", "heavyrain": "heavy-rain",
    "lightrainshowers": "showers", "rainshowers": "showers", "heavyrainshowers": "heavy-showers",
    "lightsleet": "sleet", "sleet": "sleet", "heavysleet": "sleet",
    "lightsleetshowers": "sleet", "sleetshowers": "sleet", "heavysleetshowers": "sleet",
    "lightsnow": "snow", "snow": "snow", "heavysnow": "heavy-snow",
    "lightsnowshowers": "snow-showers", "snowshowers": "snow-showers", "heavysnowshowers": "snow-showers",
    "lightrainandthunder": "thunderstorm", "rainandthunder": "thunderstorm",
    "heavyrainandthunder": "thunderstorm",
    "lightrainshowersandthunder": "thunderstorm", "rainshowersandthunder": "thunderstorm",
    "heavyrainshowersandthunder": "thunderstorm",
    "lightsnowandthunder": "thunderstorm", "snowandthunder": "thunderstorm",
    "lightsleetandthunder": "thunderstorm", "sleetandthunder": "thunderstorm",
}

_WIND_DIRS = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]


def _symbol_to_icon(symbol_code):
    base = symbol_code.split("_")[0] if symbol_code else ""
    return _SYMBOL_ICON.get(base, "clouds")


def _wind_deg_to_dir(deg):
    if deg is None:
        return None
    return _WIND_DIRS[round(deg / 22.5) % 16]


class MetNo(WeatherProvider):
    """Norwegian Meteorological Institute forecast — global coverage, no API key."""

    def __init__(self, lat, lon, date=None, units="metric", lang="en"):
        super().__init__(lat, lon, date, units, lang)
        self._request()

    @staticmethod
    def from_address(address, **kwargs):
        from temporalis.location import geolocate
        lat, lon = geolocate(address)
        return MetNo(lat, lon, **kwargs)

    def _temp_unit(self):
        return "ºF" if self._units in ("us", "imperial") else "ºC"

    def _speed_unit(self):
        return "mph" if self._units in ("us", "imperial") else "m/s"

    def _precip_unit(self):
        return "inch" if self._units in ("us", "imperial") else "mm"

    def _convert_precip(self, mm):
        if mm is None:
            return None
        if self._units in ("us", "imperial"):
            return round(mm / 25.4, 3)
        return mm

    def _convert_temp(self, celsius):
        if celsius is None:
            return None
        if self._units in ("us", "imperial"):
            return round(celsius * 9 / 5 + 32, 1)
        return celsius

    def _convert_speed(self, ms):
        if ms is None:
            return None
        if self._units in ("us", "imperial"):
            return round(ms * 2.237, 1)
        return ms

    def _request(self):
        headers = {"User-Agent": _USER_AGENT}
        params = {"lat": self.latitude, "lon": self.longitude}
        raw = self._get_json(_API_URL, params=params, headers=headers)
        timeseries = raw.get("properties", {}).get("timeseries", [])
        if not timeseries:
            return

        tz = self.timezone or "UTC"
        t_unit = self._temp_unit()
        s_unit = self._speed_unit()
        p_unit = self._precip_unit()

        hours = []
        days = {}

        for entry in timeseries:
            time_str = entry["time"]
            dt = pendulum.parse(time_str, tz=tz)
            inst = entry["data"].get("instant", {}).get("details", {})
            n1h = entry["data"].get("next_1_hours", {})
            n6h = entry["data"].get("next_6_hours", {})

            # prefer 1h block for symbol, fall back to 6h
            block = n1h or n6h
            symbol = block.get("summary", {}).get("symbol_code", "")
            icon = _symbol_to_icon(symbol)
            precip = self._convert_precip((block.get("details", {}) or {}).get("precipitation_amount"))

            temp_c = inst.get("air_temperature")
            temp = self._convert_temp(temp_c)
            dew_c = inst.get("dew_point_temperature")
            dew = self._convert_temp(dew_c)
            humidity = inst.get("relative_humidity")
            cloud = inst.get("cloud_area_fraction")
            pressure = inst.get("air_pressure_at_sea_level")
            wind_speed_ms = inst.get("wind_speed")
            wind_speed = self._convert_speed(wind_speed_ms)
            wind_dir_deg = inst.get("wind_from_direction")
            uv = inst.get("ultraviolet_index_clear_sky")

            w = {
                "datetime": dt,
                "temperature": DataPoint("Temperature", temp, t_unit) if temp is not None else None,
                "apparentTemperature": DataPoint("ApparentTemperature", temp, t_unit) if temp is not None else None,
                "humidity": DataPoint("Humidity", humidity, "%") if humidity is not None else None,
                "dewPoint": DataPoint("DewPoint", dew, t_unit) if dew is not None else None,
                "cloudCover": DataPoint("CloudCover", cloud, "%") if cloud is not None else None,
                "pressure": DataPoint("Pressure", pressure, "hPa") if pressure is not None else None,
                "windSpeed": DataPoint("WindSpeed", wind_speed, s_unit) if wind_speed is not None else None,
                "windBearing": DataPoint("WindBearing", wind_dir_deg, "°") if wind_dir_deg is not None else None,
                "precipitation": DataPoint("Precipitation", precip, p_unit) if precip is not None else None,
                "uvIndex": DataPoint("UVIndex", uv, "") if uv is not None else None,
                "summary": icon,
                "icon": icon,
            }
            wd = WeatherData.from_dict(w)
            hours.append(wd)

            day_key = dt.date()
            if day_key not in days:
                days[day_key] = []
            days[day_key].append(wd)

        # Current = first entry
        first = hours[0] if hours else WeatherData()
        self.data["currently"] = {
            "datetime": first.datetime,
            "temperature": first.temperature,
            "apparentTemperature": first.apparentTemperature,
            "humidity": first.humidity,
            "dewPoint": first.dewPoint,
            "cloudCover": first.cloudCover,
            "pressure": first.pressure,
            "windSpeed": first.windSpeed,
            "windBearing": first.windBearing,
            "precipitation": first.precipitation,
            "uvIndex": first.uvIndex,
            "summary": first.summary,
            "icon": first.icon,
        }

        first_icon = first.icon or "clouds"
        self.data["hourly"] = {"summary": first_icon, "icon": first_icon, "data": hours}

        # Build daily summaries from the first entry per day
        day_list = []
        for day_key in sorted(days):
            day_hours = days[day_key]
            temps = [h.temperature.value for h in day_hours if h.temperature is not None]
            t_min = min(temps) if temps else None
            t_max = max(temps) if temps else None
            avg = (t_min + t_max) / 2 if (t_min is not None and t_max is not None) else None
            rep = day_hours[0]
            dw = {
                "datetime": pendulum.instance(rep.datetime).start_of("day"),
                "temperature": DataPoint("Temperature", avg, t_unit,
                                          min_val=t_min, max_val=t_max) if avg is not None else None,
                "summary": rep.summary,
                "icon": rep.icon,
            }
            day_list.append(WeatherData.from_dict(dw))

        first_day_icon = day_list[0].icon if day_list else "clouds"
        self.data["daily"] = {"summary": first_day_icon, "icon": first_day_icon, "data": day_list}
