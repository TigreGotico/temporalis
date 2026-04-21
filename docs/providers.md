# Adding a New Provider

Providers are subclasses of `WeatherProvider`
(`temporalis/providers/__init__.py:13`). The base class handles caching,
geocoding, and all forecast/sun/moon accessors. A new provider only needs
to fetch data from its upstream API and populate `self.data`.

---

## Minimal Subclass

```python
from temporalis.providers import WeatherProvider
from temporalis import WeatherData, DataPoint
import pendulum


class MyProvider(WeatherProvider):

    def __init__(self, lat, lon, date=None, units="metric", lang="en"):
        super().__init__(lat, lon, date, units, lang)
        self._request()   # fetch and populate self.data

    def _request(self):
        # fetch from upstream ...
        raw = self.session.get("https://example.com/api", params={
            "lat": self.latitude,
            "lon": self.longitude,
        }).json()

        # build WeatherData objects and store in self.data
        ...
```

---

## The `self.data` Dictionary

`WeatherProvider.__init__` initialises `self.data` as:

```python
self.data = {
    "latitude": lat,
    "longitude": lon,
    "timezone": self.datetime.timezone_name,
    "units": self._units,
    "currently": {},   # dict or WeatherData
    "daily": {},       # {"summary": str, "icon": str, "data": [WeatherData, ...]}
    "hourly": {},      # {"summary": str, "icon": str, "data": [WeatherData, ...]}
}
```

`temporalis/providers/__init__.py:52`

Your `_request()` must write to these three keys.

### `"currently"`

A dict suitable for `WeatherData.from_dict()`, or a pre-built `WeatherData`.
The base accessor `weather` calls `WeatherData().from_dict(self.data["currently"])`.
`temporalis/providers/__init__.py:122`

### `"hourly"` and `"daily"`

A dict with keys `"summary"` (str), `"icon"` (str), and `"data"`
(list of `WeatherData` or dicts). The base accessors `hourly` and `daily`
iterate over `data` and call `WeatherData().from_dict(item)` for any item
that is still a dict. `temporalis/providers/__init__.py:135,153`

---

## Building WeatherData

Construct a dict from `DataPoint` instances and pass it to
`WeatherData.from_dict()`:

```python
temperature = DataPoint("Temperature", 18.5, "ºC",
                        min_val=12.0, max_val=24.0)
precipitation = DataPoint("Precipitation", 0.0, "mm",
                          prob=0.15)  # 15 % probability

w = {
    "datetime": pendulum.parse(time_str, tz=self.timezone),
    "temperature": temperature,
    "apparentTemperature": temperature,  # optional: felt temperature
    "humidity": DataPoint("Humidity", 72, "%"),
    "pressure": DataPoint("Pressure", 1013, "hPa"),
    "windSpeed": DataPoint("WindSpeed", 4.2, "m/s"),
    "windBearing": DataPoint("WindBearing", 270, "°"),
    "precipitation": precipitation,
    "cloudCover": DataPoint("CloudCover", 40, "%"),
    "summary": "partly cloudy",
    "icon": "partly-cloudy",   # see icon slug list in data-model.md
}
weather_data = WeatherData.from_dict(w)
```

Omit any field that the upstream API does not provide — it will be `None` on
the resulting `WeatherData`.

---

## Helper Utilities on the Base Class

`WeatherProvider._stamp_to_datetime(stamp, tz_name=None)` —
`temporalis/providers/__init__.py:190`
Converts a Unix timestamp to a timezone-aware `pendulum.DateTime`.

`WeatherProvider._calc_day_average(hours)` —
`temporalis/providers/__init__.py:196`
Given a list of hourly `WeatherData` dicts (from `.as_dict()`), computes
min/max/average for each `DataPoint` field, suitable for synthesising a
daily summary from hourly data.

`WeatherProvider._calc_hourly_summary(hours)` /
`WeatherProvider._calc_daily_summary(days)` —
`temporalis/providers/__init__.py:225,231`
Return `(summary, icon)` from the first entry in the list.

---

## Geographic Restrictions

If the provider only covers a specific region, raise `ValueError` in
`__init__` before calling `super().__init__()`:

```python
_LAT_MIN, _LAT_MAX = 30.0, 43.0
_LON_MIN, _LON_MAX = -32.0, -6.0

def __init__(self, lat, lon, **kwargs):
    if not (_LAT_MIN <= lat <= _LAT_MAX and _LON_MIN <= lon <= _LON_MAX):
        raise ValueError(
            f"MyProvider only covers Region X. "
            f"Coordinates ({lat}, {lon}) are outside the supported region."
        )
    super().__init__(lat, lon, **kwargs)
    self._request()
```

IPMA does this for Portugal (`temporalis/providers/ipma.py:44`);
NWS does it for the USA (`temporalis/providers/nws.py:43`).

---

## from_address

Override the static factory to return your class:

```python
from temporalis.location import geolocate

@staticmethod
def from_address(address, key=None):
    lat, lon = geolocate(address)
    return MyProvider(lat, lon)
```

---

## User-Agent

If the upstream API requires a `User-Agent` header (Met.no and NWS both
enforce this), pass it explicitly:

```python
headers = {"User-Agent": "myapp/1.0 contact@example.com"}
raw = self.session.get(url, headers=headers).json()
```

Met.no: `temporalis/providers/metno.py:6`
NWS: `temporalis/providers/nws.py:7`
