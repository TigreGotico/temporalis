from __future__ import annotations

from typing import Optional, Any, List
from temporalis.time import int_to_weekday
import pendulum
from pprint import pprint


class DataPoint:
    def __init__(self, name: str, value: Optional[float], units: str,
                 min_val: Optional[float] = None, max_val: Optional[float] = None,
                 low_val: Optional[float] = None, high_val: Optional[float] = None,
                 time: Optional[Any] = None, min_time: Optional[Any] = None,
                 max_time: Optional[Any] = None,
                 low_time: Optional[Any] = None, high_time: Optional[Any] = None,
                 prob: Optional[float] = None, prob_min: Optional[float] = None,
                 prob_max: Optional[float] = None):
        self.name = name
        self.units = units
        self.value = value
        self.min_val = min_val if min_val is not None else value
        self.max_val = max_val if max_val is not None else value
        self.low_val = low_val if low_val is not None else self.min_val
        self.high_val = high_val if high_val is not None else self.max_val
        self.prob = prob
        self.prob_min = prob_min if prob_min is not None else prob
        self.prob_max = prob_max if prob_max is not None else prob
        self.time = time
        self.min_time = min_time if min_time is not None else time
        self.max_time = max_time if max_time is not None else time
        self.low_time = low_time if low_time is not None else time
        self.high_time = high_time if high_time is not None else time

    @staticmethod
    def _stamp_to_datetime(stamp, tz=None):
        tz = tz or "UTC"
        return pendulum.from_timestamp(stamp, tz=tz)

    def as_dict(self) -> dict:
        data = dict(self.__dict__)
        for k in list(data):
            if data[k] is None:
                data.pop(k)
        return data

    @staticmethod
    def from_dict(data) -> Optional[DataPoint]:
        if not isinstance(data, int) and not data:
            return None
        if isinstance(data, DataPoint):
            return data
        assert isinstance(data, dict)
        name = data["name"]
        units = data.get("units") or data.get("unit")
        tz = data.get("timezone")
        dt = None
        if data.get("time"):
            dt = data["time"]
            try:
                dt = DataPoint._stamp_to_datetime(data["time"], tz)
            except Exception:
                pass
        if data.get("datetime"):
            dt = data["datetime"]
            try:
                dt = DataPoint._stamp_to_datetime(data["datetime"], tz)
            except Exception:
                pass

        time = min_time = max_time = dt
        value = min_val = max_val = data.get("value")
        prob = prob_min = prob_max = data.get("prob")
        min_val = data.get("min_val") or data.get("min_value") or min_val
        max_val = data.get("max_val") or data.get("max_value") or max_val
        prob_min = data.get("min_prob") or data.get("prob_min") or prob_min
        prob_max = data.get("max_prob") or data.get("prob_max") or prob_max
        return DataPoint(name, value, units,
                         min_val=min_val, max_val=max_val,
                         time=time, min_time=min_time, max_time=max_time,
                         prob=prob, prob_min=prob_min, prob_max=prob_max)

    def __repr__(self):
        return str(self.value) + " " + self.units


