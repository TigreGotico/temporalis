from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from astral.geocoder import database, lookup


def geolocate(address):
    try:
        # see https://astral.readthedocs.io/en/latest/#cities
        a = lookup(address, database())
        return a.latitude, a.longitude
    except Exception:
        pass

    geolocator = Nominatim(user_agent="temporalis")
    location = geolocator.geocode(address, timeout=10)
    if location is not None:
        return location.latitude, location.longitude
    raise ValueError(f"Could not geolocate address: {address!r}")


def reverse_geolocate(lat, lon):
    geolocator = Nominatim(user_agent="temporalis")
    location = geolocator.reverse(f"{lat}, {lon}", timeout=10)
    if location is None:
        return {}
    return location.raw


def get_timezone(latitude, longitude):
    return TimezoneFinder().timezone_at(lng=longitude, lat=latitude)
