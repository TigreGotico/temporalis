"""Working with DataPoint — the atomic unit of all weather values."""
import temporalis.providers.registry  # noqa: F401
from temporalis.providers import WeatherProvider
from temporalis import DataPoint

p = WeatherProvider.get("openmeteo", 38.72, -9.14)
w = p.weather

# Every measurement is a DataPoint — not a raw float
temp = w.temperature
print(f"Type  : {type(temp)}")
print(f"Value : {temp.value}")
print(f"Units : {temp.units}")
print(f"Min   : {temp.min_val}")
print(f"Max   : {temp.max_val}")
print(f"Repr  : {temp}")          # "15.3 °C"

# None-safe access — some fields may be absent for a given provider
if w.uvIndex is not None:
    print(f"UV Index: {w.uvIndex.value}")
else:
    print("UV Index: not available from this provider")

# Shortcut via the provider
print(f"UV (provider property): {p.uv_index}")  # returns float or None

# Serialise to plain dict (for JSON, logging, etc.)
import json
d = w.as_dict()
print("\nWeatherData as JSON (excerpt):")
# DataPoint fields are also plain dicts in the output
print(json.dumps({k: d[k] for k in list(d)[:5]}, default=str, indent=2))

# Build your own DataPoint
custom = DataPoint("CO₂", 415.3, "ppm")
print(f"\nCustom: {custom}")
