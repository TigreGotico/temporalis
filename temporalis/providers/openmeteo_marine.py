"""Open-Meteo Marine weather provider — free, no API key required.

Covers global ocean areas. Returns wave (combined), wind-wave, swell, and
ocean current data. Falls back silently for landlocked coordinates (Open-Meteo
returns an error JSON rather than raising HTTP 4xx).

API docs: https://open-meteo.com/en/docs/marine-weather-api
"""
import pendulum
from temporalis.providers import WeatherProvider
from temporalis import WeatherData, DataPoint

_MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"

_HOURLY_PARAMS = [
    "wave_height", "wave_direction", "wave_period",
    "wind_wave_height", "wind_wave_direction", "wind_wave_period",
    "swell_wave_height", "swell_wave_direction", "swell_wave_period",
    "ocean_current_velocity", "ocean_current_direction",
]

_DAILY_PARAMS = [
    "wave_height_max", "wind_wave_height_max", "swell_wave_height_max",
    "wave_direction_dominant", "wind_wave_direction_dominant",
    "swell_wave_direction_dominant",
    "wave_period_max", "wind_wave_period_max", "swell_wave_period_max",
]


class OpenMeteoMarine(WeatherProvider):
    """Marine forecast from Open-Meteo Marine API (no key required).

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees. Must be over open ocean — the API
             returns an error for landlocked coordinates.
        units: ``"metric"`` (default, metres/km/h) or ``"us"`` (feet/mph).
        forecast_days: Number of forecast days (1–7, default 7).
    """

    def __init__(self, lat, lon, date=None, units="metric", forecast_days=7):
        super().__init__(lat, lon, date, units)
        self._forecast_days = max(1, min(7, int(forecast_days)))
        self._request()

    @staticmethod
    def from_address(address, **kwargs):
        from temporalis.location import geolocate
        lat, lon = geolocate(address)
        return OpenMeteoMarine(lat, lon, **kwargs)

    # ── unit helpers ──────────────────────────────────────────────────────────

    def _height_unit(self):
        return "ft" if self.units == "us" else "m"

    def _speed_unit(self):
        return "mph" if self.units == "us" else "km/h"

    def _convert_height(self, metres):
        if metres is None:
            return None
        return round(float(metres) * 3.28084, 2) if self.units == "us" else float(metres)

    def _convert_speed(self, kmh):
        if kmh is None:
            return None
        return round(float(kmh) * 0.621371, 2) if self.units == "us" else float(kmh)

    # ── API params ────────────────────────────────────────────────────────────

    def _params(self):
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly": ",".join(_HOURLY_PARAMS),
            "daily": ",".join(_DAILY_PARAMS),
            "timezone": self.timezone or "UTC",
            "forecast_days": self._forecast_days,
        }

    # ── parsing ───────────────────────────────────────────────────────────────

    def _parse_hourly(self, hourly):
        times = hourly.get("time", [])
        if not times:
            self.data["hourly"] = {"summary": "marine", "icon": "marine", "data": []}
            return

        h_unit = self._height_unit()
        s_unit = self._speed_unit()
        tz = self.timezone or "UTC"
        hours = []

        for i, time_str in enumerate(times):
            def _get(key, idx=i):
                arr = hourly.get(key, [])
                return arr[idx] if idx < len(arr) else None

            dt = pendulum.parse(time_str, tz=tz)

            w = {
                "datetime": dt,
                "summary": "marine",
                "icon": "marine",
                "waveHeight":       DataPoint("WaveHeight",        self._convert_height(_get("wave_height")),            h_unit) if _get("wave_height")            is not None else None,
                "waveDirection":    DataPoint("WaveDirection",      _get("wave_direction"),                               "°")   if _get("wave_direction")            is not None else None,
                "wavePeriod":       DataPoint("WavePeriod",         _get("wave_period"),                                  "s")   if _get("wave_period")               is not None else None,
                "windWaveHeight":   DataPoint("WindWaveHeight",     self._convert_height(_get("wind_wave_height")),       h_unit) if _get("wind_wave_height")          is not None else None,
                "windWaveDirection":DataPoint("WindWaveDirection",   _get("wind_wave_direction"),                          "°")   if _get("wind_wave_direction")        is not None else None,
                "windWavePeriod":   DataPoint("WindWavePeriod",     _get("wind_wave_period"),                             "s")   if _get("wind_wave_period")           is not None else None,
                "swellHeight":      DataPoint("SwellHeight",        self._convert_height(_get("swell_wave_height")),      h_unit) if _get("swell_wave_height")         is not None else None,
                "swellDirection":   DataPoint("SwellDirection",     _get("swell_wave_direction"),                         "°")   if _get("swell_wave_direction")       is not None else None,
                "swellPeriod":      DataPoint("SwellPeriod",        _get("swell_wave_period"),                            "s")   if _get("swell_wave_period")          is not None else None,
                "currentVelocity":  DataPoint("CurrentVelocity",    self._convert_speed(_get("ocean_current_velocity")), s_unit) if _get("ocean_current_velocity")     is not None else None,
                "currentDirection": DataPoint("CurrentDirection",   _get("ocean_current_direction"),                     "°")   if _get("ocean_current_direction")    is not None else None,
            }
            hours.append(WeatherData.from_dict(w))

        self.data["hourly"] = {"summary": "marine", "icon": "marine", "data": hours}

        # Set currently from the nearest hour
        now = self.datetime
        nearest = min(hours, key=lambda h: abs((h.datetime - now).total_seconds())
                      if h.datetime is not None else float("inf"))
        cur = {
            "datetime": nearest.datetime,
            "summary": "marine", "icon": "marine",
            "waveHeight": nearest.waveHeight,
            "waveDirection": nearest.waveDirection,
            "wavePeriod": nearest.wavePeriod,
            "windWaveHeight": nearest.windWaveHeight,
            "windWaveDirection": nearest.windWaveDirection,
            "windWavePeriod": nearest.windWavePeriod,
            "swellHeight": nearest.swellHeight,
            "swellDirection": nearest.swellDirection,
            "swellPeriod": nearest.swellPeriod,
            "currentVelocity": nearest.currentVelocity,
            "currentDirection": nearest.currentDirection,
        }
        self.data["currently"] = cur

    def _parse_daily(self, daily):
        times = daily.get("time", [])
        if not times:
            self.data["daily"] = {"summary": "marine", "icon": "marine", "data": []}
            return

        h_unit = self._height_unit()
        tz = self.timezone or "UTC"
        days = []

        for i, time_str in enumerate(times):
            def _get(key, idx=i):
                arr = daily.get(key, [])
                return arr[idx] if idx < len(arr) else None

            dt = pendulum.parse(time_str, tz=tz)
            wave_h = self._convert_height(_get("wave_height_max"))
            ww_h = self._convert_height(_get("wind_wave_height_max"))
            sw_h = self._convert_height(_get("swell_wave_height_max"))

            w = {
                "datetime": dt,
                "summary": "marine", "icon": "marine",
                "waveHeight":       DataPoint("WaveHeight",       wave_h,                         h_unit) if wave_h is not None else None,
                "waveDirection":    DataPoint("WaveDirection",    _get("wave_direction_dominant"), "°")   if _get("wave_direction_dominant")      is not None else None,
                "wavePeriod":       DataPoint("WavePeriod",       _get("wave_period_max"),         "s")   if _get("wave_period_max")              is not None else None,
                "windWaveHeight":   DataPoint("WindWaveHeight",   ww_h,                            h_unit) if ww_h is not None else None,
                "windWaveDirection":DataPoint("WindWaveDirection", _get("wind_wave_direction_dominant"), "°") if _get("wind_wave_direction_dominant") is not None else None,
                "windWavePeriod":   DataPoint("WindWavePeriod",   _get("wind_wave_period_max"),    "s")   if _get("wind_wave_period_max")         is not None else None,
                "swellHeight":      DataPoint("SwellHeight",      sw_h,                            h_unit) if sw_h is not None else None,
                "swellDirection":   DataPoint("SwellDirection",   _get("swell_wave_direction_dominant"), "°") if _get("swell_wave_direction_dominant") is not None else None,
                "swellPeriod":      DataPoint("SwellPeriod",      _get("swell_wave_period_max"),   "s")   if _get("swell_wave_period_max")        is not None else None,
            }
            days.append(WeatherData.from_dict(w))

        self.data["daily"] = {"summary": "marine", "icon": "marine", "data": days}

    def _request(self):
        raw = self.session.get(_MARINE_URL, params=self._params()).json()
        if "error" in raw:
            raise ValueError(f"Open-Meteo Marine: {raw.get('reason', raw['error'])}")
        self._parse_hourly(raw.get("hourly", {}))
        self._parse_daily(raw.get("daily", {}))
