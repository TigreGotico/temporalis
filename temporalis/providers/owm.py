from temporalis.location import geolocate
from temporalis.providers import WeatherProvider
from temporalis import WeatherData, DataPoint, MinutelyData, MinutelyForecast

# OWM always returns wind speed in m/s and precipitation in mm regardless of
# the `units` param (the units param only affects temperature).  We convert
# locally to match the user's requested unit system.

def _ms_to_mph(ms):
    return round(ms * 2.237, 2) if ms is not None else None


def _mm_to_in(mm):
    return round(mm / 25.4, 4) if mm is not None else None


class OWM(WeatherProvider):
    default_key = "28fed22898afd4717ce5a1535da1f78c"

    def __init__(self, lat, lon, key=None,
                 date=None, units="metric"):
        super().__init__(lat, lon, date, units)
        self.key = key or self.default_key
        self._minutely: list = []
        self._request()

    def _owm_units(self):
        """Translate internal unit name to OWM API units param."""
        return "imperial" if self.units == "us" else self.units

    def _speed_unit(self):
        return "mph" if self.units == "us" else "m/s"

    def _precip_unit(self):
        return "inch" if self.units == "us" else "mm"

    def _convert_speed(self, ms):
        """OWM always returns m/s; convert to mph for imperial mode."""
        if ms is None:
            return None
        return _ms_to_mph(ms) if self.units == "us" else ms

    def _convert_precip(self, mm):
        """OWM always returns mm; convert to inches for imperial mode."""
        if mm is None:
            return None
        return _mm_to_in(mm) if self.units == "us" else mm

    @staticmethod
    def from_address(address, key=None):
        lat, lon = geolocate(address)
        return OWM(lat, lon, key)

    def _request_current(self):
        if self.units == "auto":
            API_URL = "https://api.openweathermap.org/data/2.5/weather?lat={" \
                      "lat}&lon={lon}&appid={key}"
            url = API_URL.format(key=self.key, lat=self.latitude,
                                 lon=self.longitude)
        else:
            API_URL = "https://api.openweathermap.org/data/2.5/weather?lat={" \
                      "lat}&lon={lon}&appid={key}&units={units}"
            url = API_URL.format(key=self.key, lat=self.latitude,
                                 lon=self.longitude,
                                 units=self._owm_units())
        entry = self._get_json(url)
        """
        {'base': 'stations',
         'clouds': {'all': 20},  # %
         'cod': 200,
         'coord': {'lat': 38.72, 'lon': -9.14},
         'dt': 1592522239,
         'id': 8012502,
         'main': {'feels_like': 15.59,
                  'humidity': 87,  # %
                  'pressure': 1019, # hPa
                  'temp': 16.67,  # Celsius, Kelvin, Fahrenheit
                  'temp_max': 17.78,
                  'temp_min': 15.56},
         'name': 'Socorro',
         'sys': {'country': 'PT',
                 'id': 6901,
                 'sunrise': 1592543502,
                 'sunset': 1592597056,
                 'type': 1},
         'timezone': 3600,  # Shift in seconds from UTC
         'visibility': 10000, #  meter
         'weather': [{'description': 'few clouds',
                      'icon': '02n',
                      'id': 801,
                      'main': 'Clouds'}],
         'wind': {'deg': 330, 
                  'speed': 3.6 # m/s
                  }}
        """

        pressure = entry["main"].get("pressure")
        if pressure is not None:
            pressure = DataPoint("Pressure", pressure, "hPa")

        cloudCover = entry.get("clouds", {}).get("all")
        if cloudCover is not None:
            cloudCover = DataPoint("CloudCover", cloudCover, "%")

        visibility = entry.get("visibility")
        if visibility is not None:
            visibility = DataPoint("Visibility", visibility, "m")

        humidity = entry["main"].get("humidity")
        if humidity is not None:
            humidity = DataPoint("Humidity", humidity, "%")

        temperature = entry["main"].get("temp")
        if temperature is not None:
            temperature_min = entry["main"].get("temp_min")
            temperature_max = entry["main"].get("temp_max")
            if self.units == "metric":
                unit = "ºC"
            elif self.units == "si":
                unit = "K"
            else:
                unit = "ºF"
            temperature = DataPoint("Temperature", temperature, unit,
                                    min_val=temperature_min,
                                    max_val=temperature_max)

        ap_temperature = entry["main"].get("feels_like") or temperature
        if ap_temperature is not None:
            if self.units == "metric":
                unit = "ºC"
            elif self.units == "si":
                unit = "K"
            else:
                unit = "ºF"
            ap_temperature = DataPoint("ApparentTemperature", ap_temperature,
                                       unit)

        wind_speed_raw = entry.get("wind", {}).get("speed")
        wind_speed = DataPoint("WindSpeed", self._convert_speed(wind_speed_raw),
                               self._speed_unit()) if wind_speed_raw is not None else None

        wind_bearing = entry.get("wind", {}).get("deg")
        if wind_bearing is not None:
            wind_bearing = DataPoint("WindBearing", wind_bearing, "º")

        _w = entry.get("weather", [])
        icon = ""
        summary = ""
        if _w:
            icon = _w[0].get("main", "").lower()
            summary = _w[0].get("description") or icon

        rain1h = entry.get("rain", {}).get("1h")
        rain3h = entry.get("rain", {}).get("3h")
        if rain3h is not None and rain1h is None:
            rain1h = rain3h / 3
        precip = DataPoint("Precipitation", self._convert_precip(rain1h),
                           self._precip_unit()) if rain1h is not None else None

        ts = entry["dt"]
        date = self._stamp_to_datetime(ts)
        w = {
            "datetime": date,
            "pressure": pressure,
            "cloudCover": cloudCover,
            "visibility": visibility,
            "humidity": humidity,
            "temperature": temperature,
            "apparentTemperature": ap_temperature,
            "windSpeed": wind_speed,
            "windBearing": wind_bearing,
            "precipitation": precip,
            "summary": summary,
            "icon": icon,
        }

        hour = WeatherData.from_dict(w)

        self.data["timezone"] = self.timezone
        self.data["latitude"] = self.latitude
        self.data["longitude"] = self.longitude
        self.data["currently"] = w
        self.data["daily"] = {"summary": w["summary"],
                              "icon": w["icon"],
                              "data": [hour]}
        self.data["hourly"] = {"summary": w["summary"],
                               "icon": w["icon"],
                               "data": [hour]}

    def _request_forecast(self):
        if self.units == "auto":
            OWM_URL = "https://api.openweathermap.org/data/2.5/forecast?lat" \
                      "={lat}&lon={lon}&appid={key}"
            url = OWM_URL.format(key=self.key, lat=self.latitude,
                                 lon=self.longitude)
        else:
            OWM_URL = "https://api.openweathermap.org/data/2.5/forecast?lat" \
                      "={lat}&lon={lon}&appid={key}&units={units}"
            url = OWM_URL.format(key=self.key, lat=self.latitude,
                                 lon=self.longitude,
                                 units=self._owm_units())

        res = self._get_json(url)

        # OWM returns 3h in 3h readings
        hours = []
        _days = {}
        for entry in res["list"]:
            pressure = entry["main"].get("pressure")
            if pressure is not None:
                pressure = DataPoint("Pressure", pressure, "hPa")

            cloudCover = entry.get("clouds", {}).get("all")
            if cloudCover is not None:
                cloudCover = DataPoint("CloudCover", cloudCover, "%")

            visibility = entry.get("visibility")
            if visibility is not None:
                visibility = DataPoint("Visibility", visibility, "m")

            humidity = entry["main"].get("humidity")
            if humidity is not None:
                humidity = DataPoint("Humidity", humidity, "%")

            temperature = entry["main"].get("temp")
            if self.units == "metric":
                unit = "ºC"
            elif self.units == "si":
                unit = "K"
            else:
                unit = "ºF"
            if temperature is not None:
                temperature_min = entry["main"].get("temp_min")
                temperature_max = entry["main"].get("temp_max")
                temperature = DataPoint("Temperature", temperature, unit,
                                        min_val=temperature_min,
                                        max_val=temperature_max)

            ap_temperature = entry["main"].get("feels_like")
            if ap_temperature is not None:
                ap_temperature = DataPoint("ApparentTemperature",
                                           ap_temperature,
                                           unit)
            else:
                ap_temperature = DataPoint("ApparentTemperature", temperature,
                                           unit,
                                           min_val=temperature_min,
                                           max_val=temperature_max)

            wind_speed_raw = entry.get("wind", {}).get("speed")
            wind_speed = DataPoint("WindSpeed", self._convert_speed(wind_speed_raw),
                                   self._speed_unit()) if wind_speed_raw is not None else None

            wind_bearing = entry.get("wind", {}).get("deg")
            if wind_bearing is not None:
                wind_bearing = DataPoint("WindBearing", wind_bearing, "º")

            _w = entry.get("weather", [])
            icon = ""
            summary = ""
            if _w:
                icon = _w[0].get("main", "").lower()
                summary = _w[0].get("description") or icon

            rain1h = entry.get("rain", {}).get("1h")
            rain3h = entry.get("rain", {}).get("3h")
            if rain3h is not None and rain1h is None:
                rain1h = rain3h / 3
            precip = DataPoint("Precipitation", self._convert_precip(rain1h),
                               self._precip_unit()) if rain1h is not None else None

            ts = entry["dt"]
            date = self._stamp_to_datetime(ts)
            w = {
                "datetime": date,
                "pressure": pressure,
                "cloudCover": cloudCover,
                "visibility": visibility,
                "humidity": humidity,
                "temperature": temperature,
                "apparentTemperature": ap_temperature,
                "windSpeed": wind_speed,
                "windBearing": wind_bearing,
                "precipitation": precip,
                "summary": summary,
                "icon": icon,
            }

            h = WeatherData().from_dict(w)
            hours.append(h)
            if h.datetime.day not in _days:
                _days[h.datetime.day] = []
            _days[h.datetime.day] += [h]

        hourly_summary, hourly_icon = self._calc_hourly_summary(hours)
        self.data["timezone"] = self.timezone
        self.data["latitude"] = self.latitude
        self.data["longitude"] = self.longitude
        self.data["hourly"] = {"summary": hourly_summary,
                               "icon": hourly_icon,
                               "data": hours}

        days = []
        for d in _days:
            day = self._calc_day_average(_days[d])
            day = WeatherData.from_dict(day)
            days += [day]

        daily_summary, daily_icon = self._calc_daily_summary(days)
        self.data["daily"] = {"summary": daily_summary,
                              "icon": daily_icon,
                              "data": days}

    def _request_minutely(self):
        """One Call 3.0 — per-minute precipitation for the next 60 minutes.

        Requires a paid One Call 3.0 subscription key. Falls back silently
        when the endpoint returns a 401/402 or when minutely data is absent
        (e.g. the location has no radar coverage).
        """
        url = (
            "https://api.openweathermap.org/data/3.0/onecall"
            f"?lat={self.latitude}&lon={self.longitude}"
            f"&appid={self.key}&exclude=current,hourly,daily,alerts"
        )
        try:
            resp = self.session.get(url)
            if not resp.ok:
                return
            raw = resp.json()
        except Exception:
            return

        for entry in raw.get("minutely", []):
            ts = entry.get("dt")
            if ts is None:
                continue
            dt = self._stamp_to_datetime(ts)
            precip_val = entry.get("precipitation")
            p_unit = "in/h" if self.units == "us" else "mm/h"
            precip_converted = self._convert_precip(precip_val)
            precip = DataPoint("Precipitation", precip_converted, p_unit) if precip_val is not None else None
            self._minutely.append(MinutelyData(dt, precipitation=precip))

    @property
    def minutely(self) -> MinutelyForecast:
        return MinutelyForecast(self._minutely)

    def _request(self):
        self._request_current()
        self._request_forecast()
        self._request_minutely()

