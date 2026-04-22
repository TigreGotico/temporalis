import pendulum
from temporalis.providers import WeatherProvider
from temporalis import WeatherData, DataPoint
from temporalis.providers.openmeteo import _WMO_ICON

_API_URL = "https://archive-api.open-meteo.com/v1/archive"

_DAILY_PARAMS = [
    "temperature_2m_max", "temperature_2m_min",
    "apparent_temperature_max", "apparent_temperature_min",
    "precipitation_sum", "precipitation_hours",
    "weathercode", "windspeed_10m_max", "windgusts_10m_max",
    "winddirection_10m_dominant", "shortwave_radiation_sum",
]

_HOURLY_PARAMS = [
    "temperature_2m", "apparent_temperature", "relativehumidity_2m",
    "dewpoint_2m", "cloudcover", "pressure_msl", "windspeed_10m",
    "winddirection_10m", "windgusts_10m", "precipitation",
    "snowfall", "visibility", "weathercode",
]


class OpenMeteoHistorical(WeatherProvider):
    """Open-Meteo historical archive — global, no API key.

    Usage:
        p = OpenMeteoHistorical(lat, lon, start="2024-01-01", end="2024-01-31")
        for day in p.days:
            print(day.datetime.date(), day.temperature)
    """

    def __init__(self, lat, lon, start=None, end=None,
                 date=None, units="metric", lang="en"):
        super().__init__(lat, lon, date, units, lang)
        if start is None:
            # default: yesterday
            start = pendulum.yesterday().format("YYYY-MM-DD")
        if end is None:
            end = start
        self.start_date = start
        self.end_date = end
        self._request()

    @staticmethod
    def from_address(address, **kwargs):
        from temporalis.location import geolocate
        lat, lon = geolocate(address)
        return OpenMeteoHistorical(lat, lon, **kwargs)

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
            "start_date": self.start_date,
            "end_date": self.end_date,
            "daily": ",".join(_DAILY_PARAMS),
            "hourly": ",".join(_HOURLY_PARAMS),
            "timezone": self.timezone or "UTC",
            **self._unit_params(),
        }
        raw = self.session.get(_API_URL, params=params).json()
        self._parse_daily(raw.get("daily", {}))
        self._parse_hourly(raw.get("hourly", {}))

    def _parse_daily(self, daily):
        times = daily.get("time", [])
        if not times:
            self.data["daily"] = {"summary": "", "icon": "", "data": []}
            self.data["currently"] = {}
            return

        t_unit = self._temp_unit()
        s_unit = self._speed_unit()
        p_unit = self._precip_unit()
        tz = self.timezone or "UTC"
        days = []

        for i, time_str in enumerate(times):
            def _get(key, idx=i):
                arr = daily.get(key, [])
                return arr[idx] if idx < len(arr) else None

            t_max = _get("temperature_2m_max")
            t_min = _get("temperature_2m_min")
            ap_max = _get("apparent_temperature_max")
            ap_min = _get("apparent_temperature_min")
            precip = _get("precipitation_sum")
            code = _get("weathercode") or 0
            wspeed = _get("windspeed_10m_max")
            wgust = _get("windgusts_10m_max")
            wdir = _get("winddirection_10m_dominant")
            icon = _WMO_ICON.get(code, "clouds")

            avg_temp = (t_max + t_min) / 2 if (t_max is not None and t_min is not None) else t_max

            w = {
                "datetime": pendulum.parse(time_str, tz=tz),
                "temperature": DataPoint("Temperature", avg_temp, t_unit,
                                         min_val=t_min, max_val=t_max) if avg_temp is not None else None,
                "apparentTemperature": DataPoint("ApparentTemperature",
                                                  (ap_max + ap_min) / 2 if (ap_max and ap_min) else ap_max,
                                                  t_unit, min_val=ap_min, max_val=ap_max) if ap_max is not None else None,
                "precipitation": DataPoint("Precipitation", precip, p_unit) if precip is not None else None,
                "windSpeed": DataPoint("WindSpeed", wspeed, s_unit) if wspeed is not None else None,
                "windGust": DataPoint("WindGust", wgust, s_unit) if wgust is not None else None,
                "windBearing": DataPoint("WindBearing", wdir, "°") if wdir is not None else None,
                "summary": icon,
                "icon": icon,
            }
            days.append(WeatherData.from_dict(w))

        first_icon = days[0].icon if days else "clouds"
        self.data["daily"] = {"summary": first_icon, "icon": first_icon, "data": days}
        # currently = first day's data
        self.data["currently"] = {
            "datetime": days[0].datetime,
            "temperature": days[0].temperature,
            "summary": days[0].summary,
            "icon": days[0].icon,
        }

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
            def _get(key, idx=i):
                arr = hourly.get(key, [])
                return arr[idx] if idx < len(arr) else None

            temp = _get("temperature_2m")
            ap_temp = _get("apparent_temperature")
            humidity = _get("relativehumidity_2m")
            dew = _get("dewpoint_2m")
            cloud = _get("cloudcover")
            pressure = _get("pressure_msl")
            wspeed = _get("windspeed_10m")
            wdir = _get("winddirection_10m")
            wgust = _get("windgusts_10m")
            precip = _get("precipitation")
            snow = _get("snowfall")
            vis = _get("visibility")
            code = _get("weathercode") or 0
            icon = _WMO_ICON.get(code, "clouds")

            w = {
                "datetime": pendulum.parse(time_str, tz=tz),
                "temperature": DataPoint("Temperature", temp, t_unit) if temp is not None else None,
                "apparentTemperature": DataPoint("ApparentTemperature", ap_temp, t_unit) if ap_temp is not None else None,
                "humidity": DataPoint("Humidity", humidity, "%") if humidity is not None else None,
                "dewPoint": DataPoint("DewPoint", dew, t_unit) if dew is not None else None,
                "cloudCover": DataPoint("CloudCover", cloud, "%") if cloud is not None else None,
                "pressure": DataPoint("Pressure", pressure, "hPa") if pressure is not None else None,
                "windSpeed": DataPoint("WindSpeed", wspeed, s_unit) if wspeed is not None else None,
                "windBearing": DataPoint("WindBearing", wdir, "°") if wdir is not None else None,
                "windGust": DataPoint("WindGust", wgust, s_unit) if wgust is not None else None,
                "precipitation": DataPoint("Precipitation", precip, p_unit) if precip is not None else None,
                "snow": DataPoint("Snow", snow, p_unit) if snow is not None else None,
                "visibility": DataPoint("Visibility", vis, "m") if vis is not None else None,
                "summary": icon,
                "icon": icon,
            }
            hours.append(WeatherData.from_dict(w))

        first_icon = hours[0].icon if hours else "clouds"
        self.data["hourly"] = {"summary": first_icon, "icon": first_icon, "data": hours}
