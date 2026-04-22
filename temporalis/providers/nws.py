import re
import pendulum
from temporalis.providers import WeatherProvider
from temporalis import WeatherData, DataPoint

_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"
_USER_AGENT = "temporalis/0.2.0 github.com/OpenJarbas/temporalis"

# NWS US bounding box (contiguous + AK + HI approximate)
_US_LAT_MIN, _US_LAT_MAX = 15.0, 72.0
_US_LON_MIN, _US_LON_MAX = -180.0, -60.0

_WIND_DIR_DEG = {
    "N": 0, "NNE": 22, "NE": 45, "ENE": 67, "E": 90,
    "ESE": 112, "SE": 135, "SSE": 157, "S": 180,
    "SSW": 202, "SW": 225, "WSW": 247, "W": 270,
    "WNW": 292, "NW": 315, "NNW": 337,
}


def _parse_wind_speed(s):
    """Parse '14 mph' or '10 to 15 mph' → average float in mph."""
    if not s:
        return None
    nums = re.findall(r"[\d.]+", s)
    if not nums:
        return None
    vals = [float(n) for n in nums]
    return sum(vals) / len(vals)


def _mph_to_ms(mph):
    return round(mph * 0.44704, 2) if mph is not None else None


def _f_to_c(f):
    return round((f - 32) * 5 / 9, 1) if f is not None else None


