from __future__ import annotations
from typing import Optional, List, Dict, Any, Type
from temporalis.location import geolocate, get_timezone
from temporalis.sun import get_dawn, get_dusk, get_sunrise, get_sunset, get_noon
from temporalis import WeatherData, DailyForecast, HourlyForecast, MinutelyForecast
from temporalis.time import now_utc
from temporalis.moon import get_moon_phase, moon_code_to_symbol, \
    moon_code_to_name
from pendulum import timezone
import pendulum
import requests


class WeatherProvider:

    def __init__(self, lat, lon, date=None, units="metric", lang="en"):
        self.session = requests.Session()
        self.lang = lang
        self.datetime = date or now_utc()
        self._alerts = []
        if units in ["english", "imperial", "us"]:
            units = "us"

        # units=[units] optional
        #
        # Return weather conditions in the requested units.
        # [units] should be one of the following:
        #
        #     auto: automatically select units based on geographic location
        #     ca: same as si, except that windSpeed and windGust are in kilometers per hour
        #     uk2: same as si, except that nearestStormDistance and visibility are in miles, and windSpeed and windGust in miles per hour
        #     us: Imperial units (the default)
        #     si: SI units

        # SI units are as follows:
        #
        #     summary: Any summaries containing temperature or snow accumulation units will have their values in degrees Celsius or in centimeters (respectively).
        #     nearestStormDistance: Kilometers.
        #     precipitation: Millimeters per hour.
        #     precipitation.max_val: Millimeters per hour.
        #     precipAccumulation: Centimeters.
        #     temperature: Degrees Celsius.
        #     temperature.min_val: Degrees Celsius.
        #     temperature.max_val: Degrees Celsius.
        #     apparentTemperature: Degrees Celsius.
        #     dewPoint: Degrees Celsius.
        #     windSpeed: Meters per second.
        #     windGust: Meters per second.
        #     pressure: Hectopascals.
        #     visibility: Kilometers.
        self._units = units

        self.data = {"latitude": lat,
                     "longitude": lon,
                     "timezone": self.datetime.timezone_name,
                     "units": self._units,
                     "currently": {},
                     "daily": {},
                     "hourly": {}}

    def __repr__(self):
        try:
            w = self.weather
            return (f"{self.__class__.__name__}("
                    f"{self.latitude:.4f}, {self.longitude:.4f}) "
                    f"— {w.summary} {w.temperature}")
        except Exception:
            return f"{self.__class__.__name__}({self.latitude:.4f}, {self.longitude:.4f})"

    # sun
    @property
    def dawn(self):
        return get_dawn(self.latitude, self.longitude, self.datetime)

    @property
    def sunrise(self):
        return get_sunrise(self.latitude, self.longitude, self.datetime)

    @property
    def noon(self):
        return get_noon(self.latitude, self.longitude, self.datetime)

    @property
    def sunset(self):
        return get_sunset(self.latitude, self.longitude, self.datetime)

    @property
    def dusk(self):
        return get_dusk(self.latitude, self.longitude, self.datetime)

    # moon
    @property
    def moon_phase(self):
        return get_moon_phase(self.datetime)[0]

    @property
    def moon_code(self):
        return get_moon_phase(self.datetime)[1]

    @property
    def moon_symbol(self):
        return moon_code_to_symbol(self.moon_code)

    @property
    def moon_phase_name(self):
        return moon_code_to_name(self.moon_code, self.lang)

    # uv
    @property
    def uv_index(self):
        """Current UV index, or None if the provider does not supply it."""
        uv = getattr(self.weather, "uvIndex", None)
        if uv is not None:
            return uv.value
        return None

    # alerts
    @property
    def alerts(self):
        """List of active weather alerts. Each is a dict with keys:
        event, severity, headline, description, onset, expires.
        Returns an empty list if the provider does not support alerts."""
        return list(self._alerts)

    # localization
    @property
    def units(self):
        return self._units

    @property
    def latitude(self):
        return self.data["latitude"]

    @property
    def longitude(self):
        return self.data["longitude"]

    @staticmethod
    def from_address(address, key=None):
        lat, lon = geolocate(address)
        return WeatherProvider(lat, lon)

    @property
    def timezone(self):
        return get_timezone(latitude=self.latitude, longitude=self.longitude)

    # weather forecasts
    @property
    def weather(self):
        from temporalis.derived import fill_derived
        return fill_derived(WeatherData().from_dict(self.data["currently"]),
                            lat=self.latitude, lon=self.longitude)

    @property
    def weather_tomorrow(self):
        return self.weather_in_n_days(1)

    def weather_in_n_days(self, n):
        if n >= len(self.days):
            raise OverflowError
        return self.days[n].weather

    @property
    def hourly(self):
        daily = self.data["hourly"]

        hourly_weather = WeatherData()
        hourly_weather.icon = daily["icon"]
        hourly_weather.summary = daily["summary"]
        hourly_weather.datetime = self.datetime

        from temporalis.derived import fill_derived
        hours = []
        for hour in daily["data"]:
            if isinstance(hour, dict):
                weather = WeatherData().from_dict(hour)
            else:
                weather = hour
            hours.append(fill_derived(weather, lat=self.latitude, lon=self.longitude))

        return HourlyForecast(self.datetime, hours, hourly_weather)

    @property
    def hours(self):
        return self.hourly.hours

    @property
    def minutely(self) -> MinutelyForecast:
        """Per-minute precipitation for the next ~60 minutes.

        Returns an empty MinutelyForecast when the provider does not support
        minutely data or the subscription tier does not include it.
        """
        return MinutelyForecast([])

    @property
    def daily(self):
        daily = self.data["daily"]

        daily_weather = WeatherData()
        if daily.get("icon"):
            daily_weather.icon = daily["icon"]
            daily_weather.summary = daily["summary"]
        else:
            daily_weather.icon = daily["data"][0].icon
            daily_weather.summary = daily["data"][0].summary
        daily_weather.datetime = self.datetime
        from temporalis.derived import fill_derived
        days = [fill_derived(d if not isinstance(d, dict) else WeatherData().from_dict(d),
                             lat=self.latitude, lon=self.longitude)
                for d in daily["data"]]
        return DailyForecast(self.datetime, days, daily_weather)

    @property
    def days(self):
        return self.daily.days

    # pretty print
    def print(self):
        self.weather.print()

    def print_daily(self):
        # self.daily.print()
        for day in self.days:
            print(day.weekday, ":", day.datetime.date(), ":", day.summary)

    def print_hourly(self):
        # self.hourly.print()
        for hour in self.hours:
            print(hour.weekday, ":", hour.datetime.time(), ":", hour.summary)

    def _get_json(self, url: str, **kwargs) -> dict:
        """GET *url* and return parsed JSON, raising a clear error on failure."""
        resp = self.session.get(url, **kwargs)
        if not resp.ok:
            raise RuntimeError(
                f"{self.__class__.__name__}: HTTP {resp.status_code} from {url}"
            )
        try:
            data = resp.json()
        except Exception as exc:
            raise RuntimeError(
                f"{self.__class__.__name__}: non-JSON response from {url}"
            ) from exc
        # Some APIs return HTTP 200 with an error payload (OWM, Open-Meteo)
        if isinstance(data, dict) and data.get("cod") not in (None, 200, "200"):
            raise RuntimeError(
                f"{self.__class__.__name__}: API error — {data.get('message', data)}"
            )
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(
                f"{self.__class__.__name__}: API error — {data.get('reason', data)}"
            )
        return data

    # internals
    def _stamp_to_datetime(self, stamp, tz_name=None):
        if tz_name:
            return pendulum.from_timestamp(stamp, tz=timezone(tz_name))
        return pendulum.from_timestamp(stamp, tz=self.timezone)

    @staticmethod
    def _calc_day_average(hours):
        data = hours[0].as_dict()

        for idx, d in enumerate(hours):
            new_data = d.as_dict()
            for k in new_data:
                try:
                    if new_data[k]["min_val"] < data[k]["min_val"]:
                        data[k]["min_val"] = new_data[k]["min_val"]
                        data[k]["min_time"] = new_data[k]["time"]
                    if new_data[k]["max_val"] > data[k]["max_val"]:
                        data[k]["max_val"] = new_data[k]["max_val"]
                        data[k]["max_time"] = new_data[k]["time"]
                    offset = new_data[k]["max_val"] - new_data[k]["min_val"]
                    new_data[k]["val"] = new_data[k]["min_val"] + offset / 2
                except Exception:
                    pass
                try:
                    if new_data[k]["prob_min"] < data[k]["prob_min"]:
                        data[k]["prob_min"] = new_data[k]["prob_min"]
                    if new_data[k]["prob_max"] > data[k]["prob_max"]:
                        data[k]["prob_max"] = new_data[k]["prob_max"]
                    offset = new_data[k]["prob_max"] - new_data[k]["prob_min"]
                    new_data[k]["prob"] = new_data[k]["prob_min"] + offset / 2
                except Exception:
                    pass

        return data

    @staticmethod
    def _calc_hourly_summary(hours):
        hourly_summary = hours[0].summary
        hourly_icon = hours[0].icon
        return hourly_summary, hourly_icon

    @staticmethod
    def _calc_daily_summary(days):
        hourly_summary = days[0].summary
        hourly_icon = days[0].icon
        return hourly_summary, hourly_icon

    @staticmethod
    def compare(provider_names, lat, lon, **kwargs):
        """Fetch the same location from multiple providers and return a summary dict.

        Example:
            results = WeatherProvider.compare(["openmeteo", "metno"], 38.72, -9.14)
            for name, data in results.items():
                print(name, data["temperature"], data["summary"])
        """
        import temporalis.providers.registry  # noqa: F401 — ensure registration
        results = {}
        for name in provider_names:
            try:
                p = WeatherProvider.get(name, lat, lon, **kwargs)
                w = p.weather
                results[name] = {
                    "temperature": w.temperature,
                    "summary": w.summary,
                    "humidity": w.humidity,
                    "wind_speed": w.windSpeed,
                    "precipitation": w.precipitation,
                    "uv_index": p.uv_index,
                    "alerts": p.alerts,
                    "provider": p,
                }
            except Exception as e:
                results[name] = {"error": str(e)}
        return results

    # Registry
    _registry = {}

    @classmethod
    def register(cls, name, provider_cls):
        cls._registry[name.lower()] = provider_cls

    @classmethod
    def get(cls, name, lat, lon, **kwargs):
        """Instantiate a provider by name. Example: WeatherProvider.get("metno", 38.72, -9.14)"""
        key = name.lower()
        if key not in cls._registry:
            raise ValueError(f"Unknown provider {name!r}. Available: {sorted(cls._registry)}")
        return cls._registry[key](lat, lon, **kwargs)

    @classmethod
    def from_address(cls, address, name, **kwargs):
        """Instantiate a named provider from an address string."""
        key = name.lower()
        if key not in cls._registry:
            raise ValueError(f"Unknown provider {name!r}. Available: {sorted(cls._registry)}")
        provider_cls = cls._registry[key]
        if hasattr(provider_cls, "from_address"):
            return provider_cls.from_address(address, **kwargs)
        lat, lon = geolocate(address)
        return provider_cls(lat, lon, **kwargs)

    @classmethod
    def available(cls):
        """Return sorted list of registered provider names."""
        return sorted(cls._registry)