# timestamped weather data
class WeatherData:
    def __init__(self):
        self.datetime = None
        self.apparentTemperature = None
        self.cloudCover = None
        self.dewPoint = None
        self.humidity = None
        self.icon = None
        self.ozone = None
        self.precipitation = None
        self.pressure = None
        self.summary = None
        self.temperature = None
        self.uvIndex = None
        self.visibility = None
        self.windBearing = None
        self.windGust = None
        self.windSpeed = None
        self.snow = None

    def __repr__(self):
        return str(self.datetime) + ":" + self.summary

    def pprint(self):
        pprint(self.as_dict())

    def print(self):
        print(self.weekday, self.datetime.date(), self.datetime.time(),
              self.timezone, ":", self.summary)
        print("temperature:", self.temperature)
        print("humidity:", self.humidity)
        print("cloudCover:", self.cloudCover)
        print("windSpeed:", self.windSpeed)
        print("precipitation:", self.precipitation)
        print("visibility:", self.visibility)

    @property
    def timezone(self):
        if not self.datetime:
            return pendulum.timezone("UTC")
        return self.datetime.timezone_name

    @property
    def weekday(self):
        if self.datetime is None:
            return -1
        return int_to_weekday(self.datetime.weekday())

    def as_dict(self) -> dict:
        data = dict(self.__dict__)
        for k in list(data):
            try:
                data[k] = data[k].as_dict()
            except Exception:
                pass
            if data[k] is None:
                data.pop(k)
        return data

    def _stamp_to_datetime(self, stamp, tz=None):
        tz = tz or self.timezone
        return pendulum.from_timestamp(stamp, tz=tz)

    @staticmethod
    def from_dict(data) -> WeatherData:
        assert isinstance(data, dict)
        point = WeatherData()
        point.icon = data.get("icon")
        point.summary = data.get("summary")

        if data.get("datetime"):
            dt = data["datetime"]
            try:
                dt = point._stamp_to_datetime(data["datetime"])
            except Exception:
                pass
            point.datetime = dt

        point.temperature = DataPoint.from_dict(data.get("temperature"))
        point.apparentTemperature = DataPoint.from_dict(
            data.get("apparentTemperature")) or point.temperature

        point.cloudCover = DataPoint.from_dict(data.get("cloudCover"))
        point.dewPoint = DataPoint.from_dict(data.get("dewPoint"))
        point.humidity = DataPoint.from_dict(data.get("humidity"))
        point.ozone = DataPoint.from_dict(data.get("ozone"))
        point.pressure = DataPoint.from_dict(data.get("pressure"))
        point.uvIndex = DataPoint.from_dict(data.get("uvIndex"))
        point.visibility = DataPoint.from_dict(data.get("visibility"))
        point.windBearing = DataPoint.from_dict(data.get("windBearing"))
        point.windGust = DataPoint.from_dict(data.get("windGust"))
        point.windSpeed = DataPoint.from_dict(data.get("windSpeed"))
        point.precipitation = DataPoint.from_dict(data.get("precipitation"))
        point.snow = DataPoint.from_dict(data.get("snow"))

        return point


# Collection of forecasts
class HourlyForecast:
    def __init__(self, date, hours, weather):
        self.datetime = date
        self.hours = hours
        self.weather = weather

    def __getitem__(self, item):
        return self.hours[item]

    def __iter__(self):
        for m in self.hours:
            yield m

    @property
    def summary(self):
        return self.weather.summary

    @property
    def icon(self):
        return self.weather.icon

    def print(self):
        print(self.datetime, ":", self.summary)

    def pprint(self):
        pprint(self.as_dict())

    def as_dict(self):
        return {"datetime": self.datetime,
                "hours": [m.as_dict() for m in self.hours],
                "weather": self.weather.as_dict()}


class DailyForecast:
    def __init__(self, date, days, weather):
        self.datetime = date
        self.days = days
        self.weather = weather

    def __getitem__(self, item):
        return self.days[item]

    def __iter__(self):
        for m in self.days:
            yield m

    def print(self):
        print(self.datetime, ":", self.summary)

    def pprint(self):
        pprint(self.as_dict())

    @property
    def summary(self):
        return self.weather.summary

    @property
    def icon(self):
        return self.weather.icon

    def as_dict(self):
        return {"datetime": self.datetime,
                "days": [m.as_dict() for m in self.days],
                "weather": self.weather.as_dict()}


class MinutelyData:
    """One-minute precipitation snapshot."""

    def __init__(self, dt: Any,
                 precipitation: Optional[DataPoint] = None,
                 precipitation_probability: Optional[DataPoint] = None):
        self.datetime = dt
        self.precipitation = precipitation                    # mm/h intensity
        self.precipitation_probability = precipitation_probability  # 0–1

    def __repr__(self) -> str:
        return f"MinutelyData({self.datetime}, precip={self.precipitation})"

    def as_dict(self) -> dict:
        data = dict(self.__dict__)
        for k in list(data):
            try:
                data[k] = data[k].as_dict()
            except Exception:
                pass
            if not data[k] and data[k] != 0:
                data.pop(k)
        return data


class MinutelyForecast:
    """Ordered collection of per-minute readings for the next ~60 minutes."""

    def __init__(self, minutes: List[MinutelyData]):
        self.minutes = minutes

    def __len__(self) -> int:
        return len(self.minutes)

    def __getitem__(self, item):
        return self.minutes[item]

    def __iter__(self):
        return iter(self.minutes)

    def __repr__(self) -> str:
        return f"MinutelyForecast({len(self.minutes)} minutes)"

    def as_dict(self) -> dict:
        return {"minutes": [m.as_dict() for m in self.minutes]}
