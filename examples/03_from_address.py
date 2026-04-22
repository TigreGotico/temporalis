"""Geocode an address string and get the forecast — no manual lat/lon needed."""
import temporalis.providers.registry  # noqa: F401
from temporalis.providers import WeatherProvider

# All providers expose from_address() via the registry
p = WeatherProvider.from_address("Lisbon, Portugal", "openmeteo")

w = p.weather
print(f"Location : {p.latitude:.4f}, {p.longitude:.4f}")
print(f"Timezone : {p.timezone}")
print(f"Weather  : {w.summary}")
print(f"Temp     : {w.temperature}")
print(f"Moon     : {p.moon_symbol} {p.moon_phase_name}")
