"""Registering a custom provider — plug in any data source."""
from temporalis.providers import WeatherProvider
from temporalis import DataPoint, WeatherData
from temporalis.time import now_utc


class MyProvider(WeatherProvider):
    """Minimal stub that returns a fixed reading — replace with real API calls."""

    def __init__(self, lat, lon, **kwargs):
        super().__init__(lat, lon, **kwargs)
        self._load()

    def _load(self):
        dt = now_utc()
        self.data["currently"] = {
            "datetime": dt,
            "summary": "sunny",
            "icon": "clear-day",
            "temperature": {"name": "temperature", "value": 22.0, "units": "°C"},
            "humidity": {"name": "humidity", "value": 0.55, "units": "%"},
        }
        self.data["daily"] = {"summary": "sunny", "icon": "clear-day", "data": []}
        self.data["hourly"] = {"summary": "sunny", "icon": "clear-day", "data": []}


# Register under a name so it can be selected at runtime
WeatherProvider.register("myprovider", MyProvider)

# Now usable via the registry API
p = WeatherProvider.get("myprovider", 38.72, -9.14)
print(p)                            # __repr__
print(p.weather.temperature)        # DataPoint
print(p.dawn)                       # sun/moon still work
print("Providers:", WeatherProvider.available())
