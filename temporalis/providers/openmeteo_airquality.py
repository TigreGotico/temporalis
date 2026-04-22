import pendulum
from temporalis.providers import WeatherProvider
from temporalis import DataPoint

_API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

_HOURLY_PARAMS = [
    "pm10", "pm2_5", "ozone", "nitrogen_dioxide", "sulphur_dioxide",
    "carbon_monoxide", "european_aqi", "us_aqi", "uv_index",
    "dust", "ammonia",
]

# WHO / EU AQI thresholds for PM2.5 (µg/m³)
_AQI_LABEL = [
    (0, 20, "good"),
    (20, 40, "fair"),
    (40, 60, "moderate"),
    (60, 80, "poor"),
    (80, 100, "very-poor"),
    (100, float("inf"), "extremely-poor"),
]


def _aqi_label(european_aqi):
    if european_aqi is None:
        return "unknown"
    for lo, hi, label in _AQI_LABEL:
        if lo <= european_aqi < hi:
            return label
    return "extremely-poor"


class AirQualityData:
    """Hourly air quality snapshot."""

    def __init__(self):
        self.datetime = None
        self.pm10 = None
        self.pm2_5 = None
        self.ozone = None
        self.nitrogen_dioxide = None
        self.sulphur_dioxide = None
        self.carbon_monoxide = None
        self.european_aqi = None
        self.us_aqi = None
        self.uv_index = None
        self.dust = None
        self.ammonia = None
        self.summary = None   # human-readable AQI label

    def __repr__(self):
        return f"AirQualityData({self.datetime}, aqi={self.european_aqi}, {self.summary})"

    def as_dict(self):
        data = dict(self.__dict__)
        for k in list(data):
            try:
                data[k] = data[k].as_dict()
            except Exception:
                pass
            if not data[k] and data[k] != 0:
                data.pop(k)
        return data


class OpenMeteoAirQuality(WeatherProvider):
    """Open-Meteo Air Quality API — global, no API key.

    Usage:
        aq = OpenMeteoAirQuality(38.72, -9.14)
        print(aq.current.european_aqi, aq.current.summary)
        for hour in aq.air_quality_hours:
            print(hour.datetime, hour.pm2_5, hour.uv_index)
    """

    def __init__(self, lat, lon, date=None, units="metric", lang="en"):
        super().__init__(lat, lon, date, units, lang)
        self._aq_hours = []
        self._request()

    @staticmethod
    def from_address(address, **kwargs):
        from temporalis.location import geolocate
        lat, lon = geolocate(address)
        return OpenMeteoAirQuality(lat, lon, **kwargs)

    def _request(self):
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly": ",".join(_HOURLY_PARAMS),
            "timezone": self.timezone or "UTC",
        }
        raw = self.session.get(_API_URL, params=params).json()
        self._parse(raw.get("hourly", {}))

    def _parse(self, hourly):
        times = hourly.get("time", [])
        tz = self.timezone or "UTC"

        for i, time_str in enumerate(times):
            def _get(key, idx=i):
                arr = hourly.get(key, [])
                return arr[idx] if idx < len(arr) else None

            aq = AirQualityData()
            aq.datetime = pendulum.parse(time_str, tz=tz)
            aq.pm10 = DataPoint("PM10", _get("pm10"), "µg/m³") if _get("pm10") is not None else None
            aq.pm2_5 = DataPoint("PM2.5", _get("pm2_5"), "µg/m³") if _get("pm2_5") is not None else None
            aq.ozone = DataPoint("Ozone", _get("ozone"), "µg/m³") if _get("ozone") is not None else None
            aq.nitrogen_dioxide = DataPoint("NO₂", _get("nitrogen_dioxide"), "µg/m³") if _get("nitrogen_dioxide") is not None else None
            aq.sulphur_dioxide = DataPoint("SO₂", _get("sulphur_dioxide"), "µg/m³") if _get("sulphur_dioxide") is not None else None
            aq.carbon_monoxide = DataPoint("CO", _get("carbon_monoxide"), "µg/m³") if _get("carbon_monoxide") is not None else None
            aq.dust = DataPoint("Dust", _get("dust"), "µg/m³") if _get("dust") is not None else None
            aq.ammonia = DataPoint("NH₃", _get("ammonia"), "µg/m³") if _get("ammonia") is not None else None
            eu_aqi = _get("european_aqi")
            aq.european_aqi = DataPoint("European AQI", eu_aqi, "") if eu_aqi is not None else None
            us_aqi = _get("us_aqi")
            aq.us_aqi = DataPoint("US AQI", us_aqi, "") if us_aqi is not None else None
            uv = _get("uv_index")
            aq.uv_index = DataPoint("UV Index", uv, "") if uv is not None else None
            aq.summary = _aqi_label(eu_aqi)
            self._aq_hours.append(aq)

        # Populate standard WeatherProvider data fields with a stub so
        # inherited properties (dawn, moon, etc.) still work.
        if self._aq_hours:
            first = self._aq_hours[0]
            uv_val = first.uv_index.value if first.uv_index else None
            self.data["currently"] = {
                "datetime": first.datetime,
                "uvIndex": first.uv_index,
                "summary": first.summary,
                "icon": first.summary,
            }
        self.data["daily"] = {"summary": "", "icon": "", "data": []}
        self.data["hourly"] = {"summary": "", "icon": "", "data": []}

    @property
    def current(self):
        """Most recent air quality reading."""
        return self._aq_hours[0] if self._aq_hours else AirQualityData()

    @property
    def air_quality_hours(self):
        """All hourly air quality readings (120 hours / 5 days)."""
        return self._aq_hours