class NWS(WeatherProvider):
    """NOAA National Weather Service — USA only, no API key."""

    def __init__(self, lat, lon, date=None, units="metric", lang="en"):
        if not (_US_LAT_MIN <= lat <= _US_LAT_MAX and
                _US_LON_MIN <= lon <= _US_LON_MAX):
            raise ValueError(
                f"NWS only covers the United States. Coordinates ({lat}, {lon}) are outside the supported region."
            )
        super().__init__(lat, lon, date, units, lang)
        self._request()

    @staticmethod
    def from_address(address, **kwargs):
        from temporalis.location import geolocate
        lat, lon = geolocate(address)
        return NWS(lat, lon, **kwargs)

    def _temp_unit(self):
        return "ºF" if self._units in ("us", "imperial") else "ºC"

    def _speed_unit(self):
        return "mph" if self._units in ("us", "imperial") else "m/s"

    def _convert_temp(self, fahrenheit):
        if fahrenheit is None:
            return None
        if self._units not in ("us", "imperial"):
            return _f_to_c(fahrenheit)
        return fahrenheit

    def _convert_speed_mph(self, mph):
        if mph is None:
            return None
        if self._units not in ("us", "imperial"):
            return _mph_to_ms(mph)
        return mph

    def _headers(self):
        return {"User-Agent": _USER_AGENT, "Accept": "application/geo+json"}

    def _request(self):
        # Step 1: resolve grid from lat/lon
        points_url = _POINTS_URL.format(lat=round(self.latitude, 4),
                                        lon=round(self.longitude, 4))
        points = self.session.get(points_url, headers=self._headers()).json()
        props = points.get("properties", {})
        forecast_url = props.get("forecast")
        hourly_url = props.get("forecastHourly")
        tz = props.get("timeZone") or self.timezone

        if not forecast_url or not hourly_url:
            return

        self._parse_hourly(self.session.get(hourly_url, headers=self._headers()).json(), tz)
        self._parse_daily(self.session.get(forecast_url, headers=self._headers()).json(), tz)

    def _parse_hourly(self, raw, tz):
        periods = raw.get("properties", {}).get("periods", [])
        if not periods:
            self.data["hourly"] = {"summary": "", "icon": "", "data": []}
            return

        t_unit = self._temp_unit()
        s_unit = self._speed_unit()
        hours = []

        for p in periods:
            dt = pendulum.parse(p["startTime"], tz=tz)
            temp_f = p.get("temperature")
            temp = self._convert_temp(temp_f)
            humidity = (p.get("relativeHumidity") or {}).get("value")
            dew_raw = p.get("dewpoint", {})
            dew_c = dew_raw.get("value") if isinstance(dew_raw, dict) else None
            dew = self._convert_temp(_f_to_c(dew_c * 9 / 5 + 32) if dew_c is not None else None) if dew_c is not None else None
            precip_prob = (p.get("probabilityOfPrecipitation") or {}).get("value")
            wind_mph = _parse_wind_speed(p.get("windSpeed", ""))
            wind_speed = self._convert_speed_mph(wind_mph)
            wind_dir_str = p.get("windDirection", "")
            wind_deg = _WIND_DIR_DEG.get(wind_dir_str)
            summary = p.get("shortForecast", "")
            icon = self._nws_icon(summary)

            w = {
                "datetime": dt,
                "temperature": DataPoint("Temperature", temp, t_unit) if temp is not None else None,
                "apparentTemperature": DataPoint("ApparentTemperature", temp, t_unit) if temp is not None else None,
                "humidity": DataPoint("Humidity", humidity, "%") if humidity is not None else None,
                "dewPoint": DataPoint("DewPoint", dew_c, "ºC") if dew_c is not None else None,
                "windSpeed": DataPoint("WindSpeed", wind_speed, s_unit) if wind_speed is not None else None,
                "windBearing": DataPoint("WindBearing", wind_deg, "°") if wind_deg is not None else None,
                "precipitation": DataPoint("Precipitation", 0.0, "mm",
                                           prob=precip_prob / 100 if precip_prob is not None else None) if precip_prob is not None else None,
                "summary": summary,
                "icon": icon,
            }
            hours.append(WeatherData.from_dict(w))

        first = hours[0]
        self.data["currently"] = {
            "datetime": first.datetime,
            "temperature": first.temperature,
            "apparentTemperature": first.apparentTemperature,
            "humidity": first.humidity,
            "dewPoint": first.dewPoint,
            "windSpeed": first.windSpeed,
            "windBearing": first.windBearing,
            "precipitation": first.precipitation,
            "summary": first.summary,
            "icon": first.icon,
        }
        first_icon = first.icon or "clouds"
        self.data["hourly"] = {"summary": first_icon, "icon": first_icon, "data": hours}

    def _parse_daily(self, raw, tz):
        periods = raw.get("properties", {}).get("periods", [])
        if not periods:
            self.data["daily"] = {"summary": "", "icon": "", "data": []}
            return

        t_unit = self._temp_unit()
        s_unit = self._speed_unit()

        # NWS gives day/night pairs — group by date
        days_map = {}
        for p in periods:
            dt = pendulum.parse(p["startTime"], tz=tz)
            day_key = dt.date()
            if day_key not in days_map:
                days_map[day_key] = {"day": None, "night": None, "dt": dt}
            if p.get("isDaytime"):
                days_map[day_key]["day"] = p
            else:
                days_map[day_key]["night"] = p

        day_list = []
        for day_key in sorted(days_map):
            entry = days_map[day_key]
            day_p = entry["day"] or entry["night"]
            night_p = entry["night"]

            temp_f = day_p.get("temperature") if day_p else None
            t_max = self._convert_temp(temp_f)
            t_min = self._convert_temp(night_p.get("temperature")) if night_p else t_max
            avg = (t_max + t_min) / 2 if (t_max is not None and t_min is not None) else t_max

            wind_mph = _parse_wind_speed((day_p or {}).get("windSpeed", ""))
            wind_speed = self._convert_speed_mph(wind_mph)
            wind_dir_str = (day_p or {}).get("windDirection", "")
            wind_deg = _WIND_DIR_DEG.get(wind_dir_str)
            summary = (day_p or {}).get("shortForecast", "")
            icon = self._nws_icon(summary)

            dw = {
                "datetime": pendulum.instance(entry["dt"]).start_of("day"),
                "temperature": DataPoint("Temperature", avg, t_unit,
                                          min_val=t_min, max_val=t_max) if avg is not None else None,
                "windSpeed": DataPoint("WindSpeed", wind_speed, s_unit) if wind_speed is not None else None,
                "windBearing": DataPoint("WindBearing", wind_deg, "°") if wind_deg is not None else None,
                "summary": summary,
                "icon": icon,
            }
            day_list.append(WeatherData.from_dict(dw))

        first_icon = day_list[0].icon if day_list else "clouds"
        self.data["daily"] = {"summary": first_icon, "icon": first_icon, "data": day_list}

    @staticmethod
    def _nws_icon(forecast_text):
        t = (forecast_text or "").lower()
        if "thunder" in t:
            return "thunderstorm"
        if "snow" in t or "blizzard" in t:
            return "snow"
        if "sleet" in t or "ice" in t or "freezing" in t:
            return "sleet"
        if "rain" in t or "shower" in t or "drizzle" in t:
            return "rain"
        if "fog" in t or "mist" in t or "haze" in t:
            return "fog"
        if "cloud" in t or "overcast" in t:
            return "clouds"
        if "partly" in t or "mostly clear" in t:
            return "partly-cloudy"
        if "clear" in t or "sunny" in t or "fair" in t:
            return "clear"
        return "clouds"
